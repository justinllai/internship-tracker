# ============================================================
# db_check.py — READ-ONLY look at whatever DATABASE_URL points to
# ------------------------------------------------------------
# Run from backend/:   python scripts/db_check.py
#
# Prints:
#   - which database host you're connected to (never the password)
#   - the Alembic version recorded in the DB (or "none")
#   - every table, its columns, and its row count
#
# It only runs SELECT/inspection queries, so it's safe to run
# against production before and after a migration — compare the
# two outputs to see exactly what changed (and that row counts
# didn't).
# ============================================================

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, inspect, text  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402

import config  # noqa: E402


def main():
    if not config.DATABASE_URL:
        sys.exit("DATABASE_URL is not set (check backend/.env)")

    url = make_url(config.DATABASE_URL)
    # Show where we're pointed WITHOUT revealing credentials
    print(f"Database : {url.get_backend_name()} @ {url.host or url.database}")

    engine = create_engine(config.DATABASE_URL)
    insp = inspect(engine)
    tables = sorted(insp.get_table_names())

    with engine.connect() as conn:
        if "alembic_version" in tables:
            version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
            print(f"Alembic  : {version}")
        else:
            print("Alembic  : none (database has never been stamped/migrated)")

        print()
        for table in tables:
            if table == "alembic_version":
                continue
            count = conn.execute(text(f'SELECT COUNT(*) FROM "{table}"')).scalar()
            cols = [c["name"] for c in insp.get_columns(table)]
            print(f"{table}  ({count} rows)")
            print(f"    {', '.join(cols)}")


if __name__ == "__main__":
    main()
