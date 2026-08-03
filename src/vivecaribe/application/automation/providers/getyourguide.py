"""GetYourGuide — HTML extraction and income."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Self

from bs4 import BeautifulSoup, Tag

from vivecaribe.application.automation.models import ReservaDraft
from vivecaribe.application.automation.providers.base import BaseExtractor
from vivecaribe.domain.enums import BookingProvider, ReservaEstado
from vivecaribe.domain.errors import ValidationError


class GetYourGuideExtractor(BaseExtractor):
    """Parse GetYourGuide booking confirmation HTML."""

    booking_provider = BookingProvider.GETYOURGUIDE

    def __init__(self, soup: BeautifulSoup) -> None:
        """Store parsed HTML."""
        self._soup = soup

    @classmethod
    def from_html(cls, html: str) -> Self:
        """Build an extractor from raw HTML."""
        return cls(BeautifulSoup(html, "html.parser"))

    def _right_content(self, label: str) -> Tag:
        """Return ``.right-content`` for a GYG ``p.title`` label."""
        for title in self._soup.select("p.title"):
            if title.get_text(strip=True) != label:
                continue
            content = title.find_parent("div", class_="content")
            if content is None:
                break
            right = content.select_one(".right-content")
            if right is not None:
                return right
        raise ValidationError(f"Could not parse {label}", field=label)

    def get_reserva_reference(self) -> str:
        """Return the GYG booking reference (e.g. ``GYGX7NG8ARBW``)."""
        right = self._right_content("Número de referencia")
        strong = right.find("strong")
        return self.require_text(
            strong.get_text(strip=True) if strong else right.get_text(strip=True),
            field="reserva_reference",
        )

    def get_nombre_experiencia(self) -> str:
        """Return the English experience title."""
        node = self._soup.select_one("p.activity-title")
        return self.require_text(
            node.get_text(" ", strip=True) if node else None,
            field="nombre_experiencia",
        )

    def get_ciudad_evento(self) -> str:
        """Return the city from the experience title."""
        title = self.get_nombre_experiencia()
        if ":" not in title:
            return "Cartagena"
        return title.split(":", 1)[0].strip()

    def get_dt_evento(self) -> datetime:
        """Return the experience date/time."""
        right = self._right_content("Fecha")
        return self.parse_datetime(right.get_text(" ", strip=True))

    def get_participants(self) -> int:
        """Return the number of participants."""
        right = self._right_content("Número de participantes")
        strong = right.find("strong")
        raw = strong.get_text(strip=True) if strong else right.get_text(strip=True)
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
        right = self._right_content("Cliente principal")
        for span in right.find_all("span"):
            text = span.get_text(strip=True)
            if text and ":" not in text and "@" not in text:
                return text
        raise ValidationError("Could not parse customer_name", field="customer_name")

    def get_phone(self) -> str:
        """Return the customer phone, or empty string if missing."""
        right = self._right_content("Cliente principal")
        for span in right.find_all("span"):
            text = span.get_text(" ", strip=True)
            if text.startswith("Teléfono:"):
                return self.normalize_phone(text.split(":", 1)[1])
        return ""

    def get_pais_del_visitante(self) -> str:
        """Return visitor country when present (often absent in GYG mail)."""
        return ""

    def get_moneda(self) -> str:
        """Return currency code for GYG bookings."""
        return "USD"

    def get_price(self) -> Decimal:
        """Return the booking price."""
        right = self._right_content("Precio")
        return self.parse_decimal(right.get_text(" ", strip=True))

    def get_income(self) -> Decimal:
        """Return operator income for this GYG booking.

        Pending: booking-provider-specific commission formula.
        """
        # TODO: GetYourGuide income formula.
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
