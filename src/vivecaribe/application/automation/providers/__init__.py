"""Booking extractors — one module per booking channel.

Each module owns that channel's HTML extractor (parsing + income).
Inbox config (mailbox, query, credentials) stays in ``booking_providers.yaml``.
"""

from __future__ import annotations

from vivecaribe.application.automation.providers.base import BaseExtractor
from vivecaribe.application.automation.providers.getyourguide import (
    GetYourGuideExtractor,
)
from vivecaribe.application.automation.providers.homefans import HomefansExtractor
from vivecaribe.application.automation.providers.propio import PropioExtractor
from vivecaribe.application.automation.providers.viator import ViatorExtractor
from vivecaribe.domain.enums import BookingProvider

EXTRACTORS: dict[BookingProvider, type[BaseExtractor]] = {
    GetYourGuideExtractor.booking_provider: GetYourGuideExtractor,
    HomefansExtractor.booking_provider: HomefansExtractor,
    ViatorExtractor.booking_provider: ViatorExtractor,
    PropioExtractor.booking_provider: PropioExtractor,
}

__all__ = [
    "BaseExtractor",
    "EXTRACTORS",
    "GetYourGuideExtractor",
    "HomefansExtractor",
    "PropioExtractor",
    "ViatorExtractor",
]
