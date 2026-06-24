# ============================================================
# models.py — Defines the shape of our database tables
# Each class here = one table in the database.
# Each variable inside the class = one column in that table.
# Think of it like designing a spreadsheet before filling it in.
# ============================================================


from database import Base
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime


# ============================================================
# USER MODEL — Represents the "users" table
# ============================================================

class User(Base):
    __tablename__ = "users"

    # id: A unique number for every user.
    # primary_key=True means this is the unique identifier.
    id = Column(Integer, primary_key=True, index=True)

    # email: The user's email address.
    # unique=True means no two users can have the same email.
    email = Column(String, unique=True, index=True, nullable=False)

    # username: The user's display name.
    username = Column(String, unique=True, index=True, nullable=False)

    # hashed_password: We NEVER store the real password.
    hashed_password = Column(String, nullable=False)

    # is_active: Is this account active?
    is_active = Column(Boolean, default=True)

    # relationship: One User can have many Applications.
    # This is not a column — it's a virtual link SQLAlchemy uses
    # so we can write user.applications to get all their applications.
    applications = relationship("Application", back_populates="owner")


# ============================================================
# APPLICATION MODEL — Represents the "applications" table
# This is the core of our app — each row is one internship
# application a user has submitted.
# ============================================================

class Application(Base):
    __tablename__ = "applications"

    # id: Unique identifier for each application.
    id = Column(Integer, primary_key=True, index=True)

    # company_name: The company the user applied to.
    company_name = Column(String, nullable=False)

    # position: The job title they applied for.
    position = Column(String, nullable=False)

    # status: Where are they in the process?
    # Values we'll use: "Applied", "Interview", "Offer", "Rejected"
    status = Column(String, default="Applied")

    # deadline: Application or interview deadline.
    # nullable=True means this field is optional.
    deadline = Column(DateTime, nullable=True)

    # notes: Any extra notes the user wants to add.
    # nullable=True means this field is optional.
    notes = Column(String, nullable=True)

    # date_applied: Automatically set to when the record was created.
    # default=datetime.utcnow means we never have to set this manually.
    date_applied = Column(DateTime, default=datetime.utcnow)

    # owner_id: Which user does this application belong to?
    # ForeignKey links this to the id column in the users table.
    # This is how we know "this application belongs to user #3."
    owner_id = Column(Integer, ForeignKey("users.id"))

    # relationship: The other side of the User relationship.
    # This lets us do application.owner to get the User object.
    owner = relationship("User", back_populates="applications")