"""
FastAPI application entry point for Project 2501 backend.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.database.connection import get_db_manager
from app.models import Base
from app.api.database import router as database_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown operations.
    """
    # Startup
    logger.info("Starting Project 2501 backend")
    
    settings = get_settings()
    logger.info(f"Application: {settings.app_name}")
    logger.info(f"Debug mode: {settings.debug}")
    
    # Initialize database
    db_manager = get_db_manager()
    try:
        db_manager.initialize()
        logger.info("Database manager initialized")
        
        # Test database connection
        connection_result = await db_manager.test_connection()
        if connection_result["status"] == "success":
            logger.info(f"Database connection successful: {connection_result['database']}")
        else:
            logger.error(f"Database connection failed: {connection_result['message']}")
        
        # Create tables if they don't exist
        Base.metadata.create_all(bind=db_manager.engine)
        logger.info("Database tables created/verified")
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Project 2501 backend")
    db_manager.close()
    logger.info("Database manager closed")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()
    
    app = FastAPI(
        title="Project 2501 Backend API",
        description="Cognitive Systems Framework Backend",
        version="0.1.0",
        debug=settings.debug,
        lifespan=lifespan
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:5173"],  # Vue dev server
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(database_router, prefix="/api", tags=["database"])
    
    return app


# Create the application instance
app = create_app()


@app.get("/")
async def root():
    """Root endpoint."""
    settings = get_settings()
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": "0.1.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "project2501-backend"}


if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="info"
    )