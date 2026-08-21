"""``Gasto`` — an operator-registered expense tied to a ``Partido``."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from vivecaribe.domain.enums import GastoCategoria


class Gasto(BaseModel):
    """A partido-level expense in one fixed category.

    At most one ``Gasto`` exists per ``(partido_id, categoria)`` pair — the
    operator sets one amount per category rather than a repeatable list.
    Its value is split across the partido's linked reservas proportionally
    to each reserva's ``participants``, which feeds that reserva's derived
    ``costos`` (see ``SqlAlchemyGastoRepository`` / ``recompute_splits``).
    """

    model_config = ConfigDict(from_attributes=True, validate_assignment=True)

    partido_id: UUID
    categoria: GastoCategoria
    monto: Decimal = Field(gt=0)
    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
