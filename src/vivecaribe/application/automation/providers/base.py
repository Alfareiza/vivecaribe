"""Shared base class for booking HTML extractors."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Self

from vivecaribe.application.automation.models import ReservaDraft
from vivecaribe.domain.enums import BookingProvider
from vivecaribe.domain.errors import ValidationError

# Leading ``+`` optional; allows spaces, dashes, dots, and parentheses.
_PHONE_CANDIDATE = re.compile(r"\+?\d[\d\s().-]{5,}\d")


class BaseExtractor(ABC):
    """Contract every booking extractor must satisfy."""

    booking_provider: BookingProvider

    @classmethod
    @abstractmethod
    def from_html(cls, html: str) -> Self:
        """Build an extractor from raw HTML."""

    @abstractmethod
    def to_draft(self) -> ReservaDraft:
        """Assemble a ``ReservaDraft`` from parsed fields."""

    @staticmethod
    def normalize_phone(raw: str) -> str:
        """Return a compact phone: optional ``+`` plus digits only.

        Finds the first phone-like token in ``raw``, keeps a leading ``+`` when
        present, and strips spaces, dashes, parentheses, and other separators.

        >>> BaseExtractor.normalize_phone("+1 (813) 735-0000")
        '+18137350000'
        >>> BaseExtractor.normalize_phone("(Teléfono alternativo)US+1 (813) 735-0000")
        '+18137350000'
        >>> BaseExtractor.normalize_phone("+1 662 570 9162")
        '+16625709162'
        >>> BaseExtractor.normalize_phone("0031 641 428 471")
        '0031641428471'
        >>> BaseExtractor.normalize_phone("")
        ''
        >>> BaseExtractor.normalize_phone("no phone here")
        ''
        """
        text = raw.strip()
        if not text:
            return ""

        match = _PHONE_CANDIDATE.search(text)
        if match is None:
            return ""

        candidate = match.group(0)
        has_plus = candidate.startswith("+")
        digits = re.sub(r"\D", "", candidate)
        if not digits:
            return ""
        return f"+{digits}" if has_plus else digits

    @staticmethod
    def parse_decimal(raw: str) -> Decimal:
        """Parse amounts like ``186,00``, ``89.68``, ``$150.00 USD``."""
        token = raw.strip().replace("\xa0", " ")
        for part in token.replace("$", " ").replace("€", " ").split():
            if any(ch.isdigit() for ch in part):
                token = part
                break
        cleaned = token.replace(" ", "")
        if "," in cleaned and "." in cleaned:
            if cleaned.rfind(",") > cleaned.rfind("."):
                cleaned = cleaned.replace(".", "").replace(",", ".")
            else:
                cleaned = cleaned.replace(",", "")
        elif "," in cleaned:
            cleaned = cleaned.replace(",", ".")
        try:
            return Decimal(cleaned)
        except InvalidOperation as exc:
            raise ValidationError(f"Invalid amount: {raw}", field="price") from exc

    @staticmethod
    def parse_datetime(raw: str) -> datetime:
        """Parse common booking-email datetime shapes as timezone-aware UTC."""
        candidates = (
            "%a, %b %d, %Y",
            "%B %d, %Y %I:%M %p",
            "%B %d, %Y %H:%M",
            "%b %d, %Y %I:%M %p",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S",
        )
        text = " ".join(raw.split())
        for fmt in candidates:
            try:
                dt = datetime.strptime(text, fmt)
            except ValueError:
                continue
            if dt.tzinfo is None:
                return dt.replace(tzinfo=UTC)
            return dt.astimezone(UTC)
        raise ValidationError(f"Invalid datetime: {raw}", field="fecha_evento")

    @staticmethod
    def require_text(value: str | None, *, field: str) -> str:
        """Return stripped text or raise ``ValidationError``."""
        if value is None or not value.strip():
            raise ValidationError(f"Could not parse {field}", field=field)
        return value.strip()
