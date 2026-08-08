"""add reservas deleted_at for soft delete

Revision ID: a1b2c3d4e5f6
Revises: 331448de725b
Create Date: 2026-08-07 16:10:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "331448de725b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add nullable ``deleted_at`` for soft-deleted reservations."""
    op.add_column(
        "reservas",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_reservas_deleted_at",
        "reservas",
        ["deleted_at"],
    )


def downgrade() -> None:
    """Drop soft-delete column from reservas."""
    op.drop_index("ix_reservas_deleted_at", table_name="reservas")
    op.drop_column("reservas", "deleted_at")
