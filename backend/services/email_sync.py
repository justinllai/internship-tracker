# ============================================================
# email_sync.py — Check a user's inbox for company replies
# ------------------------------------------------------------
# Called from three places:
#   - POST /email/sync           ("Check now" button)
#   - POST /internal/sync-all    (external cron every ~30 min)
#   - GET  /notifications/unread-count (if the last sync is stale,
#     runs in the background AFTER the response is sent)
#
# Steps for one user:
#   1. Take a LEASE so two syncs for the same user never overlap.
#   2. Decrypt the refresh token → get a 1-hour access token.
#      If Google says the token is dead → mark "needs_reauth" and
#      notify the user (instead of failing silently forever).
#   3. Build ONE Gmail search for all tracked applications:
#        from:(stripe.com OR greenhouse-mail.io OR ...) after:<epoch>
#   4. For each message we haven't seen: fetch metadata, match it
#      to an application, classify it, store an EmailEvent and a
#      Notification that SUGGESTS a status change.
#   5. Refresh the "unopened in Gmail" flag on recent events.
#   6. Release the lease.
# ============================================================

from datetime import timedelta, timezone
from typing import Optional

from sqlalchemy import or_, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import crypto
from models import Application, EmailConnection, EmailEvent, Notification, utcnow
from services import gmail_client
from services.classifier import classify
from services.email_matching import ATS_DOMAINS, gmail_query_terms, pick_application

LEASE_MINUTES = 5
FAILURE_BACKOFF_MINUTES = 15
MAX_LOOKBACK_DAYS = 90       # never search further back than this
TERMS_PER_QUERY = 25         # keep Gmail queries a sane length
UNREAD_RECHECK_DAYS = 14

# Pipeline order, used to decide whether a suggestion makes sense
RANK = {"Saved": 0, "Applied": 1, "Interview": 2, "Offer": 3}

TITLE = {
    "offer": "Possible offer from {c}",
    "interview": "{c} wants to talk — interview request",
    "rejection": "Update from {c}",
    "acknowledgment": "{c} received your application",
    "other": "New email from {c}",
}


def sensible_suggestion(current: str, suggested: Optional[str]) -> Optional[str]:
    """Only suggest moves that make sense: forward in the pipeline,
    or to Rejected from an active state. Never suggest changing an
    Offer or a Rejection — the user has the final word there."""
    if not suggested or suggested == current or current in ("Offer", "Rejected"):
        return None
    if suggested == "Rejected":
        return suggested
    if RANK.get(suggested, -1) > RANK.get(current, -1):
        return suggested
    return None


# ---------- lease (a tiny distributed lock in the database) ----------

def _acquire_lease(db: Session, conn_id: int) -> bool:
    now = utcnow()
    # Atomic "check-and-set": the UPDATE only succeeds if nobody
    # else holds an unexpired lease. Exactly one concurrent caller
    # can see rowcount == 1. Works on Postgres and SQLite.
    result = db.execute(
        update(EmailConnection)
        .where(EmailConnection.id == conn_id)
        .where(or_(EmailConnection.sync_lease_until.is_(None), EmailConnection.sync_lease_until < now))
        .values(sync_lease_until=now + timedelta(minutes=LEASE_MINUTES))
    )
    db.commit()
    return result.rowcount == 1


def _release_lease(db: Session, conn_id: int, backoff_minutes: int = 0) -> None:
    # On a persistent Google error (e.g. Gmail API not enabled) we keep
    # the lease for a while instead of clearing it. That doubles as a
    # BACKOFF: otherwise every 30-second poll from every open tab would
    # retry a sync that is guaranteed to fail.
    until = utcnow() + timedelta(minutes=backoff_minutes) if backoff_minutes else None
    db.execute(update(EmailConnection).where(EmailConnection.id == conn_id).values(sync_lease_until=until))
    db.commit()


# ---------- re-auth handling ----------

def mark_needs_reauth(db: Session, conn: EmailConnection, reason: str) -> None:
    already = conn.status == "needs_reauth"
    conn.status = "needs_reauth"
    conn.last_error = reason[:500]
    if not already:
        db.add(Notification(
            user_id=conn.user_id, kind="reauth_needed",
            title="Reconnect Gmail to keep tracking replies",
            body="Google ended our read-only access (this happens every 7 days while the app is in testing). "
                 "Reconnect in Settings — your tracked applications are unchanged.",
        ))
    db.commit()


