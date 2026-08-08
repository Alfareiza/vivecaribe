"""Auth HTTP routes: register and login."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from vivecaribe.api.deps import PasswordHasherDep, TokenServiceDep, UserRepo
from vivecaribe.api.schemas.auth import (
    LoginRequest,
    TokenResponse,
    UserCreate,
    UserResponse,
)
from vivecaribe.application.auth import LoginUserUseCase, RegisterUserUseCase
from vivecaribe.domain.errors import ConflictError, DomainError

router = APIRouter(tags=["auth"])


@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_user(
    payload: UserCreate,
    users: UserRepo,
    password_hasher: PasswordHasherDep,
) -> UserResponse:
    """Create a new user account (public)."""
    use_case = RegisterUserUseCase(users, password_hasher)
    try:
        user = await use_case.execute(email=payload.email, password=payload.password)
    except ConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return UserResponse.model_validate(user)


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    users: UserRepo,
    password_hasher: PasswordHasherDep,
    tokens: TokenServiceDep,
) -> TokenResponse:
    """Exchange email + password for a JWT access token."""
    use_case = LoginUserUseCase(users, password_hasher, tokens)
    try:
        access_token = await use_case.execute(
            email=payload.email,
            password=payload.password,
        )
    except DomainError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    return TokenResponse(access_token=access_token)
