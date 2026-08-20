"""add reserva income_final field

Revision ID: 3f31dd9b6790
Revises: 41f9bc726f55
Create Date: 2026-08-20 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3f31dd9b6790"
down_revision: Union[str, Sequence[str], None] = "41f9bc726f55"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add income_final column to reservas."""
    op.add_column(
        "reservas",
        sa.Column("income_final", sa.Numeric(precision=12, scale=2), nullable=True),
    )


def downgrade() -> None:
    """Drop income_final column from reservas."""
    op.drop_column("reservas", "income_final")