# ---------- main entry point ----------

def sync_user(db: Session, user_id: int) -> dict:
    conn = db.query(EmailConnection).filter(EmailConnection.user_id == user_id).first()
    if not conn:
        return {"checked_applications": 0, "new_events": 0, "skipped": "not_connected"}
    if conn.status != "active":
        return {"checked_applications": 0, "new_events": 0, "skipped": "needs_reauth"}
    if not _acquire_lease(db, conn.id):
        db.refresh(conn)
        # Lease held because the last attempt failed → we're backing off
        reason = "backing_off" if conn.last_error else "already_running"
        return {"checked_applications": 0, "new_events": 0, "skipped": reason}

    # Plain int copy: after a rollback, touching conn.id would reload the
    # row — and crash if Disconnect deleted it while we were syncing.
    conn_id = conn.id
    result = None
    try:
        result = _sync_locked(db, conn)
        return result
    finally:
        # If a DB error happened mid-sync the session is unusable until
        # rolled back; without this, releasing the lease would raise and
        # hide the real error. (After a successful sync it's a no-op.)
        db.rollback()
        failed = result is not None and result.get("skipped") == "google_unavailable"
        _release_lease(db, conn_id, FAILURE_BACKOFF_MINUTES if failed else 0)


def _sync_locked(db: Session, conn: EmailConnection) -> dict:
    # 1. Get an access token
    try:
        refresh_token = crypto.decrypt(conn.encrypted_refresh_token)
        rotated = crypto.rotate(conn.encrypted_refresh_token)
        if rotated != conn.encrypted_refresh_token:
            conn.encrypted_refresh_token = rotated       # key rotation, transparently
        access = gmail_client.refresh_access(refresh_token)
    except (crypto.TokenDecryptError, gmail_client.ReauthRequired) as e:
        mark_needs_reauth(db, conn, str(e))
        return {"checked_applications": 0, "new_events": 0, "skipped": "needs_reauth"}
    except gmail_client.GmailError as e:
        conn.last_error = str(e)[:500]
        db.commit()
        return {"checked_applications": 0, "new_events": 0, "skipped": "google_unavailable"}

    # 2. Which applications has the user consented to track?
    apps = (db.query(Application)
            .filter(Application.owner_id == conn.user_id,
                    Application.track_email.is_(True),
                    Application.status != "Saved")
            .all())

    new_events = 0
    try:
        if apps:
            new_events = _scan(db, conn, access, apps)
        _refresh_unread_flags(db, conn, access)
    except gmail_client.ReauthRequired as e:
        mark_needs_reauth(db, conn, str(e))
        return {"checked_applications": len(apps), "new_events": new_events, "skipped": "needs_reauth"}
    except gmail_client.GmailError as e:
        conn.last_error = str(e)[:500]
        db.commit()
        return {"checked_applications": len(apps), "new_events": new_events, "skipped": "google_unavailable"}

    conn.last_synced_at = utcnow()
    conn.last_error = None
    db.commit()
    return {"checked_applications": len(apps), "new_events": new_events, "skipped": None}


def _search_after_epoch(apps) -> int:
    # Search from the earliest application date (minus a day of
    # slack), but never more than MAX_LOOKBACK_DAYS back.
    earliest = min((a.applied_at or a.date_applied) for a in apps) - timedelta(days=1)
    floor = utcnow() - timedelta(days=MAX_LOOKBACK_DAYS)
    start = max(earliest, floor)
    # Gmail's after:YYYY/MM/DD is midnight PACIFIC time; epoch
    # seconds avoid that timezone trap entirely.
    return _epoch(start)


def _epoch(dt) -> int:
    return int(dt.replace(tzinfo=timezone.utc).timestamp())


def _collect_ids(access: str, apps, after: int, seen: set, out: list) -> None:
    terms = sorted({t for a in apps for t in gmail_query_terms(a)})
    # Chunk terms so a user with 100 applications doesn't build one
    # enormous query. ATS domains go in every chunk.
    for i in range(0, max(len(terms), 1), TERMS_PER_QUERY):
        chunk = terms[i:i + TERMS_PER_QUERY] + ATS_DOMAINS
        query = f"from:({' OR '.join(chunk)}) after:{after}"
        for mid in gmail_client.list_message_ids(access, query):
            if mid not in seen:
                seen.add(mid)
                out.append(mid)


