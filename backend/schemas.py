# ============================================================
# schemas.py — Defines the shape of data coming IN and OUT
# of our API endpoints.
#
# - models.py  = how data is stored in the DATABASE
# - schemas.py = how data looks when sent to/from the API
#
# Pydantic validates incoming data automatically: a status of
# "Banana" or a 10,000-character company name is rejected with
# a 422 before our code ever runs.
# ============================================================

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


# The only statuses an application can be set to.
# Literal[...] = "must be exactly one of these strings".
# We validate on INPUT only. Responses use plain `str` so that
# any legacy row with an unexpected value still loads instead of
# crashing the whole list with a 500.
Status = Literal["Saved", "Applied", "Interview", "Offer", "Rejected"]


# ============================================================
# USER SCHEMAS
# ============================================================

class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=30)
    # 8+ chars for NEW accounts. (Login doesn't enforce this, so
    # older accounts with shorter passwords can still sign in.)
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    is_active: bool
    location_label: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class GmailStatus(BaseModel):
    configured: bool                 # does the SERVER have Google credentials?
    connected: bool                  # has THIS user linked Gmail?
    status: Optional[str] = None     # "active" | "needs_reauth"
    email_address: Optional[str] = None
    last_synced_at: Optional[datetime] = None
    last_error: Optional[str] = None


class MeResponse(UserResponse):
    gmail: GmailStatus
    jobs_configured: bool


class LocationUpdate(BaseModel):
    # null clears the saved location
    location_label: Optional[str] = Field(default=None, max_length=120)


# ============================================================
# TOKEN SCHEMAS
# ============================================================

class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None


# ============================================================
# APPLICATION SCHEMAS
# ============================================================

def _clean_domain(value: Optional[str]) -> Optional[str]:
    """Accept 'https://www.Stripe.com/jobs' and store 'stripe.com'."""
    if value is None:
        return None
    v = value.strip().lower()
    for prefix in ("https://", "http://"):
        if v.startswith(prefix):
            v = v[len(prefix):]
    v = v.split("/")[0].split("@")[-1]
    if v.startswith("www."):
        v = v[4:]
    if not v:
        return None
    if "." not in v or " " in v:
        raise ValueError("company_domain should look like 'company.com'")
    return v


def _http_url_only(value: Optional[str]) -> Optional[str]:
    # Block javascript: and other schemes — this URL is rendered as
    # a clickable link, so "javascript:alert(1)" would be an XSS hole.
    if value and not value.strip().lower().startswith(("http://", "https://")):
        raise ValueError("job_url must start with http:// or https://")
    return value.strip() if value else value


class ApplicationCreate(BaseModel):
    company_name: str = Field(min_length=1, max_length=120)
    position: str = Field(min_length=1, max_length=160)
    status: Status = "Applied"
    deadline: Optional[datetime] = None
    notes: Optional[str] = Field(default=None, max_length=2000)
    company_domain: Optional[str] = Field(default=None, max_length=255)
    job_url: Optional[str] = Field(default=None, max_length=2048)
    location: Optional[str] = Field(default=None, max_length=120)
    source: Optional[str] = Field(default="manual", max_length=30)
    external_id: Optional[str] = Field(default=None, max_length=128)
    track_email: bool = False

    @field_validator("company_domain")
    @classmethod
    def clean_domain(cls, v):
        return _clean_domain(v)

    @field_validator("job_url")
    @classmethod
    def http_only(cls, v):
        return _http_url_only(v)


class ApplicationUpdate(BaseModel):
    company_name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    position: Optional[str] = Field(default=None, min_length=1, max_length=160)
    status: Optional[Status] = None
    deadline: Optional[datetime] = None
    notes: Optional[str] = Field(default=None, max_length=2000)
    company_domain: Optional[str] = Field(default=None, max_length=255)
    job_url: Optional[str] = Field(default=None, max_length=2048)
    location: Optional[str] = Field(default=None, max_length=120)
    track_email: Optional[bool] = None

    # "Optional" here means "you may leave it OUT of the request",
    # NOT "you may set it to null". These columns can't be NULL in the
    # database — a null status once stored would crash every later
    # GET /applications. Validators only run on values actually sent,
    # so omitting the field is still fine; sending null is a 422.
    @field_validator("company_name", "position", "status", "track_email", mode="before")
    @classmethod
    def no_explicit_null(cls, v, info):
        if v is None:
            raise ValueError(f"{info.field_name} cannot be null")
        return v

    @field_validator("company_domain")
    @classmethod
    def clean_domain(cls, v):
        return _clean_domain(v)

    @field_validator("job_url")
    @classmethod
    def http_only(cls, v):
        return _http_url_only(v)


class EmailEventResponse(BaseModel):
    id: int
    from_name: Optional[str] = None
    from_address: Optional[str] = None
    subject: Optional[str] = None
    received_at: datetime
    classification: str
    is_unread: bool
    ambiguous: bool

    model_config = ConfigDict(from_attributes=True)


class ApplicationResponse(BaseModel):
    id: int
    company_name: str
    position: str
    status: str
    deadline: Optional[datetime] = None
    notes: Optional[str] = None
    date_applied: datetime
    applied_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    owner_id: int
    company_domain: Optional[str] = None
    job_url: Optional[str] = None
    location: Optional[str] = None
    source: Optional[str] = None
    external_id: Optional[str] = None
    track_email: bool = False
    email_events: List[EmailEventResponse] = []

    model_config = ConfigDict(from_attributes=True)


# ============================================================
# LOCATION + JOBS
# ============================================================

class LocationResolveRequest(BaseModel):
    # Either coordinates OR free text. Sent in a POST body (not the
    # URL) so it never lands in server access logs.
    lat: Optional[float] = Field(default=None, ge=-90, le=90)
    lng: Optional[float] = Field(default=None, ge=-180, le=180)
    q: Optional[str] = Field(default=None, max_length=200)


class LocationResponse(BaseModel):
    label: str              # "San Jose, CA"
    city: str
    state: Optional[str] = None


class JobResult(BaseModel):
    external_id: str
    title: str
    company: str
    location: str
    url: str
    posted_at: Optional[datetime] = None
    description: Optional[str] = None
    salary: Optional[str] = None
    source: str
    already_tracked: bool = False


class JobSearchResponse(BaseModel):
    source: str
    location: str
    count: int
    results: List[JobResult]


# ============================================================
# EMAIL + NOTIFICATIONS
# ============================================================

class OAuthCompleteRequest(BaseModel):
    code: str = Field(max_length=2048)
    state: str = Field(max_length=4096)


class SyncResult(BaseModel):
    checked_applications: int
    new_events: int
    skipped: Optional[str] = None


class NotificationResponse(BaseModel):
    id: int
    kind: str
    title: str
    body: Optional[str] = None
    application_id: Optional[int] = None
    suggested_status: Optional[str] = None
    suggestion_resolved: bool
    is_read: bool
    created_at: datetime
    email: Optional[EmailEventResponse] = None
    application_status: Optional[str] = None
