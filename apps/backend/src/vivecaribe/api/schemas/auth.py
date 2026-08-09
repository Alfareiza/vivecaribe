"""Auth request/response schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """Payload for ``POST /users``."""

    email: EmailStr
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    """Payload for ``POST /login``."""

    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Public user representation (never includes password hash)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    is_active: bool
    created_at: datetime


class TokenResponse(BaseModel):
    """Access JWT returned after login or refresh (refresh stays in cookie)."""

    access_token: str
    token_type: str = "bearer"
