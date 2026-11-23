# Defending the Internship Tracker: interview prep

How to explain every major decision in this project, why it was made, what the alternatives were, and what a skeptical interviewer might push back with. Several of these decisions changed after a **reviewer agent** challenged the first design. Those stories are marked 🔁 and make some of your best interview material: they show you can take critique and change your mind for a good reason.

**Practice tip:** for each section, cover the answer and say it out loud in under 60 seconds. If you can't, re-read the "core idea" line.

---

## 1. The 30-second project pitch

> "It's a full-stack internship tracker: React on Vercel, FastAPI and Postgres on Render and Neon. Beyond basic CRUD, it finds internships near you using your browser location or a typed city, and it can watch your Gmail, read-only, for replies from companies you applied to. When a company replies, you get a notification and a suggested status change, like 'Applied → Interview'. I designed it privacy-first: we store a city, never an address, and we read email headers, never bodies. Before building, I had a review agent attack the design, and that caught a real OAuth security hole."

---

## 2. Architecture

```
React (Vercel) ──HTTPS + JWT──▶ FastAPI (Render) ──▶ Postgres (Neon)
     │                              │
     │ navigator.geolocation        ├──▶ OpenStreetMap Nominatim (city lookup)
     │ (rounded to ~1 km)           ├──▶ Adzuna API (job postings)
     │                              └──▶ Google OAuth + Gmail API (read-only)
     │
GitHub Actions cron ──every 30 min──▶ POST /internal/sync-all
```

**Q: Why split the backend into `routers/` and `services/`?**
A: Routers handle HTTP (request parsing, status codes, auth). Services hold business logic (classifying an email, matching it to an application) with no HTTP involved. That separation is why the classifier and matcher can be unit-tested as plain functions. `main.py` would have grown to roughly 800 lines otherwise.

**Q: Why does each service have exactly one function that touches the network?**
A: It's a seam for testing. `geo._get_json`, `job_search._fetch_adzuna` and the `gmail_client` functions are the only places that make HTTP calls, so tests replace just those with fakes (`monkeypatch`). The tests run offline in about 15 seconds and never touch a real inbox.

---

## 3. Location: "How is this safe?"

**Core idea:** collect the least data that still works (*data minimization*), and drop precision as early as possible.

| Step | What happens | Why |
|---|---|---|
| 1 | We explain *why* before the browser prompt appears | Informed consent; the native prompt has no context |
| 2 | `enableHighAccuracy: false` | We only need a city, so coarse Wi-Fi/cell location is enough instead of GPS |
| 3 | Browser rounds to 2 decimals (~1.1 km) | Precise location never leaves the device |
| 4 | Server rounds again | Defense in depth: don't trust the client |
| 5 | Nominatim returns full address → we keep only city + state | Street/ZIP discarded immediately |
| 6 | Saved only if user clicks "Save as default" | Opt-in storage |
| 7 | Sent in a **POST body**, not the URL 🔁 | URLs are written to server access logs; bodies aren't |

**Q: The user asked to type their home address. Isn't storing that riskier?**
A: We accept it, geocode it once, return "San Jose, CA", and throw the address away. Even the server-side cache key is a SHA-256 hash of the text, so raw addresses never sit in memory as keys. We verified the access log shows only `POST /location/resolve`.

🔁 **Story:** "My first design used `GET /location/resolve?lat=..&lng=..`. The reviewer pointed out that Uvicorn logs full query strings, so my 'we never log your location' promise was false. Switching to POST fixed it. I then checked the actual server log to confirm."

**Q: Why OpenStreetMap's Nominatim instead of Google Maps?**
A: It's free and needs no API key. The trade-off is a strict usage policy: identify your app in the User-Agent, at most 1 request per second, cache results, no autocomplete. We do all of that with a lock-based throttle and an LRU cache, and we show the required "© OpenStreetMap contributors" credit.

---

## 4. Job sourcing

