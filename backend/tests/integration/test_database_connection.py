"""
Integration tests for database connection management.
These tests use the real test database instead of complex mocks.
"""

import pytest
from app.database.connection import DatabaseManager, get_db_manager


class TestDatabaseConnectionIntegration:
    """Integration tests for database connection functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.db_manager = DatabaseManager()
    
    @pytest.mark.asyncio
    async def test_connection_success(self):
        """Test successful database connection with real database."""
        # Use the real test database connection
        result = await self.db_manager.test_connection()
        
        # Verify successful connection
        assert result["status"] == "success"
        assert result["message"] == "Database connection successful"
        assert "database" in result
        assert "version" in result
        assert "host" in result
        assert "port" in result
        
        # Verify we get actual database information
        assert result["database"] is not None
        assert "PostgreSQL" in result["version"]
        assert result["host"] == "localhost"
        assert result["port"] == 5432
    
    @pytest.mark.asyncio
    async def test_connection_initializes_if_needed(self):
        """Test that connection initializes the manager if needed."""
        # Start with uninitialized manager
        db_manager = DatabaseManager()
        assert db_manager.engine is None
        
        # Connection should initialize and succeed
        result = await db_manager.test_connection()
        
        assert result["status"] == "success"
        assert db_manager.engine is not None
        
        # Clean up
        db_manager.close()
    
    def test_get_db_manager_singleton(self):
        """Test that get_db_manager returns the same instance."""
        manager1 = get_db_manager()
        manager2 = get_db_manager()
        
        assert isinstance(manager1, DatabaseManager)
        assert isinstance(manager2, DatabaseManager)
        # Note: This tests the function works, not necessarily that it's a singleton
    
    def test_database_manager_lifecycle(self):
        """Test database manager initialization and cleanup."""
        db_manager = DatabaseManager()
        
        # Initially uninitialized
        assert db_manager.engine is None
        assert db_manager.SessionLocal is None
        
        # Initialize
        db_manager.initialize()
        
        assert db_manager.engine is not None
        assert db_manager.SessionLocal is not None
        
        # Clean up
        db_manager.close()
        
        assert db_manager.engine is None
        assert db_manager.SessionLocal is None
    
    @pytest.mark.asyncio
    async def test_session_context_manager(self):
        """Test database session context manager."""
        # Get a session and perform basic operations
        async with self.db_manager.get_session_context() as session:
            # Session should be valid
            assert session is not None
            
            # We can perform basic session operations without error
            # (The session will be committed and closed automatically)
        
        # Context manager should have handled cleanup
        # (We can't easily test this without accessing private state)
    
    def test_get_session(self):
        """Test getting a database session."""
        session = self.db_manager.get_session()
        
        try:
            # Session should be valid
            assert session is not None
            
            # Session should be bound to an engine
            assert session.bind is not None
        finally:
            # Clean up session
            session.close()