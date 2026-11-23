# ============================================================
# auth_routes.py — Register, login, and "who am I?"
# (register/login are unchanged from the old main.py)
# ============================================================

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

import config
from auth import ACCESS_TOKEN_EXPIRE_MINUTES, create_access_token, hash_password, verify_password
from database import get_db
from deps import get_current_user
from models import User
from schemas import GmailStatus, LocationUpdate, MeResponse, Token, UserCreate, UserLogin, UserResponse

router = APIRouter(tags=["auth"])


@router.post("/register", response_model=UserResponse)
def register(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken")
    new_user = User(email=user.email, username=user.username, hashed_password=hash_password(user.password))
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.post("/login", response_model=Token)
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    # Same message for "no such email" and "wrong password" so an
    # attacker can't use this endpoint to discover who has an account.
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(data={"sub": db_user.email},
                                expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    return {"access_token": token, "token_type": "bearer"}


def gmail_status(user: User) -> GmailStatus:
    conn = user.email_connection
    return GmailStatus(
        configured=config.gmail_enabled(),
        connected=conn is not None,
        status=conn.status if conn else None,
        email_address=conn.email_address if conn else None,
        last_synced_at=conn.last_synced_at if conn else None,
        last_error=conn.last_error if conn else None,
    )


@router.get("/me", response_model=MeResponse)
def me(current_user: User = Depends(get_current_user)):
    base = UserResponse.model_validate(current_user).model_dump()
    return MeResponse(**base, gmail=gmail_status(current_user), jobs_configured=config.jobs_enabled())


@router.put("/me/location", response_model=UserResponse)
def save_location(body: LocationUpdate, db: Session = Depends(get_db),
                  current_user: User = Depends(get_current_user)):
    # Only a city-level label ever reaches this column.
    current_user.location_label = (body.location_label or "").strip() or None
    db.commit()
    db.refresh(current_user)
    return current_user
