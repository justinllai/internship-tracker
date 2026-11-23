# ============================================================
# deps.py — Shared FastAPI dependencies
# ------------------------------------------------------------
# get_current_user used to live in main.py. Now that routes are
# split across several router files, they all need it, so it
# lives here and everyone imports it from one place.
# ============================================================

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from auth import verify_token
from database import get_db
from models import User

# Tells FastAPI to read "Authorization: Bearer <token>" headers.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    # Runs before every protected route. Invalid/expired token → 401
    # and the route body never executes.
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token_data = verify_token(token)
    if token_data is None:
        raise credentials_exception
    user = db.query(User).filter(User.email == token_data.email).first()
    if user is None:
        raise credentials_exception
    return user
