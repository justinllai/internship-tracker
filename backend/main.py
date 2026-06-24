# ============================================================
# main.py — The entry point for our FastAPI backend server
# Think of this file as the "front desk" of our application.
# Every request that comes in goes through here first.
# ============================================================


from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import timedelta

# Our own files
from database import engine, get_db, Base
from models import User, Application
from schemas import (
    UserCreate, UserLogin, UserResponse, Token,
    ApplicationCreate, ApplicationUpdate, ApplicationResponse
)
from auth import (
    hash_password,
    verify_password,
    create_access_token,
    verify_token,
    ACCESS_TOKEN_EXPIRE_MINUTES
)


# ============================================================
# CREATE TABLES
# ============================================================

# This reads all our models and creates matching tables in the
# SQLite database if they don't exist yet.
# Safe to run every time — won't delete existing data.
Base.metadata.create_all(bind=engine)


# ============================================================
# CREATE THE APP
# ============================================================

app = FastAPI()


# ============================================================
# CORS MIDDLEWARE
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# AUTHENTICATION DEPENDENCY
# ============================================================

# OAuth2PasswordBearer tells FastAPI where to look for the token.
# tokenUrl is the endpoint the user calls to get a token (login).
# When a request comes in, FastAPI automatically extracts the
# token from the "Authorization: Bearer <token>" header.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    # This function runs automatically on every protected route.
    # It checks the token and returns the logged in user.

    # Step 1: Create a generic "credentials invalid" error.
    # We define it here so we can reuse it in multiple places.
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Step 2: Decode the token to get the email inside it.
    token_data = verify_token(token)
    if token_data is None:
        raise credentials_exception

    # Step 3: Look up the user in the database by their email.
    user = db.query(User).filter(User.email == token_data.email).first()
    if user is None:
        raise credentials_exception

    # Step 4: Return the user object to the endpoint that needs it.
    return user


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health_check():
    return {"status": "ok"}


# ============================================================
# AUTH ENDPOINTS
# ============================================================

@app.post("/register", response_model=UserResponse)
def register(user: UserCreate, db: Session = Depends(get_db)):
    # Check if email already exists
    existing_email = db.query(User).filter(User.email == user.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Check if username already exists
    existing_username = db.query(User).filter(User.username == user.username).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )

    # Hash the password and create the user
    hashed = hash_password(user.password)
    new_user = User(
        email=user.email,
        username=user.username,
        hashed_password=hashed
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@app.post("/login", response_model=Token)
def login(user: UserLogin, db: Session = Depends(get_db)):
    # Find user and verify password
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create and return JWT token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": db_user.email},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


# ============================================================
# APPLICATION ENDPOINTS
# ============================================================

# CREATE — Add a new internship application
# current_user = Depends(get_current_user) means:
# "Run get_current_user first. If the token is invalid, stop here.
# If valid, pass the logged in user to this function."
@app.post("/applications", response_model=ApplicationResponse)
def create_application(
    application: ApplicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Create a new Application object from the incoming data.
    # owner_id is set to current_user.id — not from the request body,
    # from the token. This prevents users from creating applications
    # for other users.
    new_application = Application(
        company_name=application.company_name,
        position=application.position,
        status=application.status,
        deadline=application.deadline,
        notes=application.notes,
        owner_id=current_user.id
    )
    db.add(new_application)
    db.commit()
    db.refresh(new_application)
    return new_application


# READ ALL — Get all applications for the logged in user
@app.get("/applications", response_model=List[ApplicationResponse])
def get_applications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Query only applications that belong to the current user.
    # filter(owner_id == current_user.id) ensures users only
    # ever see their own applications — never anyone else's.
    applications = db.query(Application).filter(
        Application.owner_id == current_user.id
    ).all()
    return applications


# READ ONE — Get a single application by id
@app.get("/applications/{application_id}", response_model=ApplicationResponse)
def get_application(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Find the application by id AND owner_id.
    # Checking owner_id prevents user A from reading user B's application
    # even if they guess the id.
    application = db.query(Application).filter(
        Application.id == application_id,
        Application.owner_id == current_user.id
    ).first()

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    return application


# UPDATE — Edit an existing application
@app.put("/applications/{application_id}", response_model=ApplicationResponse)
def update_application(
    application_id: int,
    updates: ApplicationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Find the application first
    application = db.query(Application).filter(
        Application.id == application_id,
        Application.owner_id == current_user.id
    ).first()

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )

    # exclude_unset=True means only update fields the user actually sent.
    # If they only sent status, only status gets updated.
    # Everything else stays the same.
    update_data = updates.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(application, field, value)

    db.commit()
    db.refresh(application)
    return application


# DELETE — Remove an application
@app.delete("/applications/{application_id}")
def delete_application(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Find the application first
    application = db.query(Application).filter(
        Application.id == application_id,
        Application.owner_id == current_user.id
    ).first()

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )

    # Delete it from the database permanently.
    db.delete(application)
    db.commit()

    # Return a simple success message.
    return {"message": "Application deleted successfully"}