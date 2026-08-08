"""Viator — HTML extraction and income."""

from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal
from typing import Self

from bs4 import BeautifulSoup
from phonenumbers import NumberParseException, phonenumber
import phonenumbers

from vivecaribe.application.automation.models import ReservaDraft
from vivecaribe.application.automation.providers.base import BaseExtractor
from vivecaribe.domain.enums import BookingProvider, ReservaEstado
from vivecaribe.domain.errors import ValidationError
from vivecaribe.logging import logger


class ViatorExtractor(BaseExtractor):
    """Parse Viator supplier booking-confirmation HTML (Spanish labels)."""

    booking_provider = BookingProvider.VIATOR

    def __init__(self, soup: BeautifulSoup) -> None:
        """Store parsed HTML."""
        self._soup = soup

    @classmethod
    def from_html(cls, html: str) -> Self:
        """Build an extractor from raw HTML."""
        return cls(BeautifulSoup(html, "html.parser"))

    def _value_after_label(self, label: str) -> str:
        """Return the span/text value after ``Label:`` inside a ``<td>``."""
        prefix = f"{label}:"
        for cell in self._soup.find_all("td"):
            text = cell.get_text(" ", strip=True)
            if not text.startswith(prefix):
                continue
            span = cell.find("span")
            if span is not None:
                return self.require_text(span.get_text(strip=True), field=label)
            return self.require_text(text[len(prefix) :], field=label)
        raise ValidationError(f"Could not parse {label}", field=label)

    def get_reserva_reference(self) -> str:
        """Return the Viator booking reference (e.g. ``BR-1429496135``)."""
        return self._value_after_label("Referencia de la reserva")

    def get_nombre_experiencia(self) -> str:
        """Return the experience / activity title."""
        return self._value_after_label("Nombre de la excursión o actividad")

    def get_ciudad_evento(self) -> str:
        """Return the city from ``Ubicación`` (e.g. ``Barranquilla, Colombia``)."""
        location = self._value_after_label("Ubicación")
        return location.split(",", 1)[0].strip()

    def get_dt_evento(self) -> datetime:
        """Return the travel date."""
        return self.parse_datetime(self._value_after_label("Fecha del viaje"))

    def get_participants(self) -> int:
        """Return traveler count from ``Viajeros`` (e.g. ``1 adulto``)."""
        raw = self._value_after_label("Viajeros")
        token = raw.split()[0] if raw else ""
        try:
            return int(token)
        except ValueError as exc:
            raise ValidationError(
                f"Could not parse participants: {raw}",
                field="participants",
            ) from exc

    def get_customer_name(self) -> str:
        """Return the lead traveler name."""
        return self._value_after_label("Nombre del viajero principal")

    def get_phone(self) -> str:
        """Return the customer phone when present (digits only, keep leading ``+``)."""
        try:
            for selector_text in "Teléfono", "Teléfono Alternativo":
                raw = self._value_after_label(selector_text)
                if parsed := phonenumbers.parse(raw, None):
                    break
        except (ValidationError, NumberParseException):
            return ""
        else:
            return str(phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164))

    def get_moneda(self) -> str:
        """Return currency code from ``Tarifa neta`` (e.g. ``USD $78.40``)."""
        raw = self._value_after_label("Tarifa neta")
        token = raw.split()[0].upper() if raw.split() else ""
        if token in {"USD", "EUR", "COP"}:
            return token
        return "USD"

    def get_price(self) -> Decimal:
        """Return the net rate (``Tarifa neta``)."""
        return self.get_income() * Decimal("1.31")

    def get_income(self) -> Decimal:
        """Return operator income for this Viator booking.

        Pending: booking-provider-specific commission formula.
        """
        return self.parse_decimal(self._value_after_label("Tarifa neta"))

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
