"""Add google_tokens, email_sync_state, synced_emails tables (Gmail sync)

Revision ID: 004_gmail_sync
Revises: 003_projects
Create Date: 2026-09-07
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "004_gmail_sync"
down_revision: Union[str, None] = "003_projects"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # google_tokens
    op.create_table(
        "google_tokens",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("access_token", sa.Text(), nullable=False),
        sa.Column("refresh_token", sa.Text(), nullable=True),
        sa.Column("token_expiry", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scopes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_google_tokens_user_id", "google_tokens", ["user_id"])

    # email_sync_state
    op.create_table(
        "email_sync_state",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("last_history_id", sa.String(length=64), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.create_index("ix_email_sync_state_user_id", "email_sync_state", ["user_id"])
    op.create_index("ix_email_sync_state_tenant_id", "email_sync_state", ["tenant_id"])

    # synced_emails
    op.create_table(
        "synced_emails",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("gmail_message_id", sa.String(length=200), nullable=False),
        sa.Column("ticket_id", sa.Uuid(), sa.ForeignKey("tickets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("subject", sa.String(length=500), nullable=True),
        sa.Column("sender", sa.String(length=320), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("user_id", "gmail_message_id", name="uq_synced_email_user_msg"),
    )
    op.create_index("ix_synced_emails_user_id", "synced_emails", ["user_id"])
    op.create_index("ix_synced_emails_tenant_id", "synced_emails", ["tenant_id"])
    op.create_index("ix_synced_emails_gmail_message_id", "synced_emails", ["gmail_message_id"])


def downgrade() -> None:
    op.drop_index("ix_synced_emails_gmail_message_id", table_name="synced_emails")
    op.drop_index("ix_synced_emails_tenant_id", table_name="synced_emails")
    op.drop_index("ix_synced_emails_user_id", table_name="synced_emails")
    op.drop_table("synced_emails")

    op.drop_index("ix_email_sync_state_tenant_id", table_name="email_sync_state")
    op.drop_index("ix_email_sync_state_user_id", table_name="email_sync_state")
    op.drop_table("email_sync_state")

    op.drop_index("ix_google_tokens_user_id", table_name="google_tokens")
    op.drop_table("google_tokens")