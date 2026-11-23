"""Live tracking: location, job sources, Gmail connection, email events, notifications.

Revision ID: 0002
Revises: 0001
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    # --- users: saved search city (city-level only) ---
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("location_label", sa.String(120), nullable=True))

    # --- applications: new optional columns ---
    with op.batch_alter_table("applications") as batch:
        batch.add_column(sa.Column("company_domain", sa.String(255), nullable=True))
        batch.add_column(sa.Column("job_url", sa.String(2048), nullable=True))
        batch.add_column(sa.Column("location", sa.String(120), nullable=True))
        batch.add_column(sa.Column("source", sa.String(30), nullable=True))
        batch.add_column(sa.Column("external_id", sa.String(128), nullable=True))
        # server_default so EXISTING rows get false instead of NULL
        batch.add_column(sa.Column("track_email", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column("applied_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("track_email_since", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("updated_at", sa.DateTime(), nullable=True))
        batch.create_index("ix_applications_owner_id", ["owner_id"])

    # Backfill existing rows: before this migration every row was
    # created at the moment the user applied.
    op.execute("UPDATE applications SET source = 'manual' WHERE source IS NULL")
    op.execute("UPDATE applications SET applied_at = date_applied WHERE applied_at IS NULL AND status <> 'Saved'")
    op.execute("UPDATE applications SET updated_at = date_applied WHERE updated_at IS NULL")

    # --- new tables ---
    op.create_table(
        "email_connections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("email_address", sa.String(320), nullable=True),
        sa.Column("encrypted_refresh_token", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(), nullable=True),
        sa.Column("last_error", sa.String(500), nullable=True),
        sa.Column("sync_lease_until", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "email_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("application_id", sa.Integer(), sa.ForeignKey("applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("connection_id", sa.Integer(), sa.ForeignKey("email_connections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider_message_id", sa.String(64), nullable=False),
        sa.Column("from_name", sa.String(200), nullable=True),
        sa.Column("from_address", sa.String(320), nullable=True),
        sa.Column("subject", sa.String(500), nullable=True),
        sa.Column("received_at", sa.DateTime(), nullable=False),
        sa.Column("classification", sa.String(20), nullable=False),
        sa.Column("is_unread", sa.Boolean(), nullable=False),
        sa.Column("ambiguous", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("user_id", "provider_message_id", name="uq_email_event_message"),
    )
    op.create_index("ix_email_events_user_id", "email_events", ["user_id"])
    op.create_index("ix_email_events_application_id", "email_events", ["application_id"])
    op.create_index("ix_email_events_connection_id", "email_events", ["connection_id"])

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("application_id", sa.Integer(), sa.ForeignKey("applications.id", ondelete="CASCADE"), nullable=True),
        sa.Column("email_event_id", sa.Integer(), sa.ForeignKey("email_events.id", ondelete="SET NULL"), nullable=True),
        sa.Column("kind", sa.String(30), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body", sa.String(500), nullable=True),
        sa.Column("suggested_status", sa.String(20), nullable=True),
        sa.Column("suggestion_resolved", sa.Boolean(), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_created_at", "notifications", ["created_at"])


def downgrade():
    op.drop_table("notifications")
    op.drop_table("email_events")
    op.drop_table("email_connections")
    with op.batch_alter_table("applications") as batch:
        batch.drop_index("ix_applications_owner_id")
        for col in ("updated_at", "track_email_since", "applied_at", "track_email", "external_id", "source",
                    "location", "job_url", "company_domain"):
            batch.drop_column(col)
    with op.batch_alter_table("users") as batch:
        batch.drop_column("location_label")
