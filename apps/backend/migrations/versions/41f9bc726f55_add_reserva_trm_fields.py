"""add reserva trm_estimado and trm_del_dia fields

Revision ID: 41f9bc726f55
Revises: f6a7b8c9d0e1
Create Date: 2026-08-20 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "41f9bc726f55"
down_revision: Union[str, Sequence[str], None] = "a8b9c0d1e2f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add trm_estimado and trm_del_dia columns to reservas."""
    op.add_column(
        "reservas",
        sa.Column("trm_estimado", sa.Numeric(precision=12, scale=2), nullable=True),
    )
    op.add_column(
        "reservas",
        sa.Column("trm_del_dia", sa.Numeric(precision=12, scale=2), nullable=True),
    )


def downgrade() -> None:
    """Drop trm_estimado and trm_del_dia columns from reservas."""
    op.drop_column("reservas", "trm_del_dia")
    op.drop_column("reservas", "trm_estimado")
