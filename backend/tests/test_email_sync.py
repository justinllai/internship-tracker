# End-to-end inbox sync with a FAKE Gmail (no network).
from datetime import datetime, timedelta

import pytest

import crypto
from models import Application, EmailConnection, EmailEvent, Notification, utcnow
from services import email_sync, gmail_client


class FakeGmail:
    """Stands in for Google. Holds a fake inbox; records queries."""

    def __init__(self, monkeypatch):
        self.inbox = {}
        self.queries = []
        self.refresh_error = None
        monkeypatch.setattr(gmail_client, "refresh_access", self.refresh_access)
        monkeypatch.setattr(gmail_client, "list_message_ids", self.list_message_ids)
        monkeypatch.setattr(gmail_client, "get_message_meta", self.get_message_meta)
        monkeypatch.setattr(gmail_client, "get_unread_flag", self.get_unread_flag)

    def add(self, mid, address, subject, snippet="", name="", unread=True, received=None):
        self.inbox[mid] = {
            "id": mid, "from_address": address, "from_name": name, "subject": subject, "snippet": snippet,
            "received_at": received or utcnow(), "is_unread": unread,
        }

    def refresh_access(self, refresh_token):
        if self.refresh_error:
            raise self.refresh_error
        assert refresh_token == "real-refresh-token"
        return "access-token"

    def list_message_ids(self, access, query, max_results=100):
        self.queries.append(query)
        return list(self.inbox)

    def get_message_meta(self, access, mid):
        return dict(self.inbox[mid])

    def get_unread_flag(self, access, mid):
        return self.inbox[mid]["is_unread"] if mid in self.inbox else None


@pytest.fixture
def gmail(monkeypatch):
    return FakeGmail(monkeypatch)


@pytest.fixture
def tracked(db, make_user):
    """A user with Gmail connected and one tracked Stripe application."""
    user_id, headers = make_user()
    db.add(EmailConnection(user_id=user_id, email_address="ada@gmail.com",
                           encrypted_refresh_token=crypto.encrypt("real-refresh-token"), status="active"))
    app = Application(owner_id=user_id, company_name="Stripe", position="SWE Intern", status="Applied",
                      company_domain="stripe.com", track_email=True,
                      applied_at=utcnow() - timedelta(days=3), date_applied=utcnow() - timedelta(days=3))
    db.add(app)
    db.commit()
    return user_id, headers, app.id


def test_detects_reply_and_suggests_status(db, gmail, tracked, client):
    user_id, headers, app_id = tracked
    gmail.add("m1", "recruiting@stripe.com", "Interview invitation", "Please share your availability")
    gmail.add("m2", "promo@shop.com", "Big sale")          # unrelated → ignored

    result = email_sync.sync_user(db, user_id)
    assert result["new_events"] == 1

    # One combined query, domain + ATS list, epoch-seconds date
    assert "stripe.com" in gmail.queries[0] and "greenhouse-mail.io" in gmail.queries[0]
    assert "after:" in gmail.queries[0]

    note = db.query(Notification).one()
    assert note.suggested_status == "Interview"
    # Suggest-only: the application itself is NOT changed automatically
    assert db.get(Application, app_id).status == "Applied"

    # The API exposes it and the user can accept it
    assert client.get("/notifications/unread-count", headers=headers).json()["count"] == 1
    r = client.post(f"/notifications/{note.id}/apply", headers=headers)
    assert r.status_code == 200 and r.json()["status"] == "Interview"
    # Second click: already resolved
    assert client.post(f"/notifications/{note.id}/apply", headers=headers).status_code == 409


def test_no_email_bodies_stored(db, gmail, tracked):
    user_id, _, _ = tracked
    gmail.add("m1", "recruiting@stripe.com", "Update", "SECRET BODY TEXT unfortunately other candidates")
    email_sync.sync_user(db, user_id)
    ev = db.query(EmailEvent).one()
    stored = " ".join(str(v) for v in vars(ev).values())
    assert "SECRET BODY TEXT" not in stored
    assert ev.classification == "rejection"


def test_second_sync_creates_no_duplicates(db, gmail, tracked):
    user_id, _, _ = tracked
    gmail.add("m1", "recruiting@stripe.com", "Interview invitation")
    email_sync.sync_user(db, user_id)
    email_sync.sync_user(db, user_id)
    assert db.query(EmailEvent).count() == 1
    assert db.query(Notification).count() == 1


def test_untracked_applications_are_never_searched(db, gmail, tracked):
    user_id, _, app_id = tracked
    db.get(Application, app_id).track_email = False
    db.commit()
    gmail.add("m1", "recruiting@stripe.com", "Interview invitation")
    result = email_sync.sync_user(db, user_id)
    assert gmail.queries == []          # Gmail wasn't even searched
    assert result["new_events"] == 0


def test_old_mail_from_before_applying_is_ignored(db, gmail, tracked):
    user_id, _, _ = tracked
    gmail.add("m1", "recruiting@stripe.com", "Interview invitation", received=utcnow() - timedelta(days=30))
    assert email_sync.sync_user(db, user_id)["new_events"] == 0


def test_expired_token_marks_needs_reauth_once(db, gmail, tracked, client):
    user_id, headers, _ = tracked
    gmail.refresh_error = gmail_client.ReauthRequired("invalid_grant")
    assert email_sync.sync_user(db, user_id)["skipped"] == "needs_reauth"
    assert email_sync.sync_user(db, user_id)["skipped"] == "needs_reauth"
    assert db.query(Notification).filter_by(kind="reauth_needed").count() == 1
    assert client.get("/me", headers=headers).json()["gmail"]["status"] == "needs_reauth"


