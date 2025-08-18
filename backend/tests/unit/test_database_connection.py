"""
Tests for database connection management.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.exc import SQLAlchemyError

from app.database.connection import DatabaseManager, get_db_manager
from app.core.config import Settings


class TestDatabaseManager:
    """Test the DatabaseManager class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.db_manager = DatabaseManager()
    
    @patch('app.database.connection.create_engine')
    def test_create_engine_success(self, mock_create_engine):
        """Test successful engine creation."""
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine
        
        engine = self.db_manager.create_engine()
        
        assert engine == mock_engine
        mock_create_engine.assert_called_once()
        
        # Verify engine configuration
        call_args = mock_create_engine.call_args
        assert call_args[1]['pool_size'] == 10
        assert call_args[1]['max_overflow'] == 20
        assert call_args[1]['pool_pre_ping'] is True
        assert call_args[1]['pool_recycle'] == 300
    
    @patch('app.database.connection.create_engine')
    def test_create_engine_failure(self, mock_create_engine):
        """Test engine creation failure."""
        mock_create_engine.side_effect = Exception("Connection failed")
        
        with pytest.raises(Exception, match="Connection failed"):
            self.db_manager.create_engine()
    
    @patch.object(DatabaseManager, 'create_engine')
    @patch('app.database.connection.sessionmaker')
    def test_initialize(self, mock_sessionmaker, mock_create_engine):
        """Test database manager initialization."""
        mock_engine = Mock()
        mock_session_factory = Mock()
        
        mock_create_engine.return_value = mock_engine
        mock_sessionmaker.return_value = mock_session_factory
        
        self.db_manager.initialize()
        
        assert self.db_manager.engine == mock_engine
        assert self.db_manager.SessionLocal == mock_session_factory
        mock_sessionmaker.assert_called_once_with(
            autocommit=False, autoflush=False, bind=mock_engine
        )
    
    def test_get_session_initializes_if_needed(self):
        """Test that get_session initializes the manager if needed."""
        with patch.object(self.db_manager, 'initialize') as mock_initialize:
            with patch.object(self.db_manager, 'SessionLocal', None):
                mock_session_factory = Mock()
                mock_session = Mock()
                mock_session_factory.return_value = mock_session
                
                # After initialize is called, set SessionLocal
                def side_effect():
                    self.db_manager.SessionLocal = mock_session_factory
                
                mock_initialize.side_effect = side_effect
                
                session = self.db_manager.get_session()
                
                mock_initialize.assert_called_once()
                assert session == mock_session
    
    @pytest.mark.asyncio
    async def test_get_session_context_success(self):
        """Test successful session context manager."""
        mock_session = Mock()
        
        with patch.object(self.db_manager, 'get_session', return_value=mock_session):
            async with self.db_manager.get_session_context() as session:
                assert session == mock_session
            
            mock_session.commit.assert_called_once()
            mock_session.close.assert_called_once()
            mock_session.rollback.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_get_session_context_error(self):
        """Test session context manager with error."""
        mock_session = Mock()
        
        with patch.object(self.db_manager, 'get_session', return_value=mock_session):
            with pytest.raises(Exception, match="Test error"):
                async with self.db_manager.get_session_context() as session:
                    raise Exception("Test error")
            
            mock_session.rollback.assert_called_once()
            mock_session.close.assert_called_once()
            mock_session.commit.assert_not_called()
    
    
    
    @pytest.mark.asyncio
    async def test_test_connection_sqlalchemy_error(self):
        """Test connection test with SQLAlchemy error."""
        mock_engine = Mock()
        mock_engine.connect.side_effect = SQLAlchemyError("Database error")
        
        self.db_manager.engine = mock_engine
        
        result = await self.db_manager.test_connection()
        
        assert result["status"] == "error"
        assert "Database connection failed" in result["message"]
        assert result["error_type"] == "database_error"
    
    @pytest.mark.asyncio
    async def test_test_connection_unexpected_error(self):
        """Test connection test with unexpected error."""
        mock_engine = Mock()
        mock_engine.connect.side_effect = Exception("Unexpected error")
        
        self.db_manager.engine = mock_engine
        
        result = await self.db_manager.test_connection()
        
        assert result["status"] == "error"
        assert "Unexpected error" in result["message"]
        assert result["error_type"] == "unknown_error"
    
    
    def test_close(self):
        """Test database manager cleanup."""
        mock_engine = Mock()
        self.db_manager.engine = mock_engine
        self.db_manager.SessionLocal = Mock()
        
        self.db_manager.close()
        
        mock_engine.dispose.assert_called_once()
        assert self.db_manager.engine is None
        assert self.db_manager.SessionLocal is None


class TestGlobalFunctions:
    """Test global helper functions."""
    
    def test_get_db_manager(self):
        """Test get_db_manager returns DatabaseManager instance."""
        manager = get_db_manager()
        assert isinstance(manager, DatabaseManager)