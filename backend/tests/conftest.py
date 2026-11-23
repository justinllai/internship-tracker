# ============================================================
# conftest.py — Shared test setup (pytest loads this automatically)
# ------------------------------------------------------------
# Key ideas:
#   - Environment variables are set BEFORE the app is imported,
#     so config.py reads test values, never your real .env secrets
#     (load_dotenv doesn't override variables that already exist).
#   - Each test session gets a throwaway SQLite file, built by
#     running our real Alembic migrations — so the tests also
#     prove the migrations work.
#   - Every test starts with empty tables (no test can affect another).
#   - Nothing touches the real internet: tests replace the one
#     network function in each service with a fake (monkeypatch).
# ============================================================

import os
import sys
import tempfile
from pathlib import Path

from cryptography.fernet import Fernet

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

_tmpdir = tempfile.mkdtemp()
TEST_DB_URL = f"sqlite:///{Path(_tmpdir, 'test.db').as_posix()}"

os.environ.update({
    "DATABASE_URL": TEST_DB_URL,
    "SECRET_KEY": "test-secret-key-not-for-production",
    "TOKEN_ENCRYPTION_KEYS": Fernet.generate_key().decode(),
    "GOOGLE_CLIENT_ID": "test-client-id",
    "GOOGLE_CLIENT_SECRET": "test-client-secret",
    "ADZUNA_APP_ID": "test-app-id",
    "ADZUNA_APP_KEY": "test-app-key",
    "CRON_SECRET": "test-cron-secret",
    "FRONTEND_URL": "http://localhost:3000",
})

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


def _alembic_config(url: str) -> Config:
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


@pytest.fixture(scope="session", autouse=True)
def _migrated_db():
    command.upgrade(_alembic_config(TEST_DB_URL), "head")
    yield


@pytest.fixture(autouse=True)
def _clean_tables():
    from database import Base, engine
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
    # Reset in-memory caches/limits so tests don't leak into each other
    from routers import email_routes
    from services import geo, job_search
    email_routes._last_manual_sync.clear()
    job_search._cache.clear()
    geo._cache.clear()
    yield


@pytest.fixture
def client():
    from main import app
    return TestClient(app)


@pytest.fixture
def db():
    from database import SessionLocal
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def make_user(client):
    """Register + log in a user; returns (user_id, auth headers)."""
    def _make(email="ada@example.com", username=None, password="password123"):
        username = username or email.split("@")[0]
        r = client.post("/register", json={"email": email, "username": username, "password": password})
        assert r.status_code == 200, r.text
        token = client.post("/login", json={"email": email, "password": password}).json()["access_token"]
        return r.json()["id"], {"Authorization": f"Bearer {token}"}
    return _make
