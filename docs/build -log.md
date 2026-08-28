Session Recap — Internship Tracker: Project Skeleton
Date: June 16, 2026

Time spent: ~1 hour

WHAT
Built the complete project skeleton for the Internship Tracker app — a full-stack web application with a React frontend, FastAPI backend, and a working health endpoint pushed to GitHub.

WHY

Every real software project needs a solid foundation before any features are built. Rushing into features without structure leads to messy, hard-to-maintain code
Setting up the skeleton first means every future session has a clean, organized place to add code
Pushing to GitHub immediately means your work is never lost and employers can see your progress from day one
Doing this yourself (not copying a template) means you understand every file in your project


HOW
Step 1 — Verified tools were installed
bashnode --version    # v20.10.0
npm --version     # 10.2.3
python --version  # 3.14.5
These three tools power everything — Node/npm for React, Python for FastAPI.
Step 2 — Created the folder structure
bashmkdir internship-tracker
cd internship-tracker
mkdir backend
mkdir frontend
Separating backend and frontend keeps concerns clean — two separate "worlds" that talk to each other through APIs.
Step 3 — Set up the React frontend
bashcd frontend
npx create-react-app frontend
npm start
React runs on http://localhost:3000. The spinning logo confirmed it was alive.
Step 4 — Set up the FastAPI backend
bashcd backend
python -m venv venv       # created isolated Python environment
venv\Scripts\activate     # activated it (saw "(venv)" appear)
pip install fastapi uvicorn
pip freeze > requirements.txt
The virtual environment is like a separate Python "room" just for this project — keeps dependencies isolated and professional.
Step 5 — Created backend/main.py
pythonfrom fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(CORSMiddleware, ...)

@app.get("/health")
def health_check():
    return {"status": "ok"}

FastAPI() creates the app
CORSMiddleware gives React permission to talk to FastAPI
/health endpoint confirms the server is alive

Step 6 — Ran the backend server
bashuvicorn main:app --reload
Confirmed working at:

http://localhost:8000/health → {"status": "ok"}
http://localhost:8000/docs → auto-generated API docs (free with FastAPI!)

Step 7 — Created .gitignore at root
venv/
__pycache__/
node_modules/
frontend/build/
.env
.vscode/
Prevents large/sensitive folders from being uploaded to GitHub.
Step 8 — Pushed to GitHub
bashgit init
git add .
git commit -m "initial project skeleton: React frontend + FastAPI backend"
git branch -M main
git remote add origin https://github.com/justinllai/internship-tracker.git
git push -u origin main

KEY CONCEPTS LEARNED
ConceptWhat it means in plain EnglishVirtual environmentA separate Python "room" so packages don't conflict between projectsCORSA browser security rule — middleware gives React permission to talk to FastAPIPortAn address on your computer — React uses 3000, FastAPI uses 8000200 OKHTTP status code meaning "success"404 Not FoundHTTP status code meaning "that URL doesn't exist".gitignoreA list of files/folders Git should never uploadrequirements.txtA list of all Python packages this project needs--reload flagTells Uvicorn to restart automatically when you save a file

DECISIONS MADE
DecisionWhat we choseWhyFrontendReactIndustry standard, shows up in every job postingBackendFastAPIYou already know Python, same patterns as NBA appDatabaseSQLiteReal persistent storage, no setup complexity for V1AuthUser accountsMost impressive for portfolio — shows real engineeringRepo visibilityPublicEmployers can


Session Recap — Internship Tracker: Authentication
Date: June 17, 2026

Time spent: ~1.5 hours

WHAT
Built a complete authentication system for the Internship Tracker backend — including database setup, password hashing, and JWT token login.

WHY
Authentication is the foundation of any multi-user app. Without it, anyone could see anyone else's applications. Building this yourself (instead of using a third-party service) shows interviewers you understand how security actually works under the hood.

HOW
Step 1 — Installed new packages
bashpip install sqlalchemy passlib[bcrypt] python-jose[cryptography] pydantic[email]
pip install bcrypt==4.0.1  # downgraded due to bcrypt 5.0.0 + passlib incompatibility
Step 2 — Created database.py

Set up SQLite connection using SQLAlchemy
Created engine (the pipeline to the database)
Created SessionLocal (a factory for database sessions)
Created Base (the foundation all models inherit from)
Created get_db() — a FastAPI dependency that opens and closes a session per request using yield

Step 3 — Created models.py

Defined the User class inheriting from Base
Columns: id, email, username, hashed_password, is_active
unique=True on email and username prevents duplicates
nullable=False makes fields required

Step 4 — Created schemas.py

UserCreate — shape of data coming IN for register (email, username, password)
UserLogin — shape of data coming IN for login (email, password)
UserResponse — shape of data going OUT (no password ever returned)
Token — shape of JWT response after login
TokenData — what's stored inside the token

Step 5 — Created auth.py

hash_password() — hashes plain text password with bcrypt (truncated to 72 chars)
verify_password() — compares plain text to stored hash without decrypting
create_access_token() — creates a signed JWT with expiry time
verify_token() — decodes and validates a JWT, returns email or None

Step 6 — Updated main.py

Added Base.metadata.create_all() to auto-create tables on startup
Added /register endpoint — checks for duplicate email/username, hashes password, saves user
Added /login endpoint — finds user, verifies password, returns JWT token


KEY CONCEPTS LEARNED
ConceptPlain English explanationORMWrite Python instead of SQL — SQLAlchemy translates itModelA Python class that represents a database tableSchemaDefines the shape of data coming in/out of the APIPassword hashingScrambles password so it can never be reversed — industry standardbcryptThe hashing algorithm — one-way, slow by design to resist attacksJWTA signed token like a wristband — proves who you are without hitting the databaseyield in get_db()Opens a session, gives it to the route, closes it automatically when done400 Bad RequestClient sent invalid data (e.g. duplicate email)401 UnauthorizedWrong credentials

BUGS DEBUGGED
BugCauseFixImportError: email-validator not installedEmailStr needs an extra packagepip install pydantic[email]ValueError: password cannot be longer than 72 bytesbcrypt 5.0.0 incompatible with passlibDowngraded to bcrypt==4.0.1 and added [:72] slice

DECISIONS MADE
DecisionChoiceWhyPassword storagebcrypt hash only, never plain textIndustry standard — irreversibleToken expiry30 minutesBalances security and convenienceDuplicate checkBoth email and usernamePrevents confusion and account conflictsError message for wrong loginSame message for bad email or bad passwordPrevents attackers from guessing valid emails


Session Recap — Internship Tracker: Applications CRUD
Date: June 23, 2026

Time spent: ~1.5 hours

WHAT
Built the core feature of the app — a complete CRUD API for internship applications, protected by JWT authentication so users can only see and modify their own data.

WHY
CRUD is the foundation of every real application. Without it the app has no actual functionality — users couldn't add, view, update, or delete their applications. This is also the session where the backend became fully functional as a standalone API.

HOW
Step 1 — Added Application model to models.py

Created Application table with: id, company_name, position, status, deadline, notes, date_applied, owner_id
Added ForeignKey("users.id") to link each application to its owner
Added relationship() on both User and Application so SQLAlchemy can navigate between them

Step 2 — Added Application schemas to schemas.py

ApplicationCreate — required: company_name, position. Optional: status, deadline, notes
ApplicationUpdate — everything Optional so users can update just one field
ApplicationResponse — includes system fields: id, date_applied, owner_id

Step 3 — Added get_current_user dependency to main.py

Uses OAuth2PasswordBearer to extract token from request header
Calls verify_token() to decode the JWT and get the email
Looks up the user in the database by email
Returns the user object or raises 401 Unauthorized

Step 4 — Built 5 application endpoints
POST   /applications          → create new application
GET    /applications          → get all MY applications
GET    /applications/{id}     → get one specific application
PUT    /applications/{id}     → update one field or all fields
DELETE /applications/{id}     → permanently delete
Step 5 — Tested all 5 endpoints using PowerShell

Got token via login
Created Google Software Engineer Intern application
Updated status from "Applied" to "Interview"
Deleted the application
Verified deletion with GET all returning empty


KEY CONCEPTS LEARNED
ConceptPlain EnglishCRUDThe 4 operations every app needs: Create, Read, Update, DeleteProtected routeAn endpoint that requires a valid JWT token to accessDepends(get_current_user)Runs the security check automatically before the endpointowner_id checkEnsures users can only access their own data — never others'exclude_unset=TrueOnly updates fields the user actually sent — leaves the rest alonePath parameter {id}A variable in the URL that identifies which resource to act on401 UnauthorizedToken is missing, invalid, or expired404 Not FoundThe resource doesn't exist or doesn't belong to this userSwagger UI /docsAuto-generated API testing interface — free with FastAPI

DECISIONS MADE
DecisionChoiceWhyAlways filter by owner_idYes, on every querySecurity — prevents users accessing each other's datadate_applied auto-setdefault=datetime.utcnowUser shouldn't have to set this manuallyowner_id from tokenNot from request bodyPrevents users from creating applications for other usersAll update fields OptionalYesUsers should only have to send what they're changing


Session Recap — Internship Tracker: React Frontend
Date: June 24, 2026

Time spent: ~1 hour

WHAT
Built the React frontend with Login and Register pages that connect to the FastAPI backend. Users can now register and log in through a real UI instead of PowerShell commands.

WHY
The backend was fully functional but unusable for real people. The frontend is what turns an API into an actual product. This session is where the app started feeling real — a user can now open a browser, create an account, and log in.

HOW
Step 1 — Created folder structure
frontend/src/
├── pages/
│   ├── Login.js
│   └── Register.js
├── App.js
└── index.js
Step 2 — Built Login.js

4 pieces of state: email, password, error, loading
handleSubmit sends POST to /login with email and password
On success: stores JWT token in localStorage
On failure: displays error message from FastAPI
Loading state disables button while waiting for response

Step 3 — Built Register.js

5 pieces of state: email, username, password, error, success, loading
handleSubmit sends POST to /register
On success: shows success screen with "Go to Login" button
On failure: displays error message (e.g. "Email already registered")

Step 4 — Installed React Router
bashnpm install react-router-dom
Step 5 — Updated App.js with routing

BrowserRouter enables client-side routing
/ → Login page
/register → Register page
* → redirects unknown URLs to login

Step 6 — Added navigation between pages

useNavigate hook lets us navigate programmatically
"Sign up" on Login → goes to /register
"Sign in" on Register → goes to /

Step 7 — Fixed git submodule issue

Create React App created its own .git folder inside frontend/
This made git treat frontend as a submodule instead of a regular folder
Fixed by deleting frontend/.git and re-adding with git rm -r --cached frontend


KEY CONCEPTS LEARNED
ConceptPlain EnglishReact componentA function that returns JSX (HTML-like UI)useStateStores data that can change — when it changes React re-rendersJSXHTML-like syntax inside JavaScript — React's way of building UIe.preventDefault()Stops form from reloading the page on submitfetch()JavaScript's built-in tool for making HTTP requestslocalStorageBrowser storage that persists across page refreshes — where we store the JWT tokenresponse.okTrue if status code is 200-299 (success)React RouterLibrary for client-side navigation — no page reloadsuseNavigateHook that gives us a function to navigate between pagesClient-side routingURL changes without browser reloading — makes apps feel fastGit submoduleA git repo inside another git repo — caused issues, fixed by removing inner .git

DECISIONS MADE
DecisionChoiceWhyToken storagelocalStoragePersists across page refreshes so users stay logged inError displayInline in the formBetter UX than alertsLoading stateDisable button while waitingPrevents double submissionsNavigationReact RouterIndustry standard for React apps

BUGS DEBUGGED
BugCauseFixFrontend not pushing to GitHubCreate React App created its own .git inside frontend/ making it a submoduleDeleted frontend/.git, ran git rm -r --cached frontend, re-added



Session Recap — Internship Tracker: Dashboard
Date: June 26, 2026

Time spent: ~1 hour

WHAT
Built the Dashboard page — the core of the app. Users can now log in, see all their applications, add new ones, update statuses, and delete applications through a real UI.

WHY
The app was fully functional on the backend but had no real user interface for managing applications. The Dashboard is what turns this from an API into an actual product people can use. This is the session where everything came together — frontend talking to backend, real data being saved and displayed.

HOW
Step 1 — Created Dashboard.js
Key pieces:

useEffect — runs on page load, checks for token, fetches applications
fetchApplications() — GET request to /applications with JWT token in header
handleCreateApp() — POST request to create new application
handleStatusChange() — PUT request to update just the status
handleDelete() — DELETE request to remove an application
handleLogout() — clears token from localStorage, redirects to login
getStatusColor() — returns color based on status (blue/yellow/green/red)

Step 2 — Updated App.js

Added import Dashboard from './pages/Dashboard'
Added <Route path="/dashboard" element={<Dashboard />} />

Step 3 — Updated Login.js

Replaced alert('Login successful!') with navigate('/dashboard')
Now users are automatically sent to Dashboard after login


KEY CONCEPTS LEARNED
ConceptPlain EnglishuseEffectRuns code when component loads — like "on page load do this"[] dependency arrayEmpty array means useEffect runs only once on mountFrontend protected routeCheck for token on load — redirect to login if missinglocalStorage.getItemReads stored token so we can attach it to requestsAuthorization: BearerHow we send JWT token in every protected requestresponse.status === 401Token expired — clear it and redirect to loginOptimistic UI updateUpdate local state immediately without refetching from backendapplications.map()Loop through applications and render a card for each oneapplications.filter()Count applications by status for the stats barEmpty stateA friendly message when there's no data yet{...app, status: newStatus}Spread operator — copy all fields but override status

DECISIONS MADE
DecisionChoiceWhyToken checkOn every protected page loadSecurity — can't access dashboard without loginUI update after CRUDUpdate local state, don't refetchFaster UX — no extra network request neededStatus colorsBlue/Yellow/Green/RedInstantly communicate meaning without readingEmpty state message"No applications yet. Click + Add Application"Better UX than a blank pageLogoutClear token + redirect to loginToken gone means next visit requires fresh login

## Session 5 — August 10, 2026
**Focus:** Deployment prep — secrets management + SQLite → Postgres migration

### What I did
- Installed `python-dotenv` and moved `SECRET_KEY` (auth.py) and `DATABASE_URL` (database.py) out of hardcoded values into a `.env` file, loaded via `os.getenv()`
- Generated a new cryptographically secure `SECRET_KEY` using Python's `secrets.token_hex(32)`, replacing the old placeholder value
- Created a Neon Postgres database and migrated `database.py` from SQLite to Postgres:
  - Removed `connect_args={"check_same_thread": False}` (SQLite-only, not needed for Postgres)
  - Installed `psycopg2-binary` as the Postgres driver SQLAlchemy needed
- Verified the full auth + database flow end-to-end against the live Postgres database:
  - `/register` successfully creates a user (confirmed via API response AND direct SQL query)
  - Duplicate-email protection correctly returns 400
  - `/login` successfully returns a valid JWT using the new `SECRET_KEY`

### Bugs hit and fixed
- **Phantom `.env` file:** VS Code sidebar showed `.env` as present, but it didn't actually exist on disk (`Get-ChildItem -Force` returned nothing). Recreated it via terminal (`New-Item .env`) and verified with byte-count checks before proceeding.
- **Zombie uvicorn process:** After multiple restarts during debugging, a stale process (PID 33144) left a backlog of `ESTABLISHED`/`CLOSE_WAIT` connections on port 8000, silently blocking new requests (including `/health`, which has zero dependencies). Diagnosed with `netstat -ano | findstr :8000`; resolved after a clean restart.
- **Duplicate `requirements.txt`:** An extra `requirements.txt` had been accidentally generated in the repo root (from running `pip freeze` in the wrong directory). Deleted — `backend/requirements.txt` is the only one that matters for deployment.

### Key concepts reinforced
- Why secrets can't live in committed code once a project touches GitHub/production (JWT secret = full auth bypass if leaked)
- SQLite (file-based) vs. Postgres (networked server) — why connection strings, drivers, and thread-safety handling differ between them
- Why hosting platforms with ephemeral filesystems make SQLite unsuitable for deployment

### Verified working
- [x] `.env` correctly excluded from git (`git status` confirmed no `.env` in tracked/untracked files)
- [x] `/register`, `/login` tested against live Neon Postgres database
- [x] Data persistence confirmed via direct SQL query, independent of the API

### Next session
- Update CORS config for production frontend URL
- Deploy backend to Render
- Deploy frontend to Vercel/Netlify

## Session 6/7 — August 13 & 26, 2026
**Focus:** Full production deployment — backend to Render, frontend to Vercel, end-to-end live testing

### What I did

**Backend deployment (Render)**
- Created Render account with GitHub access scoped to only `internship-tracker` (least-privilege)
- Configured web service: Python 3, Root Directory `backend`, Build Command `pip install -r requirements.txt`, Start Command `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Added `DATABASE_URL` and `SECRET_KEY` as Render environment variables (separate copy from local `.env` — Render can't read a file that was never pushed to GitHub)
- Verified `/health`, `/docs`, `/register`, `/login` all work against the live Neon database

**Frontend environment setup**
- Created `frontend/.env` with `REACT_APP_API_URL` pointing to the Render backend URL
- Fixed a gap in `frontend/.gitignore` — Create React App's default template only ignores `.env.local` variants, not plain `.env`; added `.env` explicitly
- Replaced hardcoded `http://localhost:8000` with `apiUrl` (`process.env.REACT_APP_API_URL`) across `Login.js`, `Register.js`, and all four `fetch()` calls in `Dashboard.js`
- Verified locally: React dev server (`localhost:3000`) successfully talked to the live Render backend end-to-end before ever touching Vercel

**Frontend deployment (Vercel)**
- Created Vercel account, GitHub access scoped to `internship-tracker` only
- Set Root Directory to `frontend` (Vercel initially tried to deploy `backend` too as a second service — not needed, already live on Render)
- Added `REACT_APP_API_URL` as a Vercel environment variable *before* the first build (required — React bakes env vars into static files at build time, not read live like a backend)
- Enabled 2FA on the Vercel account

**CORS fix for production**
- Updated `allow_origins` in `main.py` to include the real deployed frontend origin alongside `localhost:3000`
- Deliberately avoided `allow_origins=["*"]` due to the `allow_credentials=True` + wildcard CSRF anti-pattern

### Bugs hit and fixed
- **Wrong initial config on both Render and Vercel:** both platforms defaulted to Node.js/`yarn` settings for the FastAPI backend since they auto-detect generically; had to manually correct Language, Build Command, and Start Command on Render.
- **ESLint build failure on Vercel (`react-hooks/exhaustive-deps`):** `Dashboard.js`'s mount-only `useEffect` was missing `fetchApplications` and `navigate` from its dependency array. Locally this is just a warning; Vercel's build sets `CI=true`, which upgrades CRA warnings to hard errors. Diagnosed that `navigate` is stable (safe to ignore) but `fetchApplications` is recreated every render (adding it would cause an infinite fetch loop) — used `// eslint-disable-next-line react-hooks/exhaustive-deps` rather than blindly satisfying the linter.
- **Wrong Vercel production domain assumed:** guessed `internship-tracker-jlai1.vercel.app` by pattern-matching Render's URL style instead of checking Vercel's dashboard. The real stable domain (`internship-tracker-chi-orcin.vercel.app`) was different, found under the project's actual Domains section — cost a round of CORS debugging before catching it.
- **Stale CORS/browser cache confusion:** briefly mistook a cached preflight rejection for a still-broken deploy; confirmed via Render's deploy history that the fix was already live, then isolated the real issue (wrong domain) by testing in the correct location.

### Key concepts reinforced
- `--reload` / `0.0.0.0` / `$PORT`: why local dev flags don't carry over to production, and what each one actually does
- CORS is enforced entirely by the browser, not the server — a blocked request never reaches FastAPI at all
- Environment variables: backend reads them live at runtime (`os.getenv`, restart picks up changes); frontend bakes them in permanently at build time (`process.env`, requires a full rebuild to pick up changes)
- Least-privilege GitHub access scoping, applied consistently across Neon, Render, and Vercel

### Verified working
- [x] Backend live and independently reachable on Render (`/health`, `/docs`, `/register`, `/login`)
- [x] Frontend live on Vercel at the correct production domain
- [x] Full register → login flow tested successfully on the actual live site (not localhost, not `/docs`)
- [x] CORS correctly scoped to real origins only, no wildcard

### Next session
- Test full CRUD cycle (create/edit status/delete an application) on the live production site
- Consider centralizing frontend API calls into a single file instead of three separate hardcoded-then-fixed locations
- Ready to share with friends once CRUD is confirmed — flag Render free-tier cold start (~30-60s first request after idle) as expected behavior, not a bug