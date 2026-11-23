# ============================================================
# main.py — The entry point for our FastAPI backend server
# Think of this file as the "front desk": it creates the app,
# sets up CORS, and plugs in every group of routes (routers).
#
# The actual endpoints now live in routers/:
#   auth_routes.py    /register /login /me /me/location
#   applications.py   /applications CRUD
#   location_jobs.py  /location/resolve  /jobs/search
#   email_routes.py   /email/* (Gmail connect, sync, disconnect)
#   notifications.py  /notifications/*
#   internal.py       /internal/sync-all (cron only)
#
# Database tables are no longer created here with
# Base.metadata.create_all(). create_all can CREATE missing
# tables but can never ADD a column to an existing one — so it
# silently does nothing when models change. Schema changes are
# now Alembic migrations (alembic/versions/), applied with
# `alembic upgrade head` before the server starts.
# ============================================================

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import config
from routers import applications, auth_routes, email_routes, internal, location_jobs, notifications

app = FastAPI(title="Internship Tracker API")


# ============================================================
# CORS MIDDLEWARE
# ============================================================
# Only our own frontends may call this API from a browser.
# allow_credentials is False: we authenticate with a Bearer
# header, not cookies, so the browser never needs to send
# credentials cross-origin. (Fewer permissions = smaller risk.)
origins = {"http://localhost:3000", "https://internship-tracker-chi-orcin.vercel.app", config.FRONTEND_URL}
origins.update(config.EXTRA_CORS_ORIGINS)

app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(origins),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health_check():
    return {"status": "ok"}


# ============================================================
# ROUTERS
# ============================================================

app.include_router(auth_routes.router)
app.include_router(applications.router)
app.include_router(location_jobs.router)
app.include_router(email_routes.router)
app.include_router(notifications.router)
app.include_router(internal.router)