def test_lease_blocks_overlapping_syncs(db, gmail, tracked):
    user_id, _, _ = tracked
    conn = db.query(EmailConnection).one()
    conn.sync_lease_until = utcnow() + timedelta(minutes=5)     # someone else is syncing
    db.commit()
    assert email_sync.sync_user(db, user_id)["skipped"] == "already_running"
    # an EXPIRED lease (crashed sync) doesn't block forever
    conn.sync_lease_until = utcnow() - timedelta(minutes=1)
    db.commit()
    assert email_sync.sync_user(db, user_id)["skipped"] is None


def test_unread_flag_refreshes_after_user_opens_email(db, gmail, tracked):
    user_id, _, _ = tracked
    gmail.add("m1", "recruiting@stripe.com", "Interview invitation", unread=True)
    email_sync.sync_user(db, user_id)
    assert db.query(EmailEvent).one().is_unread is True
    gmail.inbox["m1"]["is_unread"] = False                      # user read it in Gmail
    email_sync.sync_user(db, user_id)
    db.expire_all()
    assert db.query(EmailEvent).one().is_unread is False


def test_stale_suggestion_cannot_move_status_backwards(db, gmail, tracked, client):
    user_id, headers, app_id = tracked
    gmail.add("m1", "recruiting@stripe.com", "Interview invitation")
    email_sync.sync_user(db, user_id)
    note = db.query(Notification).one()
    client.put(f"/applications/{app_id}", headers=headers, json={"status": "Offer"})
    assert client.post(f"/notifications/{note.id}/apply", headers=headers).status_code == 409
    assert client.get(f"/applications/{app_id}", headers=headers).json()["status"] == "Offer"


def test_deleting_application_cascades(db, gmail, tracked, client):
    user_id, headers, app_id = tracked
    gmail.add("m1", "recruiting@stripe.com", "Interview invitation")
    email_sync.sync_user(db, user_id)
    assert client.delete(f"/applications/{app_id}", headers=headers).status_code == 200
    db.expire_all()
    assert db.query(EmailEvent).count() == 0
    assert db.query(Notification).count() == 0


@pytest.mark.parametrize("current,suggested,expected", [
    ("Applied", "Interview", "Interview"),
    ("Applied", "Rejected", "Rejected"),
    ("Interview", "Interview", None),
    ("Offer", "Rejected", None),        # never touch an offer
    ("Rejected", "Interview", None),
    ("Interview", "Applied", None),     # never backwards
])
def test_sensible_suggestion(current, suggested, expected):
    assert email_sync.sensible_suggestion(current, suggested) == expected


def test_cron_endpoint_requires_secret(client, gmail, tracked):
    assert client.post("/internal/sync-all").status_code == 401
    assert client.post("/internal/sync-all", headers={"X-Cron-Secret": "wrong"}).status_code == 401
    r = client.post("/internal/sync-all", headers={"X-Cron-Secret": "test-cron-secret"})
    assert r.status_code == 200 and r.json()["users"] == 1


# ---------- regressions from review round 2 ----------

def test_later_syncs_only_search_since_last_sync(db, gmail, tracked):
    user_id, _, app_id = tracked
    db.get(Application, app_id).track_email_since = utcnow() - timedelta(days=3)
    db.commit()
    email_sync.sync_user(db, user_id)                 # first sync: full look-back
    first_after = int(gmail.queries[0].rsplit("after:", 1)[1])
    gmail.queries.clear()
    email_sync.sync_user(db, user_id)                 # second sync: incremental
    second_after = int(gmail.queries[0].rsplit("after:", 1)[1])
    assert second_after > first_after                 # narrower window


def test_persistent_google_error_backs_off_and_is_visible(db, gmail, tracked, client, monkeypatch):
    user_id, headers, _ = tracked
    def broken(*args, **kwargs):
        raise gmail_client.GmailError("Gmail API error 403")
    monkeypatch.setattr(gmail_client, "list_message_ids", broken)
    assert email_sync.sync_user(db, user_id)["skipped"] == "google_unavailable"
    # Immediately retrying is refused (backoff), with a clear reason
    assert email_sync.sync_user(db, user_id)["skipped"] == "backing_off"
    # ...and the user can SEE what went wrong
    assert "403" in client.get("/me", headers=headers).json()["gmail"]["last_error"]


def test_deleting_connection_cascades_events_in_the_database(db, gmail, tracked):
    user_id, _, _ = tracked
    gmail.add("m1", "recruiting@stripe.com", "Interview invitation")
    email_sync.sync_user(db, user_id)
    assert db.query(EmailEvent).count() == 1
    # Raw SQL delete: proves the DATABASE enforces it, not our Python code
    from sqlalchemy import text
    db.execute(text("DELETE FROM email_connections"))
    db.commit()
    assert db.query(EmailEvent).count() == 0


def test_gmail_list_follows_pagination(monkeypatch):
    pages = {None: {"messages": [{"id": "a"}], "nextPageToken": "p2"},
             "p2": {"messages": [{"id": "b"}]}}
    monkeypatch.setattr(gmail_client, "_gmail_get",
                        lambda token, path, params: pages[params.get("pageToken")])
    assert gmail_client.list_message_ids("tok", "from:x") == ["a", "b"]
