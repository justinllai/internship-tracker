# Guards against "model drift": someone edits models.py but forgets
# to write a migration. Alembic compares the migrated database to
# the models; any difference fails this test.
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from database import Base, engine


def test_migrations_match_models():
    with engine.connect() as conn:
        ctx = MigrationContext.configure(conn, opts={"compare_type": False})
        diff = compare_metadata(ctx, Base.metadata)
    assert diff == [], f"models.py and migrations disagree: {diff}"
