"""Health check endpoints"""

from fastapi import APIRouter
import os

router = APIRouter(tags=["Health"])

@router.get("/health")
async def health():
    """Service health check"""
    return {
        "status": "ok",
        "service": "api-gateway",
        "version": "1.0.0"
    }

@router.get("/health/ready")
async def readiness():
    """Kubernetes readiness probe"""
    return {
        "ready": True,
        "service": "api-gateway"
    }
