"""Add projects table and tickets.project_id (ticket metadata)

Revision ID: 003_projects
Revises: 002_events
Create Date: 2026-09-05
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "003_projects"
down_revision: Union[str, None] = "002_events"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("color", sa.String(length=32), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "name", name="uq_project_tenant_name"),
    )
    op.create_index("ix_projects_tenant_id", "projects", ["tenant_id"])

    op.add_column("tickets", sa.Column("project_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_tickets_project_id", "tickets", "projects", ["project_id"], ["id"], ondelete="SET NULL"
    )
    op.create_index("ix_tickets_project_id", "tickets", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_tickets_project_id", table_name="tickets")
    op.drop_constraint("fk_tickets_project_id", "tickets", type_="foreignkey")
    op.drop_column("tickets", "project_id")
    op.drop_index("ix_projects_tenant_id", table_name="projects")
    op.drop_table("projects")