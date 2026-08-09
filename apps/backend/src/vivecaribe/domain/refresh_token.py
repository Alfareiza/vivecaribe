"""``RefreshToken`` — revocable session credential for minting access JWTs."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class RefreshToken(BaseModel):
    """Opaque refresh credential persisted as a hash (never store raw)."""

    model_config = ConfigDict(from_attributes=True, validate_assignment=True)

    user_id: UUID
    family_id: UUID
    token_hash: str
    expires_at: datetime
    id: UUID = Field(default_factory=uuid4)
    revoked_at: datetime | None = None
    replaced_by_id: UUID | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @property
    def is_revoked(self) -> bool:
        """Return ``True`` when this token has been revoked."""
        return self.revoked_at is not None

    @property
    def is_expired(self) -> bool:
        """Return ``True`` when ``expires_at`` is in the past."""
        return self.expires_at <= datetime.now(UTC)
