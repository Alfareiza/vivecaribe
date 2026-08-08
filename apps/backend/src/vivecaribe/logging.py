"""Shared package logger — Rich locally, JSON-friendly elsewhere.

Usage elsewhere::

    from vivecaribe.logging import logger

    logger.info("something happened")
"""

from __future__ import annotations

import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from rich.console import Console
from rich.logging import RichHandler

if TYPE_CHECKING:
    from vivecaribe.settings import Settings

correlation_id_var: ContextVar[str | None] = ContextVar(
    "correlation_id",
    default=None,
)


class JsonFormatter(logging.Formatter):
    """Minimal structured JSON formatter for non-local environments."""

    def format(self, record: logging.LogRecord) -> str:
        """Serialize a log record as a single-line JSON object."""
        payload: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "line": record.lineno,
            "message": record.getMessage(),
        }
        correlation_id = correlation_id_var.get()
        if correlation_id:
            payload["correlation_id"] = correlation_id
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(settings: Settings) -> None:
    """Configure root logging once at application startup."""
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(settings.log_level)

    if settings.environment == "local":
        handler: logging.Handler = RichHandler(
            console=Console(stderr=True),
            rich_tracebacks=True,
            show_path=False,
            markup=True,
        )
        handler.setFormatter(
            logging.Formatter("[%(module)s:%(lineno)d] %(message)s"),
        )
    else:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())

    root.addHandler(handler)

    # Quiet noisy third-party loggers in local/dev.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


# Import this everywhere: ``from vivecaribe.logging import logger``.
logger = logging.getLogger("vivecaribe")
