"""make reservas email metadata nullable

Revision ID: a8b9c0d1e2f3
Revises: f6a7b8c9d0e1
Create Date: 2026-08-17 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a8b9c0d1e2f3"
down_revision: Union[str, Sequence[str], None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Allow null fecha_email_recibido/sender/subject for manually-created reservas."""
    op.alter_column(
        "reservas",
        "fecha_email_recibido",
        existing_type=sa.DateTime(timezone=True),
        nullable=True,
    )
    op.alter_column(
        "reservas",
        "sender",
        existing_type=sa.String(length=320),
        nullable=True,
    )
    op.alter_column(
        "reservas",
        "subject",
        existing_type=sa.String(length=998),
        nullable=True,
        existing_server_default=None,
    )


def downgrade() -> None:
    """Restore NOT NULL on fecha_email_recibido/sender/subject."""
    op.alter_column(
        "reservas",
        "subject",
        existing_type=sa.String(length=998),
        nullable=False,
        server_default="",
    )
    op.alter_column(
        "reservas",
        "sender",
        existing_type=sa.String(length=320),
        nullable=False,
    )
    op.alter_column(
        "reservas",
        "fecha_email_recibido",
        existing_type=sa.DateTime(timezone=True),
        nullable=False,
    )
