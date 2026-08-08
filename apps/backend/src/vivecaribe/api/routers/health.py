"""Health check endpoint."""

from fastapi import APIRouter

from vivecaribe import __version__

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness probe for local Docker and future deploy checks."""
    return {"status": "ok", "version": __version__}
