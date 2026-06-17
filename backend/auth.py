# ============================================================
# auth.py — Handles all authentication logic
# This file is the "security guard" of our application.
# It handles:
# 1. Hashing passwords before storing them
# 2. Verifying passwords when users log in
# 3. Creating JWT tokens after successful login
# 4. Verifying JWT tokens on protected routes
# ============================================================


from datetime import datetime, timedelta
from typing import Optional

# CryptContext is what handles password hashing.
# bcrypt is the hashing algorithm — it's the industry standard
# for storing passwords safely.
from passlib.context import CryptContext

# jwt is what creates and reads our authentication tokens.
# A JWT (JSON Web Token) is a secure way to pass user info
# between the frontend and backend without storing it in the database.
from jose import JWTError, jwt

from schemas import TokenData


# ============================================================
# CONFIGURATION
# ============================================================

# SECRET_KEY is used to sign our JWT tokens.
# Think of it like a wax seal on a letter — it proves the
# token came from us and hasn't been tampered with.
# In production this should be a long random string stored
# in a .env file. We'll improve this later.
SECRET_KEY = "changethislatertoasecretrandomstring"

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
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

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