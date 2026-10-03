"""Health check endpoints - Liveness & Readiness probes"""

from fastapi import APIRouter, HTTPException, status
import logging

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
    Readiness Probe
    Returns 200 only if service is ready to handle requests
    Checks:
    - Database connectivity
    - Configuration loaded
    """
    try:
        # Test database connection
        from shared.db.database import SessionLocal
        
        db = SessionLocal()
        try:
            # Simple query to verify connection
            db.execute("SELECT 1")
            db.close()
        except Exception as e:
            logger.error(f"Database check failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database unavailable"
            )
        
        return {
            "ready": True,
            "service": "metadata-service",
            "checks": {
                "database": "ok"
            }
        }
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service not ready: {str(e)}"
        )

@router.get("/health/live")
async def liveness():
    """Alternative liveness probe endpoint"""
    return {"status": "alive"}
