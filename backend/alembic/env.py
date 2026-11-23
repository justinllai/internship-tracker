# ============================================================
# alembic/env.py — How Alembic connects to our database
# ------------------------------------------------------------
# Alembic = version control for the database schema.
# Each file in alembic/versions/ is one change ("migration") with
# an upgrade() and a downgrade(). The database remembers which
# migration it's on in a tiny `alembic_version` table, so
# `alembic upgrade head` only runs the ones it hasn't seen yet.
# ============================================================

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

import config as app_config
import models  # noqa: F401 — importing registers every table on Base.metadata
from database import Base

alembic_config = context.config
if alembic_config.config_file_name is not None:
    fileConfig(alembic_config.config_file_name)

# Tests may pass a URL explicitly; otherwise use DATABASE_URL.
url = alembic_config.get_main_option("sqlalchemy.url") or app_config.DATABASE_URL
alembic_config.set_main_option("sqlalchemy.url", url)

target_metadata = Base.metadata


def run_migrations_offline():
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True,
                      render_as_batch=url.startswith("sqlite"))
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(alembic_config.get_section(alembic_config.config_ini_section),
                                     prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        # render_as_batch: SQLite can't ALTER most things in place, so
        # Alembic copies the table instead. Harmless on Postgres.
        context.configure(connection=connection, target_metadata=target_metadata,
                          render_as_batch=connection.dialect.name == "sqlite")
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
