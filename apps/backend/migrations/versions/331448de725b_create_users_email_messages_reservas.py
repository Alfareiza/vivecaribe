"""create users email_messages reservas

Revision ID: 331448de725b
Revises:
Create Date: 2026-07-31 16:08:59.955917

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "331448de725b"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create users, email_messages, and reservas tables."""
    op.create_table(
        "email_messages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("mailbox_message_id", sa.String(length=512), nullable=False),
        sa.Column("sender", sa.String(length=320), nullable=False),
        sa.Column("recipients", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("subject", sa.String(length=998), nullable=False),
        sa.Column("body_text", sa.Text(), nullable=False),
        sa.Column("body_html", sa.Text(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source",
            "mailbox_message_id",
            name="uq_email_messages_source_mailbox_message_id",
        ),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_table(
        "reservas",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("email_message_id", sa.UUID(), nullable=True),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("booking_provider", sa.String(length=32), nullable=False),
        sa.Column("reserva_reference", sa.String(length=512), nullable=False),
        sa.Column("sender", sa.String(length=320), nullable=False),
        sa.Column("estado", sa.String(length=32), nullable=False),
        sa.Column("subject", sa.String(length=998), nullable=False),
        sa.Column("fecha_email_recibido", sa.DateTime(timezone=True), nullable=False),
        sa.Column("nombre_experiencia", sa.String(length=512), nullable=False),
        sa.Column("ciudad_experiencia", sa.String(length=255), nullable=False),
        sa.Column("fecha_evento", sa.DateTime(timezone=True), nullable=True),
        sa.Column("participants", sa.Integer(), nullable=False),
        sa.Column("customer_name", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=64), nullable=False),
        sa.Column("pais_del_visitante", sa.String(length=128), nullable=False),
        sa.Column("moneda", sa.String(length=8), nullable=False),
        sa.Column("price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("income", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("notificado_whatsapp", sa.Boolean(), nullable=False),
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
            ["email_message_id"],
            ["email_messages.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "booking_provider",
            "reserva_reference",
            name="uq_reservas_booking_provider_reserva_reference",
        ),
    )
    op.create_index("ix_reservas_estado", "reservas", ["estado"], unique=False)
    op.create_index(
        "ix_reservas_fecha_email_recibido",
        "reservas",
        ["fecha_email_recibido"],
        unique=False,
    )
    op.create_index(
        "ix_reservas_notificado_whatsapp",
        "reservas",
        ["notificado_whatsapp"],
        unique=False,
    )
    op.create_index(op.f("ix_reservas_user_id"), "reservas", ["user_id"], unique=False)


def downgrade() -> None:
    """Drop reservas, users, and email_messages."""
    op.drop_index(op.f("ix_reservas_user_id"), table_name="reservas")
    op.drop_index("ix_reservas_notificado_whatsapp", table_name="reservas")
    op.drop_index("ix_reservas_fecha_email_recibido", table_name="reservas")
    op.drop_index("ix_reservas_estado", table_name="reservas")
    op.drop_table("reservas")
    op.drop_table("users")
    op.drop_table("email_messages")
