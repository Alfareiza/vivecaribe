"""ASGI entrypoint kept for local/native FastAPI fallback.

Production on Vercel uses ``Dockerfile.vercel``
(``uvicorn vivecaribe.main:app``).
"""

from vivecaribe.main import app

__all__ = ["app"]
