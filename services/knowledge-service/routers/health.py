"""Router — health check del knowledge-service."""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health", summary="Health check del servicio")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "knowledge-service"}
