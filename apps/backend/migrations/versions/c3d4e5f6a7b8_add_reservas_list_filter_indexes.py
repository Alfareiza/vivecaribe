"""add reservas list filter indexes

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-08-11 11:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Index common ``GET /reservas`` filter columns."""
    op.create_index(
        "ix_reservas_booking_provider",
        "reservas",
        ["booking_provider"],
    )
    op.create_index(
        "ix_reservas_fecha_evento",
        "reservas",
        ["fecha_evento"],
    )


def downgrade() -> None:
    """Drop list-filter indexes."""
    op.drop_index("ix_reservas_fecha_evento", table_name="reservas")
    op.drop_index("ix_reservas_booking_provider", table_name="reservas")
