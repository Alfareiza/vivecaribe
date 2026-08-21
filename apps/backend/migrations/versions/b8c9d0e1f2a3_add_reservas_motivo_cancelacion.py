"""add reservas.motivo_cancelacion for the cancel-reserva flow

Revision ID: b8c9d0e1f2a3
Revises: a2b3c4d5e6f7
Create Date: 2026-08-21 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b8c9d0e1f2a3"
down_revision: Union[str, Sequence[str], None] = "a2b3c4d5e6f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add nullable motivo_cancelacion, populated by the Cancelar flow."""
    op.add_column(
        "reservas",
        sa.Column("motivo_cancelacion", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    """Drop motivo_cancelacion."""
    op.drop_column("reservas", "motivo_cancelacion")
