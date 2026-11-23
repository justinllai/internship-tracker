# Setup guide: deploying the redesign + live tracking

Work through this list in order. The app still runs if you skip the optional parts. Those features just switch off with a clear message ("Job search isn't configured…").

---

## 1. Database migration (required, do this FIRST)

Your Neon database already has `users` and `applications`, created by the old `create_all()`. Tell Alembic that the baseline already exists, then apply the new migration.

From `backend/`, with your real `DATABASE_URL` in `.env`:

```bash
venv\Scripts\activate
pip install -r requirements.txt
alembic stamp 0001      # ONE TIME ONLY: "the prod DB already matches the baseline"
alembic upgrade head    # adds new columns + tables (0002)
alembic current         # should print: 0002 (head)
```

> Why `stamp`? Migration 0001 *creates* `users` and `applications`. Running it against a database that already has them would fail. `stamp` records "0001 is already applied" without running it. You only need this once. Never stamp a brand-new empty database; just run `upgrade head`.

## 2. Render (backend)

**Start Command** → change it to:

```
alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port $PORT
```

Now every deploy applies any new migrations before the server starts. If nothing is pending, it does nothing.

**Environment** → add these (see `backend/.env.example` for how to generate each one):

| Key | Required? | Value |
|---|---|---|
| `FRONTEND_URL` | yes | `https://internship-tracker-chi-orcin.vercel.app` |
| `ADZUNA_APP_ID`, `ADZUNA_APP_KEY` | for Jobs page | from developer.adzuna.com (free) |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | for Gmail | from step 3 |
| `TOKEN_ENCRYPTION_KEYS` | for Gmail | a Fernet key; **back it up somewhere safe**. If you lose it, every user has to reconnect Gmail |
| `CRON_SECRET` | for scheduled sync | random string, same value as in GitHub (step 5) |

## 3. Google Cloud (for Gmail tracking)

1. console.cloud.google.com → create a project → **APIs & Services → Library** → enable **Gmail API**.
2. **OAuth consent screen**: External, app name "Internship Tracker", add scope `.../auth/gmail.readonly`. Leave it in **Testing** mode and add yourself (and any friends, max 100) as **Test users**.
3. **Credentials → Create OAuth client ID → Web application**:
   - Authorized redirect URIs:
     - `http://localhost:3000/oauth/gmail` (local dev)
     - `https://internship-tracker-chi-orcin.vercel.app/oauth/gmail` (prod)
4. Copy the client ID and secret into Render (and into your local `.env` for testing).

**Testing-mode limits you should know about and be ready to explain:**
- Test users see a "Google hasn't verified this app" screen. Click *Continue*.
- Google expires test-mode access after **7 days**. The app detects this, shows "Reconnect Gmail", and creates a notification, so tracking never fails silently.
- Leaving Testing mode needs Google verification. `gmail.readonly` is a *restricted* scope, so that includes a paid security assessment. That's not realistic for a portfolio project, and Testing mode is the right call.

## 4. Vercel (frontend)

Nothing new to configure. `frontend/vercel.json` makes Vercel serve the React app for every path, so Google's redirect to `/oauth/gmail` loads the app instead of a 404. Redeploying picks it up automatically.

## 5. GitHub (scheduled sync + CI)

Repo → **Settings → Secrets and variables → Actions → New repository secret**:
- `BACKEND_URL` = your Render URL (no trailing slash)
- `CRON_SECRET` = the same value you put on Render

Then go to **Actions → "Sync tracked inboxes" → Run workflow** to test it once by hand. The **Tests** workflow runs by itself on every push.

## 6. Local development

```bash
# backend
cd backend && venv\Scripts\activate
pip install -r requirements-dev.txt
alembic upgrade head
uvicorn main:app --reload
python -m pytest -q          # 68 tests, no network needed

# frontend
cd frontend
npm start
npm test                      # 7 tests
```

## 7. Verify on the live site

- [ ] Register → lands on the tracker
- [ ] Jobs → "Use my current location" → browser asks permission → shows your city
- [ ] Jobs → type a ZIP → shows a city (and nothing more specific)
- [ ] Apply to a posting → new tab opens + "Get notified when X replies?" dialog
- [ ] Connect Gmail → Google consent → back on Settings with "Gmail connected!"
- [ ] Send yourself a test email *from the company domain you entered* (or test with a domain you control) → "Check now" → it appears under Updates with a suggested status
- [ ] Settings → Disconnect → myaccount.google.com/permissions no longer lists the app
