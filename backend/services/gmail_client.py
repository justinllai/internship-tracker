# ============================================================
# gmail_client.py — Talk to Google OAuth + the Gmail API
# ------------------------------------------------------------
# We use plain HTTP (httpx) instead of Google's SDK so every
# step of OAuth 2.0 is visible:
#
#   1. build_auth_url()   → send the user to Google's consent page
#   2. exchange_code()    → trade the one-time ?code for tokens
#   3. refresh_access()   → trade the long-lived REFRESH token for
#                           a short-lived (1 hour) ACCESS token
#   4. list/get messages  → call Gmail with "Bearer <access token>"
#   5. revoke()           → tell Google to kill the token on disconnect
#
# Scope: gmail.readonly — read-only. We can't send, delete or
# modify mail. (gmail.metadata would be even narrower, but it
# doesn't allow search queries, so we'd have to list the ENTIRE
# inbox to find company replies — worse for privacy, not better.)
#
# What we read per message: From, Subject, internalDate, labels
# (for UNREAD) and Google's ~200-char snippet. format=metadata
# means Google never even sends us the body.
# ============================================================

from datetime import datetime, timezone
from email.utils import parseaddr
from typing import Optional
from urllib.parse import urlencode

import httpx

import config

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"
GMAIL = "https://gmail.googleapis.com/gmail/v1/users/me"
SCOPE = "https://www.googleapis.com/auth/gmail.readonly"


class GmailError(Exception):
    pass


class ReauthRequired(GmailError):
    """Refresh token expired/revoked — the user must reconnect.
    Happens every 7 days while the Google app is in Testing mode."""


def build_auth_url(state: str) -> str:
    params = {
        "client_id": config.GOOGLE_CLIENT_ID,
        "redirect_uri": config.gmail_redirect_uri(),
        "response_type": "code",
        "scope": SCOPE,
        # offline + consent = Google returns a REFRESH token, so we
        # can check mail later without the user being present.
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
        "state": state,
    }
    return f"{AUTH_URL}?{urlencode(params)}"


def _post_token(data: dict) -> dict:
    try:
        resp = httpx.post(TOKEN_URL, data=data, timeout=10.0)
    except httpx.HTTPError as e:
        raise GmailError("Could not reach Google") from e
    body = resp.json() if resp.content else {}
    if resp.status_code != 200:
        # invalid_grant = code/refresh token expired or revoked
        if body.get("error") == "invalid_grant":
            raise ReauthRequired(body.get("error_description", "invalid_grant"))
        raise GmailError(f"Google token endpoint error: {body.get('error', resp.status_code)}")
    return body


def exchange_code(code: str) -> dict:
    return _post_token({
        "code": code,
        "client_id": config.GOOGLE_CLIENT_ID,
        "client_secret": config.GOOGLE_CLIENT_SECRET,
        "redirect_uri": config.gmail_redirect_uri(),
        "grant_type": "authorization_code",
    })


def refresh_access(refresh_token: str) -> str:
    body = _post_token({
        "refresh_token": refresh_token,
        "client_id": config.GOOGLE_CLIENT_ID,
        "client_secret": config.GOOGLE_CLIENT_SECRET,
        "grant_type": "refresh_token",
    })
    return body["access_token"]


def revoke(token: str) -> None:
    # Best effort: even if Google is unreachable we still delete
    # our copy, and the user can revoke at myaccount.google.com.
    try:
        httpx.post(REVOKE_URL, params={"token": token}, timeout=10.0)
    except httpx.HTTPError:
        pass


def _gmail_get(access_token: str, path: str, params=None) -> dict:
    try:
        resp = httpx.get(f"{GMAIL}{path}", params=params,
                         headers={"Authorization": f"Bearer {access_token}"}, timeout=15.0)
    except httpx.HTTPError as e:
        raise GmailError("Could not reach Gmail") from e
    if resp.status_code == 401:
        raise ReauthRequired("Gmail rejected the access token")
    if resp.status_code >= 400:
        raise GmailError(f"Gmail API error {resp.status_code}")
    return resp.json()


def get_profile_email(access_token: str) -> Optional[str]:
    return _gmail_get(access_token, "/profile").get("emailAddress")


def list_message_ids(access_token: str, query: str, max_total: int = 300) -> list:
    """Follow Gmail's pagination (nextPageToken) so a busy inbox doesn't
    hide an older company reply, but cap the total so one sync can't
    run away."""
    ids, page_token = [], None
    while len(ids) < max_total:
        params = {"q": query, "maxResults": min(100, max_total - len(ids))}
        if page_token:
            params["pageToken"] = page_token
        data = _gmail_get(access_token, "/messages", params)
        ids.extend(m["id"] for m in data.get("messages", []))
        page_token = data.get("nextPageToken")
        if not page_token:
            break
    return ids


def get_message_meta(access_token: str, message_id: str) -> dict:
    # params as a list of tuples because metadataHeaders repeats
    data = _gmail_get(access_token, f"/messages/{message_id}", [
        ("format", "metadata"),
        ("metadataHeaders", "From"),
        ("metadataHeaders", "Subject"),
    ])
    headers = {h["name"].lower(): h["value"] for h in data.get("payload", {}).get("headers", [])}
    from_name, from_address = parseaddr(headers.get("from", ""))
    # internalDate = when Gmail received it, in epoch MILLISECONDS.
    # More reliable than parsing the free-form "Date" header.
    received = datetime.fromtimestamp(int(data.get("internalDate", "0")) / 1000, tz=timezone.utc)
    return {
        "id": data["id"],
        "from_name": from_name or None,
        "from_address": from_address.lower() or None,
        "subject": headers.get("subject", "")[:500],
        # Not formally documented for format=metadata, so default to ""
        "snippet": data.get("snippet", ""),
        "received_at": received.replace(tzinfo=None),
        "is_unread": "UNREAD" in data.get("labelIds", []),
    }


def get_unread_flag(access_token: str, message_id: str) -> Optional[bool]:
    """Re-check whether the user has opened a message since we saw it."""
    try:
        data = _gmail_get(access_token, f"/messages/{message_id}", [("format", "minimal")])
    except ReauthRequired:
        raise
    except GmailError:
        return None
    return "UNREAD" in data.get("labelIds", [])
