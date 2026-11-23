# ============================================================
# database.py — Sets up our database connection
# Think of this file as the "blueprint" for how our app
# connects to and interacts with the database.
# ============================================================


# SQLAlchemy is our ORM (Object Relational Mapper).
# An ORM lets us write Python code instead of raw SQL.
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

from config import DATABASE_URL


# ============================================================
# DATABASE CONNECTION
# ============================================================

# Production uses Postgres (Neon). Our automated tests use a
# throwaway SQLite file so they never touch real data.
# SQLite needs check_same_thread=False because FastAPI may use a
# session on a different thread than the one that created it;
# Postgres doesn't need (or accept) that flag.
connect_args = {"check_same_thread": False} if DATABASE_URL and DATABASE_URL.startswith("sqlite") else {}

# pool_pre_ping=True: before handing out a pooled connection,
# SQLAlchemy sends a tiny "SELECT 1". Neon closes idle
# connections, and Render's free server sleeps — without this,
# the first request after waking can fail with "connection closed".
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)

# SQLite ignores foreign keys (and ON DELETE CASCADE) unless you
# switch them on for every connection. Postgres always enforces
# them. Turning them on keeps our SQLite tests honest — they
# behave like production instead of hiding cascade bugs.
if engine.dialect.name == "sqlite":
    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, _record):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

# SessionLocal is a factory that creates database sessions.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base is the foundation that all our database models inherit from.
Base = declarative_base()


# ============================================================
# DATABASE SESSION — Dependency for FastAPI routes
# ============================================================

# Opens one session per request and always closes it afterwards
# (the `finally` runs even if the route raised an error).
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
