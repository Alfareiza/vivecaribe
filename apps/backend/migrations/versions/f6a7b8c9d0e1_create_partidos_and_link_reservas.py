"""create partidos and link reservas

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-08-14 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create partidos table and link reservas to it via a nullable FK."""
    op.create_table(
        "partidos",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("equipo_local", sa.String(length=25), nullable=False),
        sa.Column("equipo_visitante", sa.String(length=25), nullable=False),
        sa.Column("nombre_campeonato", sa.String(length=50), nullable=False),
        sa.Column("estadio", sa.String(length=25), nullable=False),
        sa.Column("fecha", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ciudad", sa.String(length=50), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_partidos_fecha", "partidos", ["fecha"], unique=False)
    op.create_index("ix_partidos_ciudad", "partidos", ["ciudad"], unique=False)
    op.create_index(
        "ix_partidos_deleted_at",
        "partidos",
        ["deleted_at"],
        unique=False,
    )

    op.add_column(
        "reservas",
        sa.Column("partido_id", sa.UUID(), nullable=True),
    )
    op.create_index(
        op.f("ix_reservas_partido_id"),
        "reservas",
        ["partido_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_reservas_partido_id_partidos",
        "reservas",
        "partidos",
        ["partido_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Drop the reservas -> partidos FK and the partidos table."""
    op.drop_constraint(
        "fk_reservas_partido_id_partidos",
        "reservas",
        type_="foreignkey",
    )
    op.drop_index(op.f("ix_reservas_partido_id"), table_name="reservas")
    op.drop_column("reservas", "partido_id")

    op.drop_index("ix_partidos_deleted_at", table_name="partidos")
    op.drop_index("ix_partidos_ciudad", table_name="partidos")
    op.drop_index("ix_partidos_fecha", table_name="partidos")
    op.drop_table("partidos")
