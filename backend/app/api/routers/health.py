"""Health check router (example capability module)."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Basic health check for load balancers and CI."""
    return {"status": "ok"}
