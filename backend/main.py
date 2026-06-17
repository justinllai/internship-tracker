# ============================================================
# main.py — The entry point for our FastAPI backend server
# Think of this file as the "front desk" of our application.
# Every request that comes in goes through here first.
# ============================================================


from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

# SQLAlchemy's Session type — used to type hint our db parameter
from sqlalchemy.orm import Session

# Our own files
from database import engine, get_db, Base
from models import User
from schemas import UserCreate, UserLogin, UserResponse, Token
from auth import (
    hash_password,
    verify_password,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from datetime import timedelta


# ============================================================
# CREATE TABLES
# ============================================================

# This line reads all our models and creates the matching
# tables in the SQLite database if they don't exist yet.
# It's safe to run every time — it won't delete existing data.
Base.metadata.create_all(bind=engine)


# ============================================================
# CREATE THE APP
# ============================================================

# This line creates our FastAPI application.
# Think of `app` as the restaurant itself — everything else
# (routes, middleware, etc.) gets attached to it.
app = FastAPI()


# ============================================================
# CORS MIDDLEWARE — Allowing React to talk to FastAPI
# ============================================================

app.add_middleware(
    CORSMiddleware,

    # allow_origins: Which websites are allowed to talk to us?
    # We're only allowing our React app running on port 3000.
    allow_origins=["http://localhost:3000"],

    # allow_credentials: Can the request include login cookies?
    # Yes — we'll need this later when we add user authentication.
    allow_credentials=True,

    # allow_methods: Which HTTP methods are allowed?
    # "*" means all of them (GET, POST, PUT, DELETE, etc.)
    allow_methods=["*"],

    # allow_headers: Which request headers are allowed?
    # "*" means all of them.
    allow_headers=["*"],
)


# ============================================================
# ROUTES
# ============================================================

# Health check — confirms the server is running.
@app.get("/health")
def health_check():
    return {"status": "ok"}


# ============================================================
# REGISTER ENDPOINT
# ============================================================

# @app.post means this route accepts POST requests.
# POST is used when we're CREATING something new.
# response_model=UserResponse means we always return
# a UserResponse shaped object — never a password.
@app.post("/register", response_model=UserResponse)
def register(user: UserCreate, db: Session = Depends(get_db)):
    # user: UserCreate — FastAPI automatically reads the request
    # body and validates it matches our UserCreate schema.
    # db: Session — FastAPI automatically gives us a database
    # session using our get_db function.

    # Step 1: Check if email is already registered.
    # We query the users table for a matching email.
    existing_email = db.query(User).filter(User.email == user.email).first()
    if existing_email:
        # HTTPException sends an error response back to the client.
        # 400 Bad Request means the client sent invalid data.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Step 2: Check if username is already taken.
    existing_username = db.query(User).filter(User.username == user.username).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )

    # Step 3: Hash the password before storing it.
    # We NEVER store plain text passwords in the database.
    hashed = hash_password(user.password)

    # Step 4: Create a new User object with the hashed password.
    new_user = User(
        email=user.email,
        username=user.username,
        hashed_password=hashed
    )

    # Step 5: Save the new user to the database.
    # add() stages the new user (like git add)
    # commit() saves it permanently (like git commit)
    # refresh() reloads the object so we get the auto-generated id
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


# ============================================================
# LOGIN ENDPOINT
# ============================================================

@app.post("/login", response_model=Token)
def login(user: UserLogin, db: Session = Depends(get_db)):

    # Step 1: Find the user by email in the database.
    db_user = db.query(User).filter(User.email == user.email).first()

    # Step 2: If no user found OR password doesn't match, reject.
    # We give the same error for both cases on purpose —
    # telling an attacker "email not found" helps them guess emails.
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Step 3: Create a JWT token for the user.
    # "sub" (subject) stores the user's email inside the token.
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": db_user.email},
        expires_delta=access_token_expires
    )

    # Step 4: Return the token to the frontend.
    # The frontend will store this and send it with future requests.
    return {"access_token": access_token, "token_type": "bearer"}