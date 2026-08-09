"""Auth HTTP routes: register, login, refresh, and logout."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response, status

from vivecaribe.api.cookies import (
    REFRESH_COOKIE_NAME,
    clear_refresh_cookie,
    set_refresh_cookie,
)
from vivecaribe.api.deps import (
    DbSession,
    PasswordHasherDep,
    RefreshTokenRepo,
    TokenServiceDep,
    UserRepo,
)
from vivecaribe.api.schemas.auth import (
    LoginRequest,
    TokenResponse,
    UserCreate,
    UserResponse,
)
from vivecaribe.application.auth import (
    LoginUserUseCase,
    LogoutUserUseCase,
    RefreshAccessTokenUseCase,
    RegisterUserUseCase,
)
from vivecaribe.domain.errors import ConflictError, DomainError
from vivecaribe.settings import get_settings

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
    response: Response,
    users: UserRepo,
    password_hasher: PasswordHasherDep,
    tokens: TokenServiceDep,
    refresh_tokens: RefreshTokenRepo,
) -> TokenResponse:
    """Exchange email + password for an access JWT and HttpOnly refresh cookie."""
    settings = get_settings()
    use_case = LoginUserUseCase(
        users,
        password_hasher,
        tokens,
        refresh_tokens,
        refresh_expire_days=settings.jwt_refresh_expire_days,
    )
    try:
        pair = await use_case.execute(
            email=payload.email,
            password=payload.password,
        )
    except DomainError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    set_refresh_cookie(response, pair.refresh_token, settings)
    return TokenResponse(access_token=pair.access_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request,
    response: Response,
    session: DbSession,
    users: UserRepo,
    tokens: TokenServiceDep,
    refresh_tokens: RefreshTokenRepo,
) -> TokenResponse:
    """Mint a new access JWT from the HttpOnly refresh cookie (rotates cookie)."""
    settings = get_settings()
    raw = request.cookies.get(REFRESH_COOKIE_NAME)
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    use_case = RefreshAccessTokenUseCase(
        users,
        tokens,
        refresh_tokens,
        refresh_expire_days=settings.jwt_refresh_expire_days,
    )
    try:
        pair = await use_case.execute(raw_refresh_token=raw)
    except DomainError as exc:
        # Commit before 401 so reuse / revoke side-effects are not rolled back.
        await session.commit()
        clear_refresh_cookie(response, settings)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    set_refresh_cookie(response, pair.refresh_token, settings)
    return TokenResponse(access_token=pair.access_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    tokens: TokenServiceDep,
    refresh_tokens: RefreshTokenRepo,
) -> None:
    """Revoke the refresh-token family and clear the HttpOnly cookie."""
    settings = get_settings()
    raw = request.cookies.get(REFRESH_COOKIE_NAME)
    use_case = LogoutUserUseCase(tokens, refresh_tokens)
    await use_case.execute(raw_refresh_token=raw)
    clear_refresh_cookie(response, settings)
