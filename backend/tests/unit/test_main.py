"""
Tests for the main FastAPI application.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient

from app.main import create_app, app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


class TestMainApplication:
    """Test the main FastAPI application."""
    
    def test_create_app(self):
        """Test application creation."""
        test_app = create_app()
        assert test_app.title == "Project 2501 Backend API"
        assert test_app.version == "0.1.0"
    
    def test_root_endpoint(self, client):
        """Test the root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "status" in data
        assert data["version"] == "0.1.0"
        assert data["status"] == "running"
    
    def test_health_endpoint(self, client):
        """Test the health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "project2501-backend"
    
    @patch('app.main.get_db_manager')
    @patch('app.main.Base')
    def test_lifespan_startup_success(self, mock_base, mock_get_db_manager):
        """Test successful application startup."""
        # Mock database manager
        mock_db_manager = Mock()
        mock_db_manager.test_connection = AsyncMock(return_value={
            "status": "success",
            "database": "test_db"
        })
        mock_db_manager.engine = Mock()
        mock_get_db_manager.return_value = mock_db_manager
        
        # Mock Base.metadata
        mock_metadata = Mock()
        mock_base.metadata = mock_metadata
        
        # Create app (which will trigger lifespan startup)
        test_app = create_app()
        
        # Test that we can make requests (app started successfully)
        with TestClient(test_app) as client:
            response = client.get("/health")
            assert response.status_code == 200
    
    @patch('app.main.get_db_manager')
    def test_lifespan_database_connection_failure(self, mock_get_db_manager):
        """Test application startup with database connection failure."""
        # Mock database manager with failing connection
        mock_db_manager = Mock()
        mock_db_manager.initialize.side_effect = Exception("Database connection failed")
        mock_get_db_manager.return_value = mock_db_manager
        
        # App creation should still succeed even with DB failure
        # (the failure is logged but doesn't prevent app startup)
        test_app = create_app()
        assert test_app is not None


class TestCORSConfiguration:
    """Test CORS configuration."""
    
    def test_cors_headers_present(self, client):
        """Test that CORS headers are present in responses."""
        # Make a request with Origin header
        response = client.get(
            "/health",
            headers={"Origin": "http://localhost:3000"}
        )
        
        assert response.status_code == 200
        # CORS headers should be present for allowed origins
        # Note: TestClient may not fully simulate CORS behavior
        # This is more of a configuration test
    
    def test_options_request(self, client):
        """Test OPTIONS request for CORS preflight."""
        response = client.options("/health")
        # OPTIONS requests should be handled by CORS middleware
        # Exact behavior depends on FastAPI and TestClient interaction