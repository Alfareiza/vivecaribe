"""Logging configuration and JSON formatter."""

from __future__ import annotations

import json
import logging

from rich.logging import RichHandler

from vivecaribe.logging import JsonFormatter, configure_logging, correlation_id_var
from vivecaribe.settings import Settings


def _settings(*, environment: str = "local", log_level: str = "INFO") -> Settings:
    return Settings(
        environment=environment,  # type: ignore[arg-type]
        log_level=log_level,
        database_url="postgresql+asyncpg://u:p@localhost/db",
        jwt_secret="secret",
        cron_secret="cron",
    )


def test_configure_logging_local_uses_rich() -> None:
    """Local environment installs a RichHandler."""
    configure_logging(_settings(environment="local"))
    root = logging.getLogger()
    assert any(isinstance(h, RichHandler) for h in root.handlers)


def test_configure_logging_staging_uses_json() -> None:
    """Non-local environments use the JSON formatter."""
    configure_logging(_settings(environment="staging"))
    root = logging.getLogger()
    assert any(isinstance(h.formatter, JsonFormatter) for h in root.handlers)


def test_json_formatter_with_correlation_id_and_exc_info() -> None:
    """JSON payload includes correlation_id and exception text when present."""
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="vivecaribe",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg="boom",
        args=(),
        exc_info=None,
    )
    token = correlation_id_var.set("corr-1")
    try:
        payload = json.loads(formatter.format(record))
    finally:
        correlation_id_var.reset(token)

    assert payload["message"] == "boom"
    assert payload["correlation_id"] == "corr-1"

    try:
        raise ValueError("x")
    except ValueError:
        import sys

        record.exc_info = sys.exc_info()
        with_exc = json.loads(formatter.format(record))
        assert "ValueError" in with_exc["exc_info"]
