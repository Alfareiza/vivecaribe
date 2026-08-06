"""ASGI entrypoint for Vercel native FastAPI (unused when ``Dockerfile.vercel`` is active)."""

from vivecaribe.main import app

__all__ = ["app"]
