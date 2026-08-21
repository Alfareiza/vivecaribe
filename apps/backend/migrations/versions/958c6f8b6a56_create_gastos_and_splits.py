"""create gastos and gasto_reserva_splits, reset reservas.costos

Revision ID: 958c6f8b6a56
Revises: c14156a0c938
Create Date: 2026-08-20 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "958c6f8b6a56"
down_revision: Union[str, Sequence[str], None] = "c14156a0c938"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create gastos + gasto_reserva_splits tables; reset reservas.costos.

    ``costos`` stops being an operator-entered value and becomes derived
    from gasto splits (see ``vivecaribe.infrastructure.db.repositories``),
    so every existing value is reset to NULL — it will repopulate as soon
    as a gasto is registered for that reserva's partido.
    """
    op.create_table(
        "gastos",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("partido_id", sa.UUID(), nullable=False),
        sa.Column("categoria", sa.String(length=32), nullable=False),
        sa.Column("monto", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["partido_id"],
            ["partidos.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "partido_id",
            "categoria",
            name="uq_gastos_partido_id_categoria",
        ),
    )
    op.create_index(
        op.f("ix_gastos_partido_id"),
        "gastos",
        ["partido_id"],
        unique=False,
    )

    op.create_table(
        "gasto_reserva_splits",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("gasto_id", sa.UUID(), nullable=False),
        sa.Column("reserva_id", sa.UUID(), nullable=False),
        sa.Column("monto", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.ForeignKeyConstraint(
            ["gasto_id"],
            ["gastos.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["reserva_id"],
            ["reservas.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "gasto_id",
            "reserva_id",
            name="uq_gasto_reserva_splits_gasto_id_reserva_id",
        ),
    )
    op.create_index(
        op.f("ix_gasto_reserva_splits_gasto_id"),
        "gasto_reserva_splits",
        ["gasto_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_gasto_reserva_splits_reserva_id"),
        "gasto_reserva_splits",
        ["reserva_id"],
        unique=False,
    )

    op.execute("UPDATE reservas SET costos = NULL")


def downgrade() -> None:
    """Drop gasto_reserva_splits and gastos tables.

    The ``costos`` reset performed in ``upgrade`` is not reversible.
    """
    op.drop_index(
        op.f("ix_gasto_reserva_splits_reserva_id"),
        table_name="gasto_reserva_splits",
    )
    op.drop_index(
        op.f("ix_gasto_reserva_splits_gasto_id"),
        table_name="gasto_reserva_splits",
    )
    op.drop_table("gasto_reserva_splits")

    op.drop_index(op.f("ix_gastos_partido_id"), table_name="gastos")
    op.drop_table("gastos")
