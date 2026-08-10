# ============================================================
# database.py — Sets up our database connection
# Think of this file as the "blueprint" for how our app
# connects to and interacts with the database.
# ============================================================


# SQLAlchemy is our ORM (Object Relational Mapper).
# An ORM lets us write Python code instead of raw SQL.
# Instead of writing "SELECT * FROM users", we write
# Python functions and SQLAlchemy translates it to SQL for us.
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

import os

# load_dotenv reads our .env file and loads its contents into
# the environment, so os.getenv() can actually find them.
from dotenv import load_dotenv

# Load environment variables from .env before anything below
# tries to read them.
load_dotenv()


# ============================================================
# DATABASE CONNECTION
# ============================================================

# This is our database connection string, loaded from .env.
# We used to hardcode a SQLite file path here ("sqlite:///./internship_tracker.db"),
# but SQLite just writes to a local file — that doesn't survive
# on most hosting platforms, since their filesystems get wiped
# on every restart/redeploy.
# Postgres (hosted on Neon) is a real database server, so our
# data persists independently of our backend code.
# The real connection string lives only in .env, never in this
# file, so it's never committed to version control.
DATABASE_URL = os.getenv("DATABASE_URL")

# The engine is our actual connection to the database.
# Think of it as the pipeline between Python and Postgres.
# Unlike SQLite, Postgres doesn't need check_same_thread=False —
# that flag only existed to work around SQLite's single-thread
# file-locking behavior. Postgres is a networked server built to
# handle many simultaneous connections on its own, so no special
# thread handling is needed here.
engine = create_engine(DATABASE_URL)

# SessionLocal is a factory that creates database sessions.
# A session is like a temporary workspace where we read/write
# data. We open one per request, use it, then close it.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base is the foundation that all our database models inherit from.
# A model is a Python class that represents a table in the database.
# Every model we create will say "class X(Base)" to connect to this.
Base = declarative_base()


# ============================================================
# DATABASE SESSION — Dependency for FastAPI routes
# ============================================================

# This function gives each API request its own database session.
# It uses "yield" which means:
# 1. Open a session
# 2. Give it to the route that needs it
# 3. When the route is done, close the session automatically
# This pattern prevents database connections from piling up.
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()