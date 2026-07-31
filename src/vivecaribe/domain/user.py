"""``User`` — platform account entity."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class User(BaseModel):
    """Authenticated platform user (auth / audit, not booking automation)."""

    model_config = ConfigDict(from_attributes=True, validate_assignment=True)

    email: EmailStr
    password_hash: str
    is_active: bool = True
    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        """Serialize this user to a JSON-friendly dict (includes hash)."""
        return self.model_dump(mode="json")
