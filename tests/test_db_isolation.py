"""Guard: destructive fixtures must not target the local/dev database."""

import pytest

from tests.conftest import assert_is_test_database


def test_assert_is_test_database_allows_test_suffix() -> None:
    """Names ending in ``_test`` are accepted."""
    assert_is_test_database(
        "postgresql+asyncpg://postgres:postgres@localhost:5433/vivecaribe_test",
    )


def test_assert_is_test_database_rejects_dev_db() -> None:
    """The local ``vivecaribe`` database must never be reset by fixtures."""
    with pytest.raises(RuntimeError, match="vivecaribe"):
        assert_is_test_database(
            "postgresql+asyncpg://postgres:postgres@localhost:5433/vivecaribe",
        )
