# ============================================================
# schemas.py — Defines the shape of data coming IN and OUT
# of our API endpoints.
#
# Think of the difference this way:
# - models.py = how data is stored in the DATABASE
# - schemas.py = how data looks when sent to/from the API
#
# Example: The database stores hashed_password, but when a
# user registers we ask for "password" — schemas handle that
# translation layer.
# ============================================================


# Pydantic is a library that validates data automatically.
# If someone sends us an email without an "@" sign, Pydantic
# will reject it before it ever reaches our database.
from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional


# ============================================================
# USER SCHEMAS
# ============================================================

# UserCreate: The data we expect when someone REGISTERS.
# This is what the user sends TO us.
class UserCreate(BaseModel):
    email: EmailStr        # Must be a valid email format
    username: str          # Any string
    password: str          # Plain text — we'll hash it before storing


# UserLogin: The data we expect when someone LOGS IN.
class UserLogin(BaseModel):
    email: EmailStr        # Their email
    password: str          # Plain text — we'll check it against the hash


# UserResponse: The data we send BACK to the user.
# Notice: no password field here — we never send passwords back!
class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    is_active: bool

    # This tells Pydantic to work with SQLAlchemy objects directly.
    # Without this, Pydantic wouldn't know how to read our database models.
    class Config:
        from_attributes = True


# ============================================================
# TOKEN SCHEMAS — For authentication after login
# ============================================================

# Token: What we send back after a successful login.
# The access_token is like a wristband at an event —
# the user shows it on every future request to prove who they are.
class Token(BaseModel):
    access_token: str
    token_type: str        # Will always be "bearer"


# TokenData: The information stored INSIDE the token.
# We store the email so we can look up the user on each request.
class TokenData(BaseModel):
    email: Optional[str] = None


# ============================================================
# APPLICATION SCHEMAS
# ============================================================

# ApplicationCreate: Data we expect when a user adds a new application.
# owner_id and date_applied are NOT here — the system sets those
# automatically. The user only fills in what they know.
class ApplicationCreate(BaseModel):
    company_name: str                          # Required — must provide
    position: str                              # Required — must provide
    status: Optional[str] = "Applied"          # Optional — defaults to Applied
    deadline: Optional[datetime] = None        # Optional — no deadline by default
    notes: Optional[str] = None               # Optional — no notes by default


# ApplicationUpdate: Data we expect when a user edits an application.
# Every field is Optional because they might only want to change one thing.
# Example: just changing status from "Applied" to "Interview"
# without having to resend company_name and position.
class ApplicationUpdate(BaseModel):
    company_name: Optional[str] = None
    position: Optional[str] = None
    status: Optional[str] = None
    deadline: Optional[datetime] = None
    notes: Optional[str] = None


# ApplicationResponse: What we send back to the user.
# Includes system-generated fields like id, date_applied, owner_id
# so the frontend knows everything about the application.
class ApplicationResponse(BaseModel):
    id: int
    company_name: str
    position: str
    status: str
    deadline: Optional[datetime] = None
    notes: Optional[str] = None
    date_applied: datetime
    owner_id: int

    # Tells Pydantic to work with SQLAlchemy objects directly.
    class Config:
        from_attributes = True