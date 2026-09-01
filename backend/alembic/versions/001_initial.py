"""Initial service desk schema

Revision ID: 001_initial
Revises:
Create Date: 2026-09-01
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Tables are created via autogenerate baseline; for fresh installs use:
    # alembic revision --autogenerate -m "initial"
    # This migration is a marker; create_all equivalent handled by autogenerate on first run.
    pass


def downgrade() -> None:
    pass
