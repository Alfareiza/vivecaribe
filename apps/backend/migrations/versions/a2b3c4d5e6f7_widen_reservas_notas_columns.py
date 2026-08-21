"""widen reservas.notas_cliente and notas_personales to 5000 chars

Revision ID: a2b3c4d5e6f7
Revises: 958c6f8b6a56
Create Date: 2026-08-21 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a2b3c4d5e6f7"
down_revision: Union[str, Sequence[str], None] = "958c6f8b6a56"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Widen notas_cliente/notas_personales from 255 to 5000 chars."""
    op.alter_column(
        "reservas",
        "notas_cliente",
        existing_type=sa.String(length=255),
        type_=sa.String(length=5000),
        existing_nullable=True,
    )
    op.alter_column(
        "reservas",
        "notas_personales",
        existing_type=sa.String(length=255),
        type_=sa.String(length=5000),
        existing_nullable=True,
    )


def downgrade() -> None:
    """Narrow notas_cliente/notas_personales back to 255 chars.

    Any existing value longer than 255 chars will fail this downgrade
    unless truncated first.
    """
    op.alter_column(
        "reservas",
        "notas_cliente",
        existing_type=sa.String(length=5000),
        type_=sa.String(length=255),
        existing_nullable=True,
    )
    op.alter_column(
        "reservas",
        "notas_personales",
        existing_type=sa.String(length=5000),
        type_=sa.String(length=255),
        existing_nullable=True,
    )
