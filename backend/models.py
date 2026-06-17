# ============================================================
# models.py — Defines the shape of our database tables
# Each class here = one table in the database.
# Each variable inside the class = one column in that table.
# Think of it like designing a spreadsheet before filling it in.
# ============================================================


# We import Base from database.py — every model must inherit
# from Base so SQLAlchemy knows it represents a database table.
from database import Base

# Column defines a column in the table.
# Integer, String, Boolean are the data types for each column.
from sqlalchemy import Column, Integer, String, Boolean


# ============================================================
# USER MODEL — Represents the "users" table
# ============================================================

# By inheriting from Base, we're telling SQLAlchemy:
# "This class is a database table, not just a regular class."
class User(Base):

    # __tablename__ tells SQLAlchemy what to name the table
    # in the actual database file.
    __tablename__ = "users"

    # id: A unique number for every user.
    # primary_key=True means this is the unique identifier.
    # index=True makes searching by id much faster.
    # Think of it like a student ID number — every user gets one.
    id = Column(Integer, primary_key=True, index=True)

    # email: The user's email address.
    # unique=True means no two users can have the same email.
    # index=True makes searching by email faster.
    # nullable=False means this field is required — can't be empty.
    email = Column(String, unique=True, index=True, nullable=False)

    # username: The user's display name.
    # unique=True means no two users can have the same username.
    username = Column(String, unique=True, index=True, nullable=False)

    # hashed_password: We NEVER store the real password.
    # Instead we store a hashed (scrambled) version.
    # Even if someone stole our database, they couldn't
    # recover the original passwords. This is industry standard.
    hashed_password = Column(String, nullable=False)

    # is_active: Is this account active?
    # default=True means new accounts are active by default.
    # We could set this to False to "ban" or "deactivate" a user
    # without deleting their data.
    is_active = Column(Boolean, default=True)