**Q: Why not just pull from LinkedIn or Indeed?**
A: Neither has a public job-search API, and scraping violates their Terms of Service and breaks whenever their HTML changes. Adzuna aggregates many job boards, has an official free API, and supports "near X within N km" natively. Their terms require attribution, so the page shows "Jobs by Adzuna".

🔁 **Story:** "I planned The Muse as a no-key fallback. The reviewer tested it live and it returns 404. It's dead. Instead of quietly switching to something else, the backend returns a clear 503 'not configured' message. Silent fallbacks hide misconfiguration."

**Q: Searching "software intern" also matches "internal tools engineer". How do you handle that?**
A: Two layers. Adzuna's `what_or=intern internship co-op` and `what_exclude=senior staff...`, then a whole-word regex on titles: `\b(intern|internship|co-?op)\b`. The word boundary `\b` stops "internal" and "international" from matching. There's a test with exactly those titles.

**Q: Why cache searches for 10 minutes?**
A: Free API quotas are limited, and the same search (for example, the "near you" widget on every page load) repeats constantly. Postings don't change minute to minute.

---

## 5. Email tracking: the hardest part

### Consent model
**Core idea:** *just-in-time, narrowly scoped consent.*
- We never ask for Gmail at signup. We ask right after you apply: "Get notified when Stripe replies?"
- Tracking is **per application** (`track_email` flag). Untracked applications are never searched, and a test proves Gmail isn't even queried for them.
- The search is narrow: `from:(stripe.com OR greenhouse-mail.io OR ...) after:<applied date>`.
- We store sender, subject, date and our label. **Never the body.** We request `format=metadata`, so Google doesn't even send it.
- Disconnect revokes the token *at Google* and deletes everything we derived.

### OAuth 2.0 flow (draw this on a whiteboard)
1. Frontend → `GET /email/connect` → backend signs a `state` JWT {user id, purpose, nonce, 10-min expiry} → returns Google's consent URL.
2. User approves **read-only** access on Google's page.
3. Google redirects to **the frontend** `/oauth/gmail?code=…&state=…`.
4. Frontend strips the code from the address bar, then POSTs `{code, state}` **with its login token**.
5. Backend checks the state signature and expiry **and** that `state.sub == current user`, swaps the code for a refresh token, **encrypts** it and stores it.

🔁 **The security story (tell this one):**
> "My first design had Google redirect straight to the backend and trusted the signed `state`. The reviewer showed the attack: I start the flow on *my* account, send you the link, you approve, and now *my* account is reading *your* inbox. A signature proves the server created the state. It doesn't prove the person finishing the flow is the one who started it. The fix was routing the callback through the frontend so the completion request carries the user's own login token, and the backend requires the two identities to match. There's a test where an attacker's state plus a victim's token gets a 403."

**Q: Why encrypt the refresh token instead of hashing it like passwords?**
A: Hashing is one-way. It works for passwords because we only ever *compare*. We need the actual token back to call Google, so it needs reversible encryption: Fernet (AES + HMAC), with the key only in an environment variable. `MultiFernet` supports key rotation: add a new key in front, old tokens still decrypt and get re-encrypted with the new key.

**Q: Why `gmail.readonly` and not the narrower `gmail.metadata` scope?**
A: Counter-intuitively, metadata is *worse* for privacy here. It doesn't allow search queries, so we'd have to list the entire inbox to find company replies. With readonly we search only specific senders. Both are "restricted" scopes, so the app stays in Google's Testing mode (100 test users).

