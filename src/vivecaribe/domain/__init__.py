"""Core business domain (entities, ports, errors).

No FastAPI, SQLAlchemy, email providers, or WhatsApp here.
"""

from vivecaribe.domain.enums import BookingProvider, ReservaEstado
from vivecaribe.domain.errors import (
    ConflictError,
    DomainError,
    NotFoundError,
    ValidationError,
)
from vivecaribe.domain.ports import (
    PasswordHasher,
    ReservaRepository,
    TokenService,
    UserRepository,
)
from vivecaribe.domain.reserva import Reserva
from vivecaribe.domain.user import User

__all__ = [
    "BookingProvider",
    "ConflictError",
    "DomainError",
    "NotFoundError",
    "PasswordHasher",
    "Reserva",
    "ReservaEstado",
    "ReservaRepository",
    "TokenService",
    "User",
    "UserRepository",
    "ValidationError",
]
