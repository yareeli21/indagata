"""
Storage Service - Main FastAPI Application Entry Point

Responsabilidades:
- Store raw documents metadata in database
- Retrieve documents
- Manage file storage paths
- Provide document CRUD endpoints
"""

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Annotated
import logging
from contextlib import asynccontextmanager

# Local imports
from db import init_db, get_db, engine
from routers import documents, health
from sqlalchemy.orm import Session

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════
# LIFESPAN (Startup/Shutdown Events)
# ═══════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events"""
    # Startup
    logger.info(" Storage Service starting...")
    init_db()
    logger.info(" Database initialized")
    yield
    # Shutdown
    logger.info(" Storage Service shutting down...")
    engine.dispose()

# ═══════════════════════════════════════════════════════════
# FastAPI App Creation
# ═══════════════════════════════════════════════════════════

app = FastAPI(
    title="Indagata Storage Service",
    description="Manages raw document storage and retrieval",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ═══════════════════════════════════════════════════════════
# Register Routers
# ═══════════════════════════════════════════════════════════

# Health check router
app.include_router(health.router, tags=["health"])

# Documents CRUD router
app.include_router(documents.router, prefix="/api", tags=["documents"])

# ═══════════════════════════════════════════════════════════
# Root Endpoint
# ═══════════════════════════════════════════════════════════

@app.get("/")
def root():
    """Service root endpoint"""
    return {
        "service": "storage-service",
        "version": "1.0.0",
        "docs": "/docs"
    }
