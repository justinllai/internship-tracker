# ============================================================
# internal.py — Endpoint for the scheduled (cron) sync
# ------------------------------------------------------------
# Render's free tier puts the server to sleep after ~15 minutes
# without traffic, so an in-process timer would never fire while
# you're away. Instead, an EXTERNAL scheduler (a GitHub Actions
# workflow, .github/workflows/sync-inbox.yml) calls this endpoint
# every 30 minutes. That request both wakes the server AND
# triggers the sync.
#
# It's protected by a shared secret header instead of a user
# JWT, because the caller is a machine, not a user.
# hmac.compare_digest compares in constant time so an attacker
# can't guess the secret one character at a time by measuring
# how long the comparison takes (a "timing attack").
# ============================================================

import hmac

from fastapi import APIRouter, Header, HTTPException

import config
from database import SessionLocal
from services import email_sync

router = APIRouter(prefix="/internal", tags=["internal"], include_in_schema=False)


@router.post("/sync-all")
def sync_all(x_cron_secret: str = Header(default="")):
    if not config.CRON_SECRET or not config.gmail_enabled():
        raise HTTPException(status_code=503, detail="Scheduled sync is not configured")
    if not hmac.compare_digest(x_cron_secret.encode(), config.CRON_SECRET.encode()):
        raise HTTPException(status_code=401, detail="Bad cron secret")
    return email_sync.sync_all(SessionLocal)
