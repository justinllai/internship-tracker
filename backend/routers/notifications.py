# ============================================================
# notifications.py — The bell icon
# ------------------------------------------------------------
# The frontend polls /notifications/unread-count every 30s.
# That cheap endpoint ALSO kicks off a background inbox sync if
# the user's last sync is stale — so simply having the site open
# keeps tracking fresh, even when the cron job is late.
#
# BackgroundTasks run AFTER the response is sent, so the poll
# stays fast; the new notifications show up on the next poll.
# ============================================================

from datetime import timedelta
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

import config
from database import SessionLocal, get_db
from deps import get_current_user
from models import Notification, User, utcnow
from schemas import ApplicationResponse, NotificationResponse
from services import email_sync

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _serialize(n: Notification) -> NotificationResponse:
    return NotificationResponse(
        id=n.id, kind=n.kind, title=n.title, body=n.body,
        application_id=n.application_id, suggested_status=n.suggested_status,
        suggestion_resolved=n.suggestion_resolved, is_read=n.is_read, created_at=n.created_at,
        email=n.email_event, application_status=n.application.status if n.application else None,
    )


def _owned(db: Session, notification_id: int, user: User) -> Notification:
    n = db.query(Notification).filter(Notification.id == notification_id, Notification.user_id == user.id).first()
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")
    return n


def _background_sync(user_id: int):
    # A background task must open its OWN session: the request's
    # session is closed as soon as the response is sent.
    with SessionLocal() as db:
        try:
            email_sync.sync_user(db, user_id)
        except Exception:     # noqa: BLE001 — never crash the worker
            pass


@router.get("", response_model=List[NotificationResponse])
def list_notifications(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rows = (db.query(Notification)
            .options(joinedload(Notification.email_event), joinedload(Notification.application))
            .filter(Notification.user_id == current_user.id)
            .order_by(Notification.created_at.desc(), Notification.id.desc())
            .limit(100).all())
    return [_serialize(n) for n in rows]


@router.get("/unread-count")
def unread_count(background: BackgroundTasks, db: Session = Depends(get_db),
                 current_user: User = Depends(get_current_user)):
    conn = current_user.email_connection
    now = utcnow()
    if (config.gmail_enabled() and conn and conn.status == "active"
            # don't queue work while a sync is running or backing off
            and (conn.sync_lease_until is None or conn.sync_lease_until < now)
            and (conn.last_synced_at is None
                 or conn.last_synced_at < utcnow() - timedelta(minutes=config.OPPORTUNISTIC_SYNC_MINUTES))):
        background.add_task(_background_sync, current_user.id)

    count = db.query(Notification).filter(Notification.user_id == current_user.id,
                                          Notification.is_read.is_(False)).count()
    return {"count": count}


@router.post("/read-all")
def read_all(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db.query(Notification).filter(Notification.user_id == current_user.id,
                                  Notification.is_read.is_(False)).update({"is_read": True})
    db.commit()
    return {"message": "ok"}


@router.post("/{notification_id}/read", response_model=NotificationResponse)
def mark_read(notification_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    n = _owned(db, notification_id, current_user)
    n.is_read = True
    db.commit()
    return _serialize(n)


@router.post("/{notification_id}/apply", response_model=ApplicationResponse)
def apply_suggestion(notification_id: int, db: Session = Depends(get_db),
                     current_user: User = Depends(get_current_user)):
    """The user accepts our suggested status ("Interview")."""
    n = _owned(db, notification_id, current_user)
    if not n.suggested_status or n.suggestion_resolved or not n.application:
        raise HTTPException(status_code=409, detail="This suggestion is no longer available")
    # The user may have changed the status by hand since we made the
    # suggestion (e.g. already set "Offer"). Don't move it backwards.
    if email_sync.sensible_suggestion(n.application.status, n.suggested_status) is None:
        n.suggestion_resolved = True
        db.commit()
        raise HTTPException(status_code=409,
                            detail=f"Status is already {n.application.status} — suggestion no longer applies")
    n.application.status = n.suggested_status
    n.suggestion_resolved = True
    n.is_read = True
    db.commit()
    db.refresh(n.application)
    return n.application


@router.post("/{notification_id}/dismiss", response_model=NotificationResponse)
def dismiss_suggestion(notification_id: int, db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    n = _owned(db, notification_id, current_user)
    n.suggestion_resolved = True
    n.is_read = True
    db.commit()
    return _serialize(n)
