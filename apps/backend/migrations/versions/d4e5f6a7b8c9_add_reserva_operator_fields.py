"""add reserva operator and payout fields

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-08-11 16:45:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add operator notes, finance, meeting, and paid_at columns."""
    op.add_column(
        "reservas",
        sa.Column("notas_cliente", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "reservas",
        sa.Column("tipo_tour", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "reservas",
        sa.Column("notas_personales", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "reservas",
        sa.Column("costos", sa.Numeric(precision=12, scale=2), nullable=True),
    )
    op.add_column(
        "reservas",
        sa.Column("meeting_point", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "reservas",
        sa.Column("lugar_de_recogida", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "reservas",
        sa.Column(
            "income_estimado",
            sa.Numeric(precision=12, scale=2),
            nullable=True,
        ),
    )
    op.add_column(
        "reservas",
        sa.Column("profit", sa.Numeric(precision=12, scale=2), nullable=True),
    )
    op.add_column(
        "reservas",
        sa.Column(
            "percentage",
            sa.Numeric(precision=12, scale=2),
            nullable=True,
        ),
    )
    op.add_column(
        "reservas",
        sa.Column(
            "menores_de_edad",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "reservas",
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    """Drop operator and payout columns from reservas."""
    op.drop_column("reservas", "paid_at")
    op.drop_column("reservas", "menores_de_edad")
    op.drop_column("reservas", "percentage")
    op.drop_column("reservas", "profit")
    op.drop_column("reservas", "income_estimado")
    op.drop_column("reservas", "lugar_de_recogida")
    op.drop_column("reservas", "meeting_point")
    op.drop_column("reservas", "costos")
    op.drop_column("reservas", "notas_personales")
    op.drop_column("reservas", "tipo_tour")
    op.drop_column("reservas", "notas_cliente")
