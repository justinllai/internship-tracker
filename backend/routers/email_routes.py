# ============================================================
# email_routes.py — Connect / sync / disconnect Gmail
# ------------------------------------------------------------
# The OAuth flow, step by step:
#
#  [browser]  clicks "Connect Gmail"
#      │  GET /email/connect  (with login token)
#      ▼
#  [backend]  makes a signed `state` = "user #42, expires in 10 min"
#             returns Google's consent URL containing that state
#      │
#      ▼
#  [Google]   user approves read-only access
#             redirects to FRONTEND_URL/oauth/gmail?code=...&state=...
#      │
#      ▼
#  [browser]  OAuthCallback page POSTs {code, state} to
#             /email/oauth/complete WITH the login token
#      │
#      ▼
#  [backend]  checks: state signature valid? not expired?
#             AND state's user == the logged-in user?   ← key check
#             exchanges code → refresh token, encrypts, stores it
#
# Why does Google redirect to the FRONTEND instead of straight to
# the backend? Because a redirect can't carry our Authorization
# header. Going through the frontend lets us prove the person
# finishing the flow is the same logged-in user who started it.
# That blocks "login CSRF"-style attacks where someone tricks you
# into linking YOUR inbox to THEIR account.
# ============================================================

import threading
import time

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

import config
import crypto
from auth import create_oauth_state, verify_oauth_state
from database import get_db
from deps import get_current_user
from models import EmailConnection, EmailEvent, Notification, User
from routers.auth_routes import gmail_status
from schemas import GmailStatus, OAuthCompleteRequest, SyncResult
from services import email_sync, gmail_client

router = APIRouter(prefix="/email", tags=["email tracking"])

# "Check now" rate limit: once per 60s per user. In-memory is fine
# for our single Render instance; with several servers you'd keep
# this in Redis or the database instead.
MANUAL_SYNC_COOLDOWN = 60
_last_manual_sync: dict = {}
_cooldown_lock = threading.Lock()


def _require_configured():
    if not config.gmail_enabled():
        raise HTTPException(status_code=503,
                            detail="Email tracking isn't configured on this server (missing Google OAuth settings).")


@router.get("/status", response_model=GmailStatus)
def status_(current_user: User = Depends(get_current_user)):
    return gmail_status(current_user)


@router.get("/connect")
def connect(current_user: User = Depends(get_current_user)):
    _require_configured()
    return {"auth_url": gmail_client.build_auth_url(create_oauth_state(current_user.id))}


@router.post("/oauth/complete", response_model=GmailStatus)
def oauth_complete(body: OAuthCompleteRequest, db: Session = Depends(get_db),
                   current_user: User = Depends(get_current_user)):
    _require_configured()

    state_user = verify_oauth_state(body.state)
    if state_user is None:
        raise HTTPException(status_code=400, detail="This connection link expired. Please try connecting again.")
    if state_user != current_user.id:
        # Someone else's connect link — refuse.
        raise HTTPException(status_code=403, detail="This connection was started by a different account.")

    try:
        tokens = gmail_client.exchange_code(body.code)
    except gmail_client.GmailError:
        raise HTTPException(status_code=400, detail="Google didn't accept the authorization. Please try again.")

    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=400, detail="Google didn't return offline access. Please try connecting again.")

    # We also need the access token right now to learn which inbox
    # this is. We don't store access tokens — they expire in an hour.
    try:
        address = gmail_client.get_profile_email(tokens["access_token"])
    except gmail_client.GmailError:
        address = None

    conn = current_user.email_connection
    if conn is None:
        conn = EmailConnection(user_id=current_user.id)
        db.add(conn)
    conn.provider = "gmail"
    conn.email_address = address
    conn.encrypted_refresh_token = crypto.encrypt(refresh_token)
    conn.status = "active"
    conn.last_error = None

    # A fresh connection resolves any "please reconnect" notices
    db.query(Notification).filter(Notification.user_id == current_user.id,
                                  Notification.kind == "reauth_needed",
                                  Notification.is_read.is_(False)).update({"is_read": True})
    db.commit()
    db.refresh(current_user)
    return gmail_status(current_user)


@router.post("/sync", response_model=SyncResult)
def sync_now(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _require_configured()
    now = time.monotonic()
    with _cooldown_lock:
        last = _last_manual_sync.get(current_user.id, 0)
        if now - last < MANUAL_SYNC_COOLDOWN:
            wait = int(MANUAL_SYNC_COOLDOWN - (now - last)) + 1
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                                detail=f"Checked very recently — try again in {wait}s.")
        _last_manual_sync[current_user.id] = now
    return email_sync.sync_user(db, current_user.id)


@router.delete("/connection")
def disconnect(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    conn = current_user.email_connection
    if conn:
        # 1. Ask Google to revoke the token (best effort)
        try:
            gmail_client.revoke(crypto.decrypt(conn.encrypted_refresh_token))
        except Exception:     # noqa: BLE001 — still delete our copy below
            pass
        # 2. Delete everything we derived from the inbox
        db.query(Notification).filter(Notification.user_id == current_user.id,
                                      Notification.kind.in_(["email_reply", "reauth_needed"])).delete(synchronize_session=False)
        db.query(EmailEvent).filter(EmailEvent.user_id == current_user.id).delete(synchronize_session=False)
        db.delete(conn)
        db.commit()
    return {"message": "Gmail disconnected and all email-derived data deleted"}
