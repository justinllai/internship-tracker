# ============================================================
# models.py — Defines the shape of our database tables
# Each class here = one table in the database.
# Each variable inside the class = one column in that table.
#
# IMPORTANT: changing this file does NOT change the real
# database by itself. Every change here needs a matching
# Alembic migration in alembic/versions/ (see README in docs).
#
# Tables:
#   users             — accounts (+ saved city for job search)
#   applications      — one row per internship application
#   email_connections — a user's linked Gmail (encrypted token)
#   email_events      — company replies we detected (NO bodies)
#   notifications     — what shows up under the bell icon
# ============================================================

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, false,
)
from sqlalchemy.orm import relationship

from database import Base


def utcnow():
    # Naive UTC timestamp (no timezone attached), matching how the
    # existing rows were stored with datetime.utcnow(). The frontend
    # treats these as UTC.
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ============================================================
# USER
# ============================================================

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)

    # NEW: the user's default search area, e.g. "San Jose, CA".
    # Deliberately city-level only — data minimization. We never
    # store a street address or GPS coordinates.
    location_label = Column(String(120), nullable=True)

    # cascade="all, delete-orphan": deleting a user (or removing an
    # application from user.applications) deletes the child rows too.
    applications = relationship("Application", back_populates="owner", cascade="all, delete-orphan")
    email_connection = relationship("EmailConnection", back_populates="user", uselist=False, cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")


# ============================================================
# APPLICATION — one internship application
# ============================================================

class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String, nullable=False)
    position = Column(String, nullable=False)

    # Saved → Applied → Interview → Offer, or Rejected.
    # The allowed values are enforced in schemas.py (Pydantic).
    status = Column(String, default="Applied")

    deadline = Column(DateTime, nullable=True)
    notes = Column(String, nullable=True)

    # When the row was created (kept for backwards compatibility).
    date_applied = Column(DateTime, default=utcnow)

    owner_id = Column(Integer, ForeignKey("users.id"), index=True)

    # ---- NEW COLUMNS ----

    # e.g. "stripe.com" — lets us recognise replies from this company
    company_domain = Column(String(255), nullable=True)

    job_url = Column(String(2048), nullable=True)
    location = Column(String(120), nullable=True)

    # Where it came from: "manual" or a job source like "adzuna",
    # plus that source's own job id. (source, external_id) is how
    # we tell "you already saved this posting" — URLs aren't
    # stable because job boards add tracking parameters.
    source = Column(String(30), nullable=True, default="manual")
    external_id = Column(String(128), nullable=True)

    # Consent flag: only applications with track_email=True are
    # ever searched for in the user's inbox.
    track_email = Column(Boolean, nullable=False, default=False, server_default=false())

    # When the user actually applied. Differs from date_applied for
    # jobs that sat in "Saved" first. Email search starts here.
    applied_at = Column(DateTime, nullable=True)

    # When tracking was switched on. Lets the sync do a full
    # look-back only for NEWLY tracked applications and a cheap
    # "since last sync" search for everything else.
    track_email_since = Column(DateTime, nullable=True)

    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    owner = relationship("User", back_populates="applications")

    # Newest email first. Deleting an application deletes its
    # detected emails and notifications (no orphans, no FK errors).
    email_events = relationship(
        "EmailEvent", back_populates="application",
        order_by="EmailEvent.received_at.desc()",
        cascade="all, delete-orphan", passive_deletes=True,
    )
    notifications = relationship(
        "Notification", back_populates="application",
        cascade="all, delete-orphan", passive_deletes=True,
    )


# ============================================================
# EMAIL CONNECTION — a user's linked Gmail account
# ============================================================

class EmailConnection(Base):
    __tablename__ = "email_connections"

    id = Column(Integer, primary_key=True)
    # unique=True: at most one connected inbox per user
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    provider = Column(String(20), nullable=False, default="gmail")
    email_address = Column(String(320), nullable=True)

    # Encrypted with Fernet (crypto.py). Never stored in plaintext,
    # never returned by any API endpoint.
    encrypted_refresh_token = Column(Text, nullable=False)

    # "active" or "needs_reauth". Google expires refresh tokens for
    # apps in "Testing" mode after 7 days; when that happens we flip
    # this and ask the user to reconnect instead of failing silently.
    status = Column(String(20), nullable=False, default="active")

    created_at = Column(DateTime, default=utcnow)
    last_synced_at = Column(DateTime, nullable=True)
    last_error = Column(String(500), nullable=True)

    # A "lease" so two syncs for the same user can't run at once
    # (cron + "Check now" at the same moment). See email_sync.py.
    sync_lease_until = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="email_connection")


# ============================================================
# EMAIL EVENT — one company reply we detected
# Note what is NOT here: the email body. We keep only what the
# UI needs (sender, subject, date, our classification).
# ============================================================

class EmailEvent(Base):
    __tablename__ = "email_events"
    # The same Gmail message can never be recorded twice for a user,
    # even if two syncs race. The database enforces it.
    __table_args__ = (UniqueConstraint("user_id", "provider_message_id", name="uq_email_event_message"),)

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    application_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), index=True, nullable=False)
    # Ties every event to the Gmail connection it came from. Deleting
    # the connection (Disconnect) makes the DATABASE delete these rows,
    # and a sync still running at that moment can't insert new ones —
    # the foreign key no longer exists. The privacy promise is enforced
    # by the database, not just by our code being careful.
    connection_id = Column(Integer, ForeignKey("email_connections.id", ondelete="CASCADE"), index=True, nullable=False)
    provider_message_id = Column(String(64), nullable=False)
    from_name = Column(String(200), nullable=True)
    from_address = Column(String(320), nullable=True)
    subject = Column(String(500), nullable=True)
    received_at = Column(DateTime, nullable=False)
    # offer | interview | rejection | acknowledgment | other
    classification = Column(String(20), nullable=False, default="other")
    # Was it still UNREAD in Gmail when we saw it? Lets us say
    # "you haven't opened this yet".
    is_unread = Column(Boolean, nullable=False, default=False)
    # True if several of the user's applications could match
    # (e.g. two roles at the same company) — UI shows a hint.
    ambiguous = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=utcnow)

    application = relationship("Application", back_populates="email_events")


# ============================================================
# NOTIFICATION — what shows under the bell
# ============================================================

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    application_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=True)
    email_event_id = Column(Integer, ForeignKey("email_events.id", ondelete="SET NULL"), nullable=True)

    # "email_reply" or "reauth_needed"
    kind = Column(String(30), nullable=False)
    title = Column(String(200), nullable=False)
    body = Column(String(500), nullable=True)

    # Our classifier SUGGESTS a status ("Interview"); the user
    # decides. suggestion_resolved flips once they apply/dismiss it.
    suggested_status = Column(String(20), nullable=True)
    suggestion_resolved = Column(Boolean, nullable=False, default=False)

    is_read = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=utcnow, index=True)

    user = relationship("User", back_populates="notifications")
    application = relationship("Application", back_populates="notifications")
    email_event = relationship("EmailEvent")
