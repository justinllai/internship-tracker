# The Gmail connect flow, especially the security checks.
from urllib.parse import parse_qs, urlparse

import pytest

import crypto
from auth import create_oauth_state, verify_oauth_state
from models import EmailConnection
from services import gmail_client


@pytest.fixture
def fake_google(monkeypatch):
    calls = {"revoked": []}
    monkeypatch.setattr(gmail_client, "exchange_code",
                        lambda code: {"refresh_token": "real-refresh-token", "access_token": "access"})
    monkeypatch.setattr(gmail_client, "get_profile_email", lambda access: "ada@gmail.com")
    monkeypatch.setattr(gmail_client, "revoke", lambda token: calls["revoked"].append(token))
    return calls


def test_connect_url_has_readonly_scope_and_state(client, make_user):
    user_id, h = make_user()
    url = client.get("/email/connect", headers=h).json()["auth_url"]
    params = parse_qs(urlparse(url).query)
    assert params["scope"] == ["https://www.googleapis.com/auth/gmail.readonly"]
    assert params["access_type"] == ["offline"]
    assert params["redirect_uri"] == ["http://localhost:3000/oauth/gmail"]
    assert verify_oauth_state(params["state"][0]) == user_id


def test_complete_stores_encrypted_token(client, make_user, db, fake_google):
    user_id, h = make_user()
    r = client.post("/email/oauth/complete", headers=h,
                    json={"code": "abc", "state": create_oauth_state(user_id)})
    assert r.status_code == 200, r.text
    assert r.json()["connected"] is True and r.json()["email_address"] == "ada@gmail.com"
    conn = db.query(EmailConnection).one()
    assert "real-refresh-token" not in conn.encrypted_refresh_token     # encrypted at rest
    assert crypto.decrypt(conn.encrypted_refresh_token) == "real-refresh-token"
    # ...and never returned by the API
    assert "refresh" not in r.text


def test_cannot_finish_someone_elses_connect_link(client, make_user, fake_google):
    attacker_id, _ = make_user("attacker@example.com")
    _, victim = make_user("victim@example.com")
    r = client.post("/email/oauth/complete", headers=victim,
                    json={"code": "abc", "state": create_oauth_state(attacker_id)})
    assert r.status_code == 403


def test_garbage_or_login_token_is_not_a_valid_state(client, make_user, fake_google):
    user_id, h = make_user()
    login_token = h["Authorization"].split()[1]
    for bad in ("garbage", login_token):
        r = client.post("/email/oauth/complete", headers=h, json={"code": "abc", "state": bad})
        assert r.status_code == 400


def test_disconnect_revokes_and_deletes(client, make_user, db, fake_google):
    user_id, h = make_user()
    client.post("/email/oauth/complete", headers=h, json={"code": "abc", "state": create_oauth_state(user_id)})
    r = client.delete("/email/connection", headers=h)
    assert r.status_code == 200
    assert fake_google["revoked"] == ["real-refresh-token"]
    assert db.query(EmailConnection).count() == 0


def test_manual_sync_is_rate_limited(client, make_user, monkeypatch):
    _, h = make_user()
    from services import email_sync
    monkeypatch.setattr(email_sync, "sync_user", lambda db, uid: {"checked_applications": 0, "new_events": 0, "skipped": None})
    assert client.post("/email/sync", headers=h).status_code == 200
    assert client.post("/email/sync", headers=h).status_code == 429
