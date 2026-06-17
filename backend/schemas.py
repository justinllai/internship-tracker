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