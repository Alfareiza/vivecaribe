"""rename reserva trm_del_dia to trm_final

Revision ID: c14156a0c938
Revises: 3f31dd9b6790
Create Date: 2026-08-20 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c14156a0c938"
down_revision: Union[str, Sequence[str], None] = "3f31dd9b6790"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Rename reservas.trm_del_dia to trm_final."""
    op.alter_column("reservas", "trm_del_dia", new_column_name="trm_final")


def downgrade() -> None:
    """Rename reservas.trm_final back to trm_del_dia."""
    op.alter_column("reservas", "trm_final", new_column_name="trm_del_dia")
