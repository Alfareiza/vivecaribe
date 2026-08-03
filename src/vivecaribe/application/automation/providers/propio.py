"""Propio (first-party) — skeleton until an HTML sample exists."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import NoReturn, Self

from bs4 import BeautifulSoup

from vivecaribe.application.automation.models import ReservaDraft
from vivecaribe.application.automation.providers.base import BaseExtractor
from vivecaribe.domain.enums import BookingProvider, ReservaEstado
from vivecaribe.domain.errors import ValidationError


class PropioExtractor(BaseExtractor):
    """Skeleton for first-party / Propio booking emails."""

    booking_provider = BookingProvider.PROPIO

    def __init__(self, soup: BeautifulSoup) -> None:
        """Store parsed HTML."""
        self._soup = soup

    @classmethod
    def from_html(cls, html: str) -> Self:
        """Build an extractor from raw HTML."""
        return cls(BeautifulSoup(html, "html.parser"))

    def _pending(self, field: str) -> NoReturn:
        """Raise until a Propio HTML sample exists."""
        raise ValidationError(
            "Propio extractor is a skeleton — HTML sample pending",
            field=field,
        )

    def get_reserva_reference(self) -> str:
        """Not implemented until a Propio HTML sample is available."""
        self._pending("reserva_reference")

    def get_nombre_experiencia(self) -> str:
        """Not implemented until a Propio HTML sample is available."""
        self._pending("nombre_experiencia")

    def get_ciudad_evento(self) -> str:
        """Not implemented until a Propio HTML sample is available."""
        self._pending("ciudad_experiencia")

    def get_dt_evento(self) -> datetime:
        """Not implemented until a Propio HTML sample is available."""
        self._pending("fecha_evento")

    def get_participants(self) -> int:
        """Not implemented until a Propio HTML sample is available."""
        self._pending("participants")

    def get_customer_name(self) -> str:
        """Not implemented until a Propio HTML sample is available."""
        self._pending("customer_name")

    def get_phone(self) -> str:
        """Not implemented until a Propio HTML sample is available."""
        self._pending("phone")

    def get_pais_del_visitante(self) -> str:
        """Not implemented until a Propio HTML sample is available."""
        self._pending("pais_del_visitante")

    def get_moneda(self) -> str:
        """Not implemented until a Propio HTML sample is available."""
        self._pending("moneda")

    def get_price(self) -> Decimal:
        """Not implemented until a Propio HTML sample is available."""
        self._pending("price")

    def get_income(self) -> Decimal:
        """Not implemented until a Propio HTML sample is available."""
        self._pending("income")

    def get_estado(self) -> ReservaEstado:
        """Not implemented until a Propio HTML sample is available."""
        self._pending("estado")

    def to_draft(self) -> ReservaDraft:
        """Not implemented until a Propio HTML sample is available."""
        self._pending("booking_provider")
