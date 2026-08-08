"""Core business domain (entities, errors).

No FastAPI, SQLAlchemy, mailbox clients, or WhatsApp here.
"""

from vivecaribe.domain.email_message import EmailMessage
from vivecaribe.domain.enums import BookingProvider, ReservaEstado
from vivecaribe.domain.errors import (
    ConflictError,
    DomainError,
    EmailNotFound,
    NotFoundError,
    ValidationError,
)
from vivecaribe.domain.reserva import Reserva
from vivecaribe.domain.user import User

__all__ = [
    "BookingProvider",
    "ConflictError",
    "DomainError",
    "EmailMessage",
    "EmailNotFound",
    "NotFoundError",
    "Reserva",
    "ReservaEstado",
    "User",
    "ValidationError",
]
