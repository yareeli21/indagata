"""Health checks — liveness y readiness."""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text

logger = logging.getLogger("metadata-service")
router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "metadata-service", "version": "2.0.0"}


@router.get("/health/ready")
def readiness_check() -> dict:
    """200 solo si la base de datos responde."""
    from shared.db.session import SessionLocal

    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        logger.error("Base de datos no disponible: %s", exc)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Base de datos no disponible.") from exc
    finally:
        db.close()
    return {"ready": True, "service": "metadata-service", "checks": {"database": "ok"}}
