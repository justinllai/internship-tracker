"""Baseline: the schema as it existed before migrations were added.

The production database ALREADY has these tables (made by the old
Base.metadata.create_all). For that database, don't run this — mark
it as applied once with:

    alembic stamp 0001

A brand-new database (or the test suite) runs it normally.

Revision ID: 0001
Revises:
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("username", sa.String(), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=True),
    )
    op.create_index("ix_users_id", "users", ["id"])
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.create_table(
        "applications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_name", sa.String(), nullable=False),
        sa.Column("position", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("deadline", sa.DateTime(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("date_applied", sa.DateTime(), nullable=True),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
    )
    op.create_index("ix_applications_id", "applications", ["id"])


def downgrade():
    op.drop_index("ix_applications_id", table_name="applications")
    op.drop_table("applications")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_id", table_name="users")
    op.drop_table("users")
