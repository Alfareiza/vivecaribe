"""HttpOnly refresh-token cookie helpers for auth routes."""

from __future__ import annotations

from fastapi import Response

from vivecaribe.settings import Settings

REFRESH_COOKIE_NAME = "refresh_token"


def refresh_cookie_secure(settings: Settings) -> bool:
    """Return whether the refresh cookie should set the ``Secure`` flag."""
    return settings.environment != "local"


def refresh_cookie_samesite(settings: Settings) -> str:
    """Return SameSite mode for the refresh cookie.

    Local HTTP uses ``lax`` (localhost ports are same-site). Staging/prod use
    ``none`` so the dual-Vercel frontend can send the cookie cross-origin with
    ``credentials: "include"``.
    """
    return "lax" if settings.environment == "local" else "none"


def set_refresh_cookie(
    response: Response,
    raw_token: str,
    settings: Settings,
) -> None:
    """Attach the opaque refresh token as an HttpOnly cookie."""
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=raw_token,
        httponly=True,
        secure=refresh_cookie_secure(settings),
        samesite=refresh_cookie_samesite(settings),
        path="/",
        max_age=settings.jwt_refresh_expire_days * 24 * 60 * 60,
    )


def clear_refresh_cookie(response: Response, settings: Settings) -> None:
    """Clear the refresh cookie using the same flags used when setting it."""
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path="/",
        secure=refresh_cookie_secure(settings),
        samesite=refresh_cookie_samesite(settings),
    )
