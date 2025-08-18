"""
Tests for database API endpoints.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


class TestDatabaseTestEndpoint:
    """Test the database test connection endpoint."""
    
    @patch('app.api.database.get_db_manager')
    def test_database_test_success(self, mock_get_db_manager, client):
        """Test successful database connection test."""
        # Mock successful database connection
        mock_db_manager = Mock()
        mock_db_manager.test_connection = AsyncMock(return_value={
            "status": "success",
            "message": "Database connection successful",
            "database": "project2501",
            "version": "PostgreSQL 14.0",
            "host": "localhost",
            "port": 5432
        })
        mock_get_db_manager.return_value = mock_db_manager
        
        response = client.get("/api/database/test")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert data["message"] == "Database connection successful"
        assert data["database"] == "project2501"
        assert data["version"] == "PostgreSQL 14.0"
        assert data["host"] == "localhost"
        assert data["port"] == 5432
        assert data["error_type"] is None
    
    @patch('app.api.database.get_db_manager')
    def test_database_test_connection_failure(self, mock_get_db_manager, client):
        """Test database connection failure."""
        # Mock failed database connection
        mock_db_manager = Mock()
        mock_db_manager.test_connection = AsyncMock(return_value={
            "status": "error",
            "message": "Database connection failed: Connection refused",
            "error_type": "database_error"
        })
        mock_get_db_manager.return_value = mock_db_manager
        
        response = client.get("/api/database/test")
        
        # Should return 200 OK with error details (not raise HTTP exception)
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "error"
        assert "Connection refused" in data["message"]
        assert data["error_type"] == "database_error"
        assert data["database"] is None
        assert data["version"] is None
    
    @patch('app.api.database.get_db_manager')
    def test_database_test_unexpected_error(self, mock_get_db_manager, client):
        """Test unexpected error during database test."""
        # Mock unexpected exception
        mock_db_manager = Mock()
        mock_db_manager.test_connection = AsyncMock(side_effect=Exception("Unexpected error"))
        mock_get_db_manager.return_value = mock_db_manager
        
        response = client.get("/api/database/test")
        
        # Should return 200 OK with error details (not raise HTTP exception)
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "error"
        assert "Unexpected error" in data["message"]
        assert data["error_type"] == "server_error"


class TestDatabaseInfoEndpoint:
    """Test the database info endpoint."""
    
    @patch('app.api.database.get_db_manager')
    def test_database_info_success(self, mock_get_db_manager, client):
        """Test successful database info retrieval."""
        # Mock successful database connection
        mock_db_manager = Mock()
        mock_db_manager.test_connection = AsyncMock(return_value={
            "status": "success",
            "message": "Database connection successful",
            "database": "project2501",
            "version": "PostgreSQL 14.0",
            "host": "localhost",
            "port": 5432
        })
        mock_get_db_manager.return_value = mock_db_manager
        
        with patch('app.models.Base') as mock_base:
            mock_base.metadata.tables.keys.return_value = ["conversations", "messages", "personas"]
            
            response = client.get("/api/database/info")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "connected"
        assert data["database"] == "project2501"
        assert data["version"] == "PostgreSQL 14.0"
        assert data["host"] == "localhost"
        assert data["port"] == 5432
        assert data["tables"] == ["conversations", "messages", "personas"]
    
    @patch('app.api.database.get_db_manager')
    def test_database_info_connection_failure(self, mock_get_db_manager, client):
        """Test database info when connection fails."""
        # Mock failed database connection
        mock_db_manager = Mock()
        mock_db_manager.test_connection = AsyncMock(return_value={
            "status": "error",
            "message": "Connection refused",
            "error_type": "database_error"
        })
        mock_get_db_manager.return_value = mock_db_manager
        
        response = client.get("/api/database/info")
        
        assert response.status_code == 503
        data = response.json()
        assert "Connection refused" in data["detail"]
    
    @patch('app.api.database.get_db_manager')
    def test_database_info_table_error(self, mock_get_db_manager, client):
        """Test database info when table information fails."""
        # Mock successful connection but failing table info
        mock_db_manager = Mock()
        mock_db_manager.test_connection = AsyncMock(return_value={
            "status": "success",
            "message": "Database connection successful",
            "database": "project2501",
            "version": "PostgreSQL 14.0",
            "host": "localhost",
            "port": 5432
        })
        mock_get_db_manager.return_value = mock_db_manager
        
        with patch('app.models.Base') as mock_base:
            mock_base.metadata.tables.keys.side_effect = Exception("Table access error")
            
            response = client.get("/api/database/info")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "connected"
        assert data["tables"] == []  # Should be empty list when table info fails
    
    @patch('app.api.database.get_db_manager')
    def test_database_info_unexpected_error(self, mock_get_db_manager, client):
        """Test database info with unexpected error."""
        # Mock unexpected exception
        mock_db_manager = Mock()
        mock_db_manager.test_connection = AsyncMock(side_effect=Exception("Unexpected error"))
        mock_get_db_manager.return_value = mock_db_manager
        
        response = client.get("/api/database/info")
        
        assert response.status_code == 500
        data = response.json()
        assert "Unexpected error" in data["detail"]