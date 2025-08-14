"""
Database API endpoints for Project 2501.
"""

import logging
from typing import Dict, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.database.connection import get_db_manager

logger = logging.getLogger(__name__)

router = APIRouter()


class DatabaseTestResponse(BaseModel):
    """Response model for database test endpoint."""
    status: str
    message: str
    database: str = None
    version: str = None
    host: str = None
    port: int = None
    error_type: str = None


@router.get("/database/test", response_model=DatabaseTestResponse)
async def test_database_connection() -> DatabaseTestResponse:
    """
    Test database connection endpoint.
    This endpoint is called by the frontend "Test Connection" button.
    
    Returns:
        DatabaseTestResponse: Connection status and information
    """
    logger.info("Testing database connection")
    
    try:
        db_manager = get_db_manager()
        result = await db_manager.test_connection()
        
        logger.info(f"Database test result: {result['status']}")
        
        if result["status"] == "success":
            return DatabaseTestResponse(
                status=result["status"],
                message=result["message"],
                database=result["database"],
                version=result["version"],
                host=result["host"],
                port=result["port"]
            )
        else:
            # Return error response but don't raise HTTP exception
            # Let frontend handle the error display
            return DatabaseTestResponse(
                status=result["status"],
                message=result["message"],
                error_type=result.get("error_type", "unknown_error")
            )
    
    except Exception as e:
        logger.error(f"Unexpected error in database test endpoint: {e}")
        
        # Return error response instead of raising exception
        return DatabaseTestResponse(
            status="error",
            message=f"Unexpected error: {str(e)}",
            error_type="server_error"
        )


@router.get("/database/info")
async def get_database_info() -> Dict[str, Any]:
    """
    Get database information and statistics.
    
    Returns:
        dict: Database information
    """
    logger.info("Getting database information")
    
    try:
        db_manager = get_db_manager()
        
        # Test connection first
        connection_result = await db_manager.test_connection()
        
        if connection_result["status"] != "success":
            raise HTTPException(
                status_code=503,
                detail=f"Database connection failed: {connection_result['message']}"
            )
        
        # Get additional database info
        info = {
            "status": "connected",
            "database": connection_result["database"],
            "version": connection_result["version"],
            "host": connection_result["host"],
            "port": connection_result["port"],
        }
        
        # Add table information if possible
        try:
            from app.models import Base
            table_names = list(Base.metadata.tables.keys())
            info["tables"] = table_names
        except Exception as e:
            logger.warning(f"Could not get table information: {e}")
            info["tables"] = []
        
        return info
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting database info: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get database information: {str(e)}"
        )