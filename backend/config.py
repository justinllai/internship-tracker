# ============================================================
# config.py — Every environment variable, read in ONE place
# ------------------------------------------------------------
# Before: auth.py and database.py each called os.getenv().
# As we add Gmail, Adzuna and cron secrets, scattering getenv
# calls everywhere makes it impossible to answer "what config
# does this app need?" Now the answer is: read this file.
#
# Optional features (job search, Gmail) turn themselves OFF
# gracefully when their keys are missing, instead of crashing
# the whole server. `*_enabled()` helpers make that explicit.
# ============================================================

import os
from dotenv import load_dotenv

load_dotenv()

# --- Core (required) ---
DATABASE_URL = os.getenv("DATABASE_URL")
SECRET_KEY = os.getenv("SECRET_KEY")

# Where the React app lives. Used for CORS and as the OAuth
# redirect target (Google sends the user back to the FRONTEND).
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000").rstrip("/")

# Extra allowed origins, comma-separated (e.g. a Vercel preview URL)
EXTRA_CORS_ORIGINS = [o.strip().rstrip("/") for o in os.getenv("EXTRA_CORS_ORIGINS", "").split(",") if o.strip()]

# --- Job search (Adzuna) ---
ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY")
ADZUNA_COUNTRY = os.getenv("ADZUNA_COUNTRY", "us")

# --- Gmail OAuth ---
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

# Fernet keys used to encrypt stored refresh tokens.
# Comma-separated, NEWEST FIRST — this allows key rotation:
# add a new key at the front, old tokens still decrypt with the
# old key and get re-encrypted with the new one (see crypto.py).
TOKEN_ENCRYPTION_KEYS = [k.strip() for k in os.getenv("TOKEN_ENCRYPTION_KEYS", "").split(",") if k.strip()]

# --- Background sync ---
# Shared secret the external cron job (GitHub Actions) sends in
# the X-Cron-Secret header to trigger /internal/sync-all.
CRON_SECRET = os.getenv("CRON_SECRET")

# How stale a user's last sync must be before visiting the site
# triggers a fresh one in the background.
OPPORTUNISTIC_SYNC_MINUTES = int(os.getenv("OPPORTUNISTIC_SYNC_MINUTES", "15"))

# Contact string sent to OpenStreetMap's Nominatim in the
# User-Agent header — their usage policy requires apps to
# identify themselves. Generic by default; no personal info.
GEOCODER_USER_AGENT = os.getenv("GEOCODER_USER_AGENT", "internship-tracker-student-project/1.0")


def jobs_enabled() -> bool:
    return bool(ADZUNA_APP_ID and ADZUNA_APP_KEY)


def gmail_enabled() -> bool:
    return bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET and TOKEN_ENCRYPTION_KEYS)


def gmail_redirect_uri() -> str:
    # Must exactly match an "Authorized redirect URI" in the
    # Google Cloud console. It points at the FRONTEND on purpose:
    # the frontend then POSTs the code to the backend together
    # with the user's login token (see routers/email_routes.py).
    return f"{FRONTEND_URL}/oauth/gmail"
