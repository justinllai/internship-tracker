# ============================================================
# database.py — Sets up our SQLite database connection
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


# ============================================================
# DATABASE CONNECTION
# ============================================================

# This is the path to our SQLite database file.
# SQLite stores everything in a single .db file — no separate
# database server needed. Perfect for V1.
# The "///" means the file is stored locally on our computer.
DATABASE_URL = "sqlite:///./internship_tracker.db"

# The engine is our actual connection to the database.
# Think of it as the pipeline between Python and the .db file.
# check_same_thread=False is needed for FastAPI because it
# handles multiple requests at the same time.
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

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