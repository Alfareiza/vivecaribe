"""Core business domain (entities, errors).

No FastAPI, SQLAlchemy, mailbox clients, or WhatsApp here.
"""

from vivecaribe.domain.email_message import EmailMessage
from vivecaribe.domain.enums import (
    BookingProvider,
    MeetingPoint,
    ReservaEstado,
    TipoTour,
)
from vivecaribe.domain.errors import (
    ConflictError,
    DomainError,
    EmailNotFound,
    NotFoundError,
    ValidationError,
)
from vivecaribe.domain.reserva import Reserva, compute_paid_at
from vivecaribe.domain.user import User

__all__ = [
    "BookingProvider",
    "ConflictError",
    "DomainError",
    "EmailMessage",
    "EmailNotFound",
    "MeetingPoint",
    "NotFoundError",
    "Reserva",
    "ReservaEstado",
    "TipoTour",
    "User",
    "ValidationError",
    "compute_paid_at",
]
