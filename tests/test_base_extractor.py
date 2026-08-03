"""Doctests and helpers for ``BaseExtractor``."""

from __future__ import annotations

import doctest

from vivecaribe.application.automation.providers import base


def test_normalize_phone_doctests() -> None:
    """Run doctests defined on ``BaseExtractor.normalize_phone``."""
    failures, tests_run = doctest.testmod(base)
    assert tests_run >= 6
    assert failures == 0
