from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness check: if this answers, the app is running."""
    settings = get_settings()
    return {"status": "ok", "app": settings.app_name, "environment": settings.environment}