**Q: What were the alternatives to Gmail OAuth?**
- **Forwarding to an inbound address:** better privacy (the user picks exactly what's shared), but needs a domain, inbound mail service, and user-made filters. A good production path.
- **IMAP app password:** full mailbox access including sending, no scoping. Strictly worse.

🔁 **The 7-day expiry story:** "Google expires refresh tokens after 7 days for apps in Testing mode. Without handling that, tracking would silently stop every week. Now an `invalid_grant` flips the connection to `needs_reauth`, creates one notification, and shows a Reconnect banner."

### Matching an email to an application
- Company domain match: `hr@stripe.com` or subdomains like `mail.stripe.com`, but **not** `notstripe.com` or `stripe.com.evil.io` (we check `== domain` or `endswith("." + domain)`).
- Hiring platforms (Greenhouse, Lever, Workday…) send on companies' behalf, so for those we require the company name as a **whole word** in the sender name, address local part, or subject. "Meta" must not match "metadata".
- 🔁 The reviewer found real-world misses: Greenhouse actually sends from `greenhouse-mail.io`, and Lever from `hire.lever.co`.
- Two applications at the same company → attach to the newest and flag it "ambiguous".

### Classifying the email
**Q: Why keyword rules instead of an LLM?**
A: Rules are explainable ("labeled rejection because it contains 'other candidates'"), testable (the test file pins down real examples), free, and the text never leaves our server. An LLM is a reasonable upgrade, but you'd want this rule-based baseline and test suite first to *measure* whether it does better.

**Q: How do you avoid misclassifying?** Scoring: strong phrases count 2 points, weak words count 1, and a label needs 2. So "Unfortunately the interviewer is sick" (one weak word) isn't a rejection. Precedence is offer > rejection > interview > acknowledgment, because rejection emails often mention the interview you had. I also caught one bug myself: "Thanks for applying! Next steps: we'll reach out if we'd like to interview you" scored as an interview, so weak-only interview signals now lose to acknowledgment phrases.

🔁 **Suggest, don't auto-change:**
> "I originally auto-updated the status with an Undo button. The reviewer gave concrete failures: 'pleased to offer you an *interview*' would have matched my offer rule. A false 'Rejected' or 'Offer' does far more harm than one extra click, so the classifier *suggests* and the user applies. Applying re-checks the current status, so an old suggestion can't move an Offer back to Interview."

---

## 6. "Live" updates

**Q: How is it live? Why not WebSockets?**
A: The frontend polls a cheap `/notifications/unread-count` endpoint every 30 seconds, **only while the tab is visible** (Page Visibility API). New data only appears when we check Gmail, every few minutes at best, so a push channel wouldn't feel faster. And Render's free tier sleeps, which kills long-lived connections. WebSockets or SSE earn their complexity for chat or live prices, not here.

**Q: How do background syncs run on a server that sleeps?**
A: Three triggers:
1. A **GitHub Actions cron** hits `/internal/sync-all` every 30 minutes. That request wakes the server *and* does the work. It's protected by a shared secret compared with `hmac.compare_digest` (constant time, which prevents timing attacks).
2. A **"Check now" button**, rate-limited to once a minute.
3. **Opportunistic sync:** if you have the site open and the last sync is over 15 minutes old, the unread-count poll schedules a sync as a `BackgroundTask`. That runs *after* the response is sent, so polling stays fast.

🔁 "I first planned an in-process timer. The reviewer pointed out that on a sleeping free-tier server it would almost never fire."

**Q: Two syncs at once (cron + button). What happens?**
A: Two layers of protection:
- **Lease:** an atomic `UPDATE email_connections SET lease_until = now + 5min WHERE lease is empty or expired`. Only one caller sees `rowcount == 1`. That's a small distributed lock that works on Postgres and SQLite, and a crashed sync's lease simply expires.
- **Unique constraint** on (user, Gmail message id). Each insert runs in a SAVEPOINT, so if a duplicate slips through, only that insert rolls back and no duplicate notification is created.

---

## 7. Database and migrations

**Q: Why add Alembic?**
A: `Base.metadata.create_all()` can create *missing tables* but never adds a column to an existing table. It would silently do nothing, and the app would crash on the new columns. Alembic is version control for the schema: numbered migrations, and an `alembic_version` table recording which ones have run.

🔁 **Q: The prod DB already had tables. How did you baseline?**
A: Migration 0001 recreates the old schema exactly, and on prod I ran `alembic stamp 0001` once ("already applied"), then `upgrade head`. I first considered a "tolerant" 0001 that skipped tables that already existed. The reviewer argued that it hides schema drift, because migrations should be a deterministic history. One audited manual step beat permanent ambiguity.

**Q: How do you know the migrations match the models?** `test_migrations.py` runs Alembic's autogenerate comparison between the migrated test database and `models.py`. Any drift fails CI.

**Q: A bug your tests caught?**
A: Deleting an application should cascade to its emails. It passed in my head but failed in the test, because **SQLite ignores foreign keys unless you run `PRAGMA foreign_keys=ON`**, while Postgres always enforces them. I enabled the pragma so the test database behaves like production. The lesson: the test environment has to mirror prod, or tests give false confidence.

---

## 8. Frontend

| Decision | Why |
|---|---|
| CSS variables (design tokens) instead of inline styles | Inline styles can't do `:hover`, media queries or dark mode; tokens make dark mode a 20-line override |
| `api.js` wrapper | One place for base URL, auth header, JSON, 401 → logout, readable errors (DRY) |
| `ProtectedRoute` + layout route | Login check and nav bar written once. Note: it's UX only. **Security is the backend's 401** |
| `SessionContext` | Avoids prop-drilling user/unread count through every component |
| `useVisiblePolling` custom hook | Reusable "poll only while visible"; a ref holds the latest callback so the timer isn't recreated each render (the exhaustive-deps trap from Session 6/7) |
| Open the job tab *before* `await` | Browsers block pop-ups that don't happen directly in a click handler |
| `useRef` guard in OAuthCallback | React StrictMode runs effects twice in dev; OAuth codes are single-use |
| Accessibility | Labels wired to inputs (`htmlFor`), `role="dialog"`, Escape closes modals, `:focus-visible` rings |

---

## 9. Security checklist (rapid-fire)

- **IDOR:** every query filters `owner_id == current_user.id`; other users' rows return 404 (tested).
- **XSS:** `job_url` must be `http(s)://`, which blocks `javascript:` links (tested). React escapes text by default.
- **CORS:** explicit origins only; `allow_credentials=False` because we use Bearer headers, not cookies.
- **Secrets:** all in env vars; `.env.example` documents them; tokens never returned by any endpoint (tested).
- **Login errors:** same message for wrong email and wrong password (no account enumeration).
- **Known trade-off:** JWT in `localStorage` is readable by injected scripts (XSS). An httpOnly cookie is safer but needs CSRF protection. That's a reasonable next step.

---

## 10. Bugs the second review caught (great "tell me about a bug" answers)

**Q: "Optional" vs "nullable": what's the difference?**
A: In my update schema every field was `Optional`, meaning *you may leave it out*. But Pydantic also accepted an explicit `null`, and I wrote it straight to the database. One `{"status": null}` request stored a NULL, and after that every `GET /applications` for that user crashed, because the response requires a string. The fix is a validator that rejects explicit null for NOT NULL columns, while omitting the field still works. There's now a regression test.

**Q: How do you avoid silent failures in background jobs?**
A: If the Gmail API wasn't enabled, every sync returned 403. The UI said "No new replies yet", and the poll retried every 30 seconds. Now the error is stored and shown in the UI, and a failed sync keeps its lease for 15 minutes. That turns the lock column into a backoff timer, so retries stop hammering a broken dependency.

**Q: Why enforce a privacy rule with a foreign key instead of code?**
A: Disconnect deleted the email data, but a sync already running could insert new rows a second later. Making every email event reference its connection with `ON DELETE CASCADE` means the database both deletes them and *rejects* late inserts. Code can be raced; a constraint can't.

**Q: What's a UI race condition you fixed?**
A: Two job searches in flight: if the older one responds last, it overwrites the newer results. Each search gets an incrementing id, and only the latest id may update state.

---

## 11. What I'd do next (shows judgment)
- Move the JWT to an httpOnly cookie, and add refresh tokens for our own auth.
- Outlook support via Microsoft Graph (`Mail.Read`), behind the same `gmail_client`-style interface.
- Measure classifier accuracy on a labeled set of real emails before considering an LLM.
- Move rate limits and the location cache into Redis once there's more than one server instance.
