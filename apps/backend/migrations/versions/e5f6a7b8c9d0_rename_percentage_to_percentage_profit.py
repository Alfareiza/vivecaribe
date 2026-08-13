"""rename percentage to percentage_profit

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-08-13 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Rename reservas.percentage to reservas.percentage_profit."""
    op.alter_column("reservas", "percentage", new_column_name="percentage_profit")


def downgrade() -> None:
    """Restore the original reservas.percentage column name."""
    op.alter_column("reservas", "percentage_profit", new_column_name="percentage")