def _scan(db: Session, conn: EmailConnection, access: str, apps) -> int:
    # INCREMENTAL search. Only applications that are newly tracked
    # (or everything, on the very first sync) get the full look-back
    # to their application date. Everything else only searches since
    # the last successful sync (minus a day of slack). Without this,
    # every sync would re-read the same hiring-platform emails forever.
    last = conn.last_synced_at
    if last is None:
        new_apps, old_apps = list(apps), []
    else:
        slack = last - timedelta(hours=1)
        new_apps = [a for a in apps if a.track_email_since is None or a.track_email_since >= slack]
        old_apps = [a for a in apps if a not in new_apps]

    message_ids: list = []
    seen: set = set()
    if new_apps:
        _collect_ids(access, new_apps, _search_after_epoch(new_apps), seen, message_ids)
    if old_apps:
        _collect_ids(access, old_apps, _epoch(last - timedelta(days=1)), seen, message_ids)

    if not message_ids:
        return 0

    # Skip messages we've already recorded (cheap DB check, saves API calls)
    known = {row[0] for row in db.query(EmailEvent.provider_message_id)
             .filter(EmailEvent.user_id == conn.user_id,
                     EmailEvent.provider_message_id.in_(message_ids))}

    created = 0
    for mid in message_ids:
        if mid in known:
            continue
        msg = gmail_client.get_message_meta(access, mid)
        app, ambiguous = pick_application(apps, msg)
        if app is None:
            continue    # e.g. a Greenhouse email about a company we're not tracking
        # Ignore mail from before this specific application
        if msg["received_at"] < (app.applied_at or app.date_applied) - timedelta(days=1):
            continue

        label, suggested = classify(msg["subject"], msg.get("snippet", ""))
        event = EmailEvent(
            user_id=conn.user_id, application_id=app.id, connection_id=conn.id, provider_message_id=mid,
            from_name=(msg["from_name"] or "")[:200] or None, from_address=msg["from_address"],
            subject=msg["subject"], received_at=msg["received_at"],
            classification=label, is_unread=msg["is_unread"], ambiguous=ambiguous,
        )
        # SAVEPOINT: if another sync inserted this message a split
        # second ago, the UNIQUE constraint fires — roll back just
        # this one insert and move on, no duplicate notification.
        try:
            with db.begin_nested():
                db.add(event)
                db.flush()
        except IntegrityError:
            continue

        db.add(Notification(
            user_id=conn.user_id, application_id=app.id, email_event_id=event.id,
            kind="email_reply",
            title=TITLE[label].format(c=app.company_name),
            body=msg["subject"] or "(no subject)",
            suggested_status=sensible_suggestion(app.status, suggested),
        ))
        created += 1

    db.commit()
    return created


def _refresh_unread_flags(db: Session, conn: EmailConnection, access: str) -> None:
    """Keep "Unopened in Gmail" accurate: once the user reads the
    email in Gmail, the badge disappears here too."""
    since = utcnow() - timedelta(days=UNREAD_RECHECK_DAYS)
    events = (db.query(EmailEvent)
              .filter(EmailEvent.user_id == conn.user_id, EmailEvent.is_unread.is_(True),
                      EmailEvent.received_at >= since)
              .limit(50).all())
    for ev in events:
        flag = gmail_client.get_unread_flag(access, ev.provider_message_id)
        if flag is not None:
            ev.is_unread = flag
    db.commit()


def sync_all(session_factory) -> dict:
    """Used by the cron endpoint: sync every active connection,
    each in its own DB session so one failure can't break the rest."""
    totals = {"users": 0, "new_events": 0, "errors": 0}
    with session_factory() as db:
        user_ids = [row[0] for row in db.query(EmailConnection.user_id).filter(EmailConnection.status == "active")]
    for uid in user_ids:
        try:
            with session_factory() as db:
                result = sync_user(db, uid)
            totals["users"] += 1
            totals["new_events"] += result["new_events"]
        except Exception:     # noqa: BLE001 — keep going for other users
            totals["errors"] += 1
    return totals
