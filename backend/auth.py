# ============================================================
# auth.py — Handles all authentication logic
# This file is the "security guard" of our application.
# It handles:
# 1. Hashing passwords before storing them
# 2. Verifying passwords when users log in
# 3. Creating JWT tokens after successful login
# 4. Verifying JWT tokens on protected routes
# ============================================================


from datetime import datetime, timedelta, timezone
from typing import Optional
import os
import secrets

# load_dotenv reads our .env file and loads its contents into
# the environment, so os.getenv() can actually find them.
from dotenv import load_dotenv

# CryptContext is what handles password hashing.
# bcrypt is the hashing algorithm — it's the industry standard
# for storing passwords safely.
from passlib.context import CryptContext

# jwt is what creates and reads our authentication tokens.
# A JWT (JSON Web Token) is a secure way to pass user info
# between the frontend and backend without storing it in the database.
from jose import JWTError, jwt

from schemas import TokenData


# Load environment variables from .env before anything below
# tries to read them.
load_dotenv()


# ============================================================
# CONFIGURATION
# ============================================================

# SECRET_KEY is used to sign our JWT tokens.
# Think of it like a wax seal on a letter — it proves the
# token came from us and hasn't been tampered with.
# Loaded from .env so the real value is never committed to
# version control (GitHub only ever sees this line of code,
# never the actual secret string).
SECRET_KEY = os.getenv("SECRET_KEY")

# The algorithm used to sign the token.
# HS256 is the most common and secure choice for V1.
ALGORITHM = "HS256"

# How long a token stays valid after login.
# After 30 minutes the user will need to log in again.
ACCESS_TOKEN_EXPIRE_MINUTES = 30


# ============================================================
# PASSWORD HASHING
# ============================================================

# This creates our password hashing tool using bcrypt.
# "deprecated='auto'" means old hashing methods get
# automatically upgraded to the latest standard.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    # Takes a plain text password and returns a hashed version.
    # Example: "mypassword123" → "$2b$12$randomscrambledstring"
    # The hash can NEVER be reversed back to the original.
    # Note: bcrypt has a 72 character limit — we slice to prevent errors.
    return pwd_context.hash(password[:72])


def verify_password(plain_password: str, hashed_password: str) -> bool:
    # Checks if a plain text password matches a stored hash.
    # It hashes the plain password and compares — never decrypts.
    # We slice to 72 characters here too so it matches what we stored.
    # Returns True if they match, False if they don't.
    return pwd_context.verify(plain_password[:72], hashed_password)


# ============================================================
# JWT TOKEN CREATION AND VERIFICATION
# ============================================================

def create_access_token(data: dict, expires_delta=None):
    # Creates a JWT token containing the user's info.
    # The token has an expiry time so it doesn't last forever.

    # Make a copy of the data so we don't modify the original.
    to_encode = data.copy()

    # Set the expiry time — either custom or default 30 minutes.
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    # Add the expiry time to the token data.
    # "exp" is a standard JWT field that means "expiration".
    to_encode.update({"exp": expire})

    # Encode everything into a JWT string using our secret key.
    # This is the actual token string we send to the frontend.
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str):
    # Verifies a token the frontend sends us.
    # Returns the user's email if valid, None if invalid/expired.
    try:
        # Decode the token using our secret key.
        # If it was tampered with or expired, this will throw an error.
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # Extract the email from the token payload.
        # "sub" is a standard JWT field that means "subject" (the user).
        email = payload.get("sub")

        if email is None:
            return None

        return TokenData(email=email)

    except JWTError:
        # If anything goes wrong (expired, tampered, invalid)
        # we return None which will cause a 401 Unauthorized error.
        return None

# ============================================================
# OAUTH "STATE" TOKENS — protect the Gmail connect flow
# ============================================================
# When we send a user to Google's consent screen we attach a
# `state` value; Google hands it back unchanged. We make it a
# short-lived signed JWT that says "user #42 started a Gmail
# connection".
#
# The signature proves WE created it (can't be forged).
# BUT a signature alone is not enough: an attacker could start
# the flow on THEIR account and trick a victim into finishing
# it, linking the victim's inbox to the attacker's account.
# So the completion endpoint ALSO requires the victim's own
# login token and checks state.sub == current user
# (see routers/email_routes.py). Both checks together = safe.

OAUTH_STATE_PURPOSE = "gmail_oauth"


def create_oauth_state(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "aud": OAUTH_STATE_PURPOSE,          # can't be reused as a login token
        "nonce": secrets.token_urlsafe(16),  # every state is unique
        "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_oauth_state(state: str) -> Optional[int]:
    """Return the user id inside a valid state token, else None."""
    try:
        payload = jwt.decode(state, SECRET_KEY, algorithms=[ALGORITHM], audience=OAUTH_STATE_PURPOSE)
        # python-jose skips the audience check when a token has no
        # "aud" at all (like our login tokens), so check explicitly.
        if payload.get("aud") != OAUTH_STATE_PURPOSE:
            return None
        return int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        return None
