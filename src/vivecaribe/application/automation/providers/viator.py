"""Viator — HTML extraction and income."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Self

from bs4 import BeautifulSoup

from vivecaribe.application.automation.models import ReservaDraft
from vivecaribe.application.automation.providers.base import BaseExtractor
from vivecaribe.domain.enums import BookingProvider, ReservaEstado
from vivecaribe.domain.errors import ValidationError


class ViatorExtractor(BaseExtractor):
    """Parse Viator booking HTML (stand-in fixture until a real sample lands)."""

    booking_provider = BookingProvider.VIATOR

    def __init__(self, soup: BeautifulSoup) -> None:
        """Store parsed HTML."""
        self._soup = soup

    @classmethod
    def from_html(cls, html: str) -> Self:
        """Build an extractor from raw HTML."""
        return cls(BeautifulSoup(html, "html.parser"))

    def _after_label(self, label: str) -> str:
        """Return value from a ``<p>Label: value</p>`` line."""
        prefix = f"{label}:"
        for paragraph in self._soup.find_all("p"):
            text = paragraph.get_text(" ", strip=True)
            if text.startswith(prefix):
                return self.require_text(text[len(prefix) :], field=label)
        raise ValidationError(f"Could not parse {label}", field=label)

    def get_reserva_reference(self) -> str:
        """Return the Viator booking reference."""
        return self._after_label("Booking reference")

    def get_nombre_experiencia(self) -> str:
        """Return the experience title."""
        return self._after_label("Experience")

    def get_ciudad_evento(self) -> str:
        """Return the city from the experience title."""
        title = self.get_nombre_experiencia()
        if ":" not in title:
            return "Cartagena"
        return title.split(":", 1)[0].strip()

    def get_dt_evento(self) -> datetime:
        """Return the experience date/time."""
        return self.parse_datetime(self._after_label("Date"))

    def get_participants(self) -> int:
        """Return traveler count."""
        raw = self._after_label("Travelers")
        try:
            return int(raw.split()[0])
        except ValueError as exc:
            raise ValidationError(
                f"Could not parse participants: {raw}",
                field="participants",
            ) from exc

    def get_customer_name(self) -> str:
        """Return the lead traveler name."""
        return self._after_label("Lead traveler")

    def get_phone(self) -> str:
        """Return the customer phone, or empty string if missing."""
        try:
            return self._after_label("Phone")
        except ValidationError:
            return ""

    def get_pais_del_visitante(self) -> str:
        """Return visitor country when present."""
        return ""

    def get_moneda(self) -> str:
        """Return currency code from the total line when present."""
        raw = self._after_label("Total")
        token = raw.split()[-1].upper()
        if token in {"USD", "EUR"}:
            return token
        return "USD"

    def get_price(self) -> Decimal:
        """Return the booking total."""
        return self.parse_decimal(self._after_label("Total"))

    def get_income(self) -> Decimal:
        """Return operator income for this Viator booking.

        Pending: booking-provider-specific commission formula.
        """
        # TODO: Viator income formula.
        return self.get_price()

    def get_estado(self) -> ReservaEstado:
        """Return reservation lifecycle state inferred from this email."""
        return ReservaEstado.CONFIRMADA

    def to_draft(self) -> ReservaDraft:
        """Assemble a ``ReservaDraft`` from all getters."""
        return ReservaDraft(
            booking_provider=self.booking_provider,
            reserva_reference=self.get_reserva_reference(),
            estado=self.get_estado(),
            nombre_experiencia=self.get_nombre_experiencia(),
            ciudad_experiencia=self.get_ciudad_evento(),
            fecha_evento=self.get_dt_evento(),
            participants=self.get_participants(),
            customer_name=self.get_customer_name(),
            phone=self.get_phone(),
            pais_del_visitante=self.get_pais_del_visitante(),
            moneda=self.get_moneda(),
            price=self.get_price(),
            income=self.get_income(),
        )
