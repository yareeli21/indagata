"""
Metadata Service - FastAPI Entry Point
Port: 8003
Responsibility: Dublin Core metadata registration, enrichment, and retrieval
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import os
import sys

# Add shared to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

SERVICE_NAME = "metadata-service"
PORT = 8003

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events"""
    logger.info(f"🚀 {SERVICE_NAME} starting on port {PORT}...")
    try:
        # Initialize database if needed
        from db.database import init_db
        init_db()
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")
    
    yield
    
    logger.info(f"🛑 {SERVICE_NAME} shutting down...")

app = FastAPI(
    title=f"Indagata {SERVICE_NAME}",
    description="Manages all metadata operations for instruments (Dublin Core + Enrichment)",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include routers
try:
    from routers import health, metadata, enrichment
    
    app.include_router(health.router, tags=["health"])
    app.include_router(metadata.router, prefix="/api", tags=["metadata"])
    app.include_router(enrichment.router, prefix="/api", tags=["enrichment"])
    
    logger.info("✅ All routers registered")
except ImportError as e:
    logger.error(f"❌ Failed to import routers: {e}")

if __name__ == "__main__":
    import uvicorn
    debug_mode = os.getenv("DEBUG", "false").lower() == "true"
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=PORT,
        reload=debug_mode,
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )
