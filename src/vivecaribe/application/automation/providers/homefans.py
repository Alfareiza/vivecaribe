"""Homefans — HTML extraction and income."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from functools import lru_cache
from typing import Self

from bs4 import BeautifulSoup
import pycountry

from vivecaribe.application.automation.models import ReservaDraft
from vivecaribe.application.automation.providers.base import BaseExtractor
from vivecaribe.domain.enums import BookingProvider, ReservaEstado
from vivecaribe.domain.errors import ValidationError
from vivecaribe.logging import logger


class HomefansExtractor(BaseExtractor):
    """Parse Homefans (WooCommerce) new-order HTML."""

    booking_provider = BookingProvider.HOMEFANS

    def __init__(self, soup: BeautifulSoup) -> None:
        """Store parsed HTML."""
        self._soup = soup

    @classmethod
    def from_html(cls, html: str) -> Self:
        """Build an extractor from raw HTML."""
        return cls(BeautifulSoup(html, "html.parser"))

    def _after_strong(self, label: str) -> str:
        """Return text after a Homefans ``<strong>Label:</strong>`` marker."""
        needle = label.rstrip(":")
        for strong in self._soup.find_all("strong"):
            if strong.get_text(strip=True).rstrip(":") != needle:
                continue
            parent = strong.parent
            if parent is None:
                break
            full = parent.get_text(" ", strip=True)
            prefix = strong.get_text(" ", strip=True)
            value = full[len(prefix) :].strip().lstrip(":").strip()
            return self.require_text(value, field=label)
        raise ValidationError(f"Could not parse {label}", field=label)

    def get_reserva_reference(self) -> str:
        """Return the Homefans order number."""
        heading = self._soup.find("h1")
        text = self.require_text(
            heading.get_text(" ", strip=True) if heading else None,
            field="reserva_reference",
        )
        if "#" not in text:
            raise ValidationError(
                "Could not parse reserva_reference",
                field="reserva_reference",
            )
        return text.split("#", 1)[1].strip()

    def get_nombre_experiencia(self) -> str:
        """Return the purchased experience name."""
        cell = self._soup.select_one("tr.order_item td")
        return self.require_text(
            cell.get_text(" ", strip=True) if cell else None,
            field="nombre_experiencia",
        )

    def get_ciudad_evento(self) -> str:
        """Return the event city from the experience name when present."""
        title = self.get_nombre_experiencia()
        if ":" in title:
            return title.split(":", 1)[0].strip()
        return title.split()[0] if title.split() else "Cartagena"

    def get_dt_evento(self) -> datetime:
        """Return the experience date/time."""
        return self.parse_datetime(self._after_strong("Experience date"))

    def get_participants(self) -> int:
        """Return quantity from the order line item."""
        cells = self._soup.select("tr.order_item td")
        if len(cells) < 2:
            raise ValidationError("Could not parse participants", field="participants")
        raw = cells[1].get_text(strip=True)
        try:
            return int(raw)
        except ValueError as exc:
            raise ValidationError(
                f"Could not parse participants: {raw}",
                field="participants",
            ) from exc

    def get_customer_name(self) -> str:
        """Return ``First Name`` + ``Last Name`` from customer details."""
        first = self._after_strong("First Name").capitalize()
        last = self._after_strong("Last Name").capitalize()
        return f"{first} {last}".strip()

    def get_phone(self) -> str:
        """Return the customer phone."""
        return self.normalize_phone(self._after_strong("Phone"))

    def get_pais_del_visitante(self) -> str:
        """Return the customer country in format 2-letter codes."""
        try:
            country = pycountry.countries.get(name=self._after_strong("Country"))
            return country.alpha_2
        except AttributeError:
            return super().get_pais_del_visitante()

    def get_moneda(self) -> str:
        """Return currency code for Homefans bookings."""
        return "EUR"

    @lru_cache
    def prices(self) -> list(Decimal, Decimal, Decimal, Decimal):
        """Return the 4 detectes prices in the e-mail."""
        all_prices = self._soup.find_all("span", class_=["woocommerce-Price-amount", "amount"])
        return [self.parse_decimal(price.get_text(strip=True)) for price in all_prices]

    def get_price(self) -> Decimal:
        """Return order total (not subtotal)."""
        for th in self._soup.find_all("th"):
            if th.get_text(" ", strip=True).rstrip(":") != "Total":
                continue
            td = th.find_next("td")
            if td is None:
                break
            amount = td.select_one(".woocommerce-Price-amount")
            raw = (amount or td).get_text(" ", strip=True)
            return self.parse_decimal(raw)
        raise ValidationError("Could not parse price", field="price")

    def get_income(self) -> Decimal:
        """Return operator income for this Homefans booking.

        Pending: booking-provider-specific commission formula.
        """
        try:
            income, *_ = self.prices()
            return income * Decimal(0.75)
        except ValueError:
            logger.exception('Se esperaban 4 valores referentes a precio en e-mail')
            return ""
        
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
