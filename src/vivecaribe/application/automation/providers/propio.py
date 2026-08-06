"""Propio (Grupo Vive Caribe / WooCommerce) — HTML extraction."""

from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal
from typing import Self

import phonenumbers
from bs4 import BeautifulSoup, Tag
from phonenumbers import NumberParseException, region_code_for_number

from vivecaribe.application.automation.models import ReservaDraft
from vivecaribe.application.automation.providers.base import BaseExtractor
from vivecaribe.domain.enums import BookingProvider, ReservaEstado
from vivecaribe.domain.errors import ValidationError
from vivecaribe.logging import logger

_SPANISH_MONTHS: dict[str, str] = {
    "enero": "January",
    "febrero": "February",
    "marzo": "March",
    "abril": "April",
    "mayo": "May",
    "junio": "June",
    "julio": "July",
    "agosto": "August",
    "septiembre": "September",
    "octubre": "October",
    "noviembre": "November",
    "diciembre": "December",
}


class PropioExtractor(BaseExtractor):
    """Parse Grupo Vive Caribe (WooCommerce) new-order HTML."""

    booking_provider = BookingProvider.PROPIO
    # Alias (casefolded) → canonical city name returned on drafts.
    CITY_ALIASES: dict[str, str] = {
        "barranquilla": "Barranquilla",
        "cartagena": "Cartagena",
        "santa marta": "Santa Marta",
        "bogotá": "Bogotá",
        "bogota": "Bogotá",
        "medellín": "Medellín",
        "medellin": "Medellín",
    }

    def __init__(self, soup: BeautifulSoup) -> None:
        """Store parsed HTML."""
        self._soup = soup

    @classmethod
    def from_html(cls, html: str) -> Self:
        """Build an extractor from raw HTML."""
        return cls(BeautifulSoup(html, "html.parser"))

    def _order_item_cell(self) -> Tag:
        """Return the product description cell of the first order line."""
        row = self._soup.select_one('tr[class*="order_item"]')
        if row is None:
            raise ValidationError("Could not find order item", field="nombre_experiencia")
        cell = row.find("td")
        if not isinstance(cell, Tag):
            raise ValidationError("Could not find order item", field="nombre_experiencia")
        return cell

    @staticmethod
    def _collapse(text: str) -> str:
        """Collapse internal whitespace from Zoho-mangled HTML text nodes."""
        return " ".join(text.split())

    def get_reserva_reference(self) -> str:
        """Return the WooCommerce order number digits (e.g. ``1995``)."""
        heading = self._soup.find("h1")
        text = self.require_text(
            self._collapse(heading.get_text(" ", strip=True)) if heading else None,
            field="reserva_reference",
        )
        match = re.search(r"#\s*(\d+)", text)
        if match is None:
            raise ValidationError(
                "Could not parse reserva_reference",
                field="reserva_reference",
            )
        return match.group(1)

    def get_nombre_experiencia(self) -> str:
        """Return the purchased experience title."""
        cell = self._order_item_cell()
        title = cell.find("h3")
        raw = self._collapse(title.get_text(" ", strip=True)) if title else None
        return self.require_text(raw, field="nombre_experiencia")

    def get_ciudad_evento(self) -> str:
        """Return the event city found in the experience title, or empty string."""
        title = self.get_nombre_experiencia()
        lowered = title.casefold()
        for alias, canonical in sorted(
            self.CITY_ALIASES.items(),
            key=lambda item: len(item[0]),
            reverse=True,
        ):
            if alias in lowered:
                return canonical
        logger.warning(f"Propio ciudad_experiencia not found in title={title!r}")
        return ""

    def get_dt_evento(self) -> datetime:
        """Return the trip date/time from the order line."""
        cell = self._order_item_cell()
        text = self._collapse(cell.get_text(" ", strip=True))
        match = re.search(
            r"Trip\s+Date:\s*(.+?)(?:\s*Pax:|$)",
            text,
            flags=re.IGNORECASE,
        )
        if match is None:
            raise ValidationError("Could not parse fecha_evento", field="fecha_evento")
        raw = match.group(1).strip()
        for spanish, english in _SPANISH_MONTHS.items():
            if spanish in raw.casefold():
                raw = re.sub(spanish, english, raw, count=1, flags=re.IGNORECASE)
                break
        return self.parse_datetime(raw)

    def get_participants(self) -> int:
        """Return guest count from the ``Guest x N`` line."""
        cell = self._order_item_cell()
        text = self._collapse(cell.get_text(" ", strip=True))
        match = re.search(r"Guest\s*x\s*(\d+)", text, flags=re.IGNORECASE)
        if match is None:
            raise ValidationError("Could not parse participants", field="participants")
        return int(match.group(1))

    def get_customer_name(self) -> str:
        """Return the buyer name from the introduction line."""
        intro = self._soup.select_one('[class*="email-introduction"]')
        text = self._collapse(intro.get_text(" ", strip=True)) if intro else ""
        match = re.search(
            r"new order from\s+(.+?)\s*:",
            text,
            flags=re.IGNORECASE,
        )
        if match is None:
            raise ValidationError("Could not parse customer_name", field="customer_name")
        return self.require_text(match.group(1), field="customer_name")

    def get_phone(self) -> str:
        """Return the customer phone from the billing ``tel:`` link."""
        link = self._soup.select_one('a[href^="tel:"]')
        if link is None:
            return ""
        href = str(link.get("href", ""))
        raw = href.removeprefix("tel:")
        return self.normalize_phone(raw or link.get_text(strip=True))

    def get_pais_del_visitante(self) -> str:
        """Return ISO alpha-2 country inferred from the customer phone."""
        phone = self.get_phone()
        if not phone:
            return ""
        try:
            parsed = phonenumbers.parse(phone, None)
        except NumberParseException:
            return ""
        region = region_code_for_number(parsed)
        return region or ""

    def get_moneda(self) -> str:
        """Return ``USD`` when a ``$`` amount is present in the order total."""
        total = self._total_amount_node()
        if total is None:
            raise ValidationError("Could not parse moneda", field="moneda")
        text = total.get_text(" ", strip=True)
        if "$" in text:
            return "USD"
        raise ValidationError(f"Unsupported currency in {text!r}", field="moneda")

    def _total_amount_node(self) -> Tag | None:
        """Return the Total row amount node when present."""
        for th in self._soup.find_all("th"):
            if th.get_text(" ", strip=True).rstrip(":") != "Total":
                continue
            td = th.find_next("td")
            if td is None:
                return None
            amount = td.select_one('[class*="woocommerce-Price-amount"]')
            return amount if amount is not None else td
        return None

    def get_price(self) -> Decimal:
        """Return the order total as ``Decimal``."""
        node = self._total_amount_node()
        if node is None:
            raise ValidationError("Could not parse price", field="price")
        return self.parse_decimal(node.get_text(" ", strip=True))

    def get_income(self) -> Decimal:
        """Return operator income — same as price for Propio."""
        return self.get_price()

    def get_estado(self) -> ReservaEstado:
        """Return reservation lifecycle state for a new-order email."""
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
