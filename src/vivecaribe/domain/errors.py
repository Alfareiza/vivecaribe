"""Domain error hierarchy (business failures, not infra/transport)."""

from __future__ import annotations


class DomainError(Exception):
    """Base class for expected business-rule failures."""

    def __init__(self, message: str = "Domain error") -> None:
        """Store a human-readable error message.

        Args:
            message: Description of the business failure.
        """
        self.message = message
        super().__init__(message)


class ValidationError(DomainError):
    """Raised when domain input violates an invariant."""

    def __init__(
        self,
        message: str = "Validation failed",
        *,
        field: str | None = None,
    ) -> None:
        """Create a validation error, optionally tied to a field name.

        Args:
            message: Description of the validation failure.
            field: Optional field that failed validation.
        """
        self.field = field
        if field is not None:
            message = f"{field}: {message}"
        super().__init__(message)


class NotFoundError(DomainError):
    """Raised when a required domain entity cannot be found."""

    def __init__(
        self,
        message: str = "Entity not found",
        *,
        entity: str | None = None,
    ) -> None:
        """Create a not-found error for a domain entity.

        Args:
            message: Description of the missing entity.
            entity: Optional entity type name (e.g. ``\"User\"``).
        """
        self.entity = entity
        if entity is not None:
            message = f"{entity}: {message}"
        super().__init__(message)


class ConflictError(DomainError):
    """Raised when a unique business constraint would be violated."""


class EmailNotFound(DomainError):
    """Raised when an expected mailbox message cannot be found."""

    def __init__(self, message: str = "Email not found") -> None:
        """Create an email-not-found error.

        Args:
            message: Description of the missing email.
        """
        super().__init__(message)
