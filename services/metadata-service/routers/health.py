"""Health check endpoints - Liveness & Readiness probes"""

from fastapi import APIRouter, HTTPException, status
import logging
from shared.db import SessionLocal

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])

@router.get("/health")
async def health_check():
    """
    Liveness Probe
    Returns 200 if service is running
    Docker/Kubernetes use this to verify container is alive
    """
    return {
        "status": "ok",
        "service": "metadata-service",
        "version": "1.0.0"
    }

@router.get("/health/ready")
async def readiness_check():
    """
    Readiness probe - ¿El servicio está listo para recibir requests?
    
    Verifica conexión a la base de datos
    """
    try:
        # Verifica conexión a la base de datos
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        
        return {
            "ready": True,
            "service": "storage_service",
            "checks": {
                "database": "ok"
            }
        }
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connectin failed!"
        )

@router.get("/health/live")
async def liveness():
    """Alternative liveness probe endpoint"""
    return {"status": "alive"}
