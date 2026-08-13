"""Doctests and helpers for ``BaseExtractor``."""

from __future__ import annotations

import doctest
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from vivecaribe.application.automation.providers import base
from vivecaribe.application.automation.providers.base import BaseExtractor
from vivecaribe.domain.errors import ValidationError


def test_normalize_phone_doctests() -> None:
    """Run doctests defined on ``BaseExtractor.normalize_phone``."""
    failures, tests_run = doctest.testmod(base)
    assert tests_run >= 6
    assert failures == 0


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("186,00", Decimal("186.00")),
        ("89.68", Decimal("89.68")),
        ("$150.00 USD", Decimal("150.00")),
        ("1.234,56", Decimal("1234.56")),
        ("1,234.56", Decimal("1234.56")),
    ],
)
def test_parse_decimal_formats(raw: str, expected: Decimal) -> None:
    """Common EU/US money formats parse to Decimal."""
    assert BaseExtractor.parse_decimal(raw) == expected


def test_parse_decimal_invalid_raises() -> None:
    """Non-numeric amounts raise ValidationError."""
    with pytest.raises(ValidationError, match="Invalid amount"):
        BaseExtractor.parse_decimal("not-a-price")


def test_parse_datetime_naive_and_aware() -> None:
    """Naive datetimes become UTC; aware values convert to UTC."""
    naive = BaseExtractor.parse_datetime("2026-07-01 15:30")
    assert naive == datetime(2026, 7, 1, 15, 30)


def test_parse_datetime_invalid_raises() -> None:
    """Unrecognized datetime strings raise ValidationError."""
    with pytest.raises(ValidationError, match="Invalid datetime"):
        BaseExtractor.parse_datetime("not-a-date")


def test_require_text_empty_raises() -> None:
    """Blank/None values raise ValidationError for the given field."""
    assert BaseExtractor.require_text("  hello ", field="name") == "hello"
    with pytest.raises(ValidationError, match="name"):
        BaseExtractor.require_text("  ", field="name")
    with pytest.raises(ValidationError, match="name"):
        BaseExtractor.require_text(None, field="name")
