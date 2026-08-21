"""Request/response schemas for gasto endpoints (partido-scoped expenses)."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from vivecaribe.domain.enums import GastoCategoria


class GastoUpsert(BaseModel):
    """Payload for ``PUT /partidos/{partido_id}/gastos/{categoria}``."""

    monto: Decimal = Field(gt=0)


class GastoItem(BaseModel):
    """A single category's registered amount, for the partido's Gastos grid."""

    model_config = ConfigDict(from_attributes=True)

    categoria: GastoCategoria
    monto: Decimal


class GastoShareItem(BaseModel):
    """A single reserva's computed share of one gasto category."""

    categoria: GastoCategoria
    monto: Decimal
