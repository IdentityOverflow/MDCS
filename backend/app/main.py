"""
FastAPI application entry point for Project 2501 backend.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.database.connection import get_db_manager
from app.models import Base
from app.api.database import router as database_router
from app.api.modules import router as modules_router
from app.api.personas import router as personas_router
from app.api.chat import router as chat_router
from app.api.websocket_chat import router as websocket_router
from app.api.connections import router as connections_router
from app.api.conversations import router as conversations_router
from app.api.messages import router as messages_router
from app.api.templates import router as templates_router
from app.core.script_plugins import plugin_registry

# Configure logging
logging.basicConfig(level=logging.WARNING)
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
        
        # Load advanced module plugins
        plugin_registry.load_all_plugins()
        plugin_count = len(plugin_registry.get_registered_functions())
        logger.info(f"Advanced module plugins loaded: {plugin_count} functions available")
        
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
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:5173",  # Vue dev server (npm run dev)
            "http://localhost:4173"   # Vue preview server (npm run preview)
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Session-ID"],  # Expose custom session header to frontend
    )
    
    # Include routers
    app.include_router(database_router, prefix="/api", tags=["database"])
    app.include_router(modules_router, prefix="/api", tags=["modules"])
    app.include_router(personas_router, prefix="/api", tags=["personas"])
    app.include_router(conversations_router, tags=["conversations"])
    app.include_router(messages_router, tags=["messages"])
    app.include_router(chat_router, tags=["chat"])
    app.include_router(websocket_router, tags=["websocket"])  # WebSocket chat endpoint
    app.include_router(connections_router, tags=["connections"])
    app.include_router(templates_router, tags=["templates"])
    
    # Mount static files for serving images
    static_dir = Path(__file__).parent.parent / "static"
    static_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    
    # Add main routes
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
    
    return app


# Create the application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="warning"
    )