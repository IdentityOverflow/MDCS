"""
Database connection management for Project 2501.
Handles SQLAlchemy engine creation, connection pooling, and health checks.
"""

import logging
from typing import Optional
from contextlib import asynccontextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker, Session

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and operations."""
    
    def __init__(self):
        self.engine: Optional[Engine] = None
        self.SessionLocal: Optional[sessionmaker] = None
        self._settings = get_settings()
    
    def create_engine(self) -> Engine:
        """Create SQLAlchemy engine with connection pooling."""
        database_url = self._settings.get_database_url()
        
        try:
            engine = create_engine(
                database_url,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,  # Validate connections before use
                pool_recycle=300,    # Recycle connections every 5 minutes
                echo=self._settings.debug  # Log SQL statements in debug mode
            )
            
            logger.info("Database engine created successfully")
            return engine
            
        except Exception as e:
            logger.error(f"Failed to create database engine: {e}")
            raise
    
    def initialize(self) -> None:
        """Initialize database engine and session factory."""
        if self.engine is None:
            self.engine = self.create_engine()
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            logger.info("Database manager initialized")
    
    def get_session(self) -> Session:
        """Get a database session."""
        if self.SessionLocal is None:
            self.initialize()
        
        return self.SessionLocal()
    
    @asynccontextmanager
    async def get_session_context(self):
        """Get a database session as an async context manager."""
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    async def test_connection(self) -> dict:
        """
        Test database connection and return status information.
        
        Returns:
            dict: Connection status and database information
        """
        try:
            if self.engine is None:
                self.initialize()
            
            with self.engine.connect() as connection:
                # Test basic connectivity
                result = connection.execute(text("SELECT 1 as test"))
                test_value = result.scalar()
                
                if test_value != 1:
                    raise Exception("Basic connection test failed")
                
                # Get database information
                db_version_result = connection.execute(text("SELECT version()"))
                db_version = db_version_result.scalar()
                
                # Get current database name
                db_name_result = connection.execute(text("SELECT current_database()"))
                current_db = db_name_result.scalar()
                
                logger.info("Database connection test successful")
                
                return {
                    "status": "success",
                    "message": "Database connection successful",
                    "database": current_db,
                    "version": db_version,
                    "host": self._settings.db_host,
                    "port": self._settings.db_port
                }
                
        except SQLAlchemyError as e:
            logger.error(f"Database connection test failed: {e}")
            return {
                "status": "error", 
                "message": f"Database connection failed: {str(e)}",
                "error_type": "database_error"
            }
        except Exception as e:
            logger.error(f"Unexpected error during connection test: {e}")
            return {
                "status": "error",
                "message": f"Unexpected error: {str(e)}",
                "error_type": "unknown_error"
            }
    
    def close(self) -> None:
        """Close database engine and cleanup resources."""
        if self.engine:
            self.engine.dispose()
            self.engine = None
            self.SessionLocal = None
            logger.info("Database engine closed")


# Global database manager instance
db_manager = DatabaseManager()


def get_db_manager() -> DatabaseManager:
    """Get the global database manager instance."""
    return db_manager


def get_db() -> Session:
    """Dependency function to get database session for FastAPI."""
    session = db_manager.get_session()
    try:
        yield session
    finally:
        session.close()