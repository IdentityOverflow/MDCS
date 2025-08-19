"""
Integration tests for provider connection testing endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from app.main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def ollama_connection_settings():
    """Sample Ollama connection settings."""
    return {
        "host": "http://localhost:11434",
        "model": "llama3:8b",
        "route": "/api/chat",
        "timeout_ms": 30000
    }


@pytest.fixture
def openai_connection_settings():
    """Sample OpenAI connection settings."""
    return {
        "base_url": "https://api.openai.com/v1",
        "api_key": "sk-test-key-123",
        "default_model": "gpt-4",
        "organization": "org-test",
        "project": "proj-test",
        "timeout_ms": 60000
    }


class TestOllamaConnectionTest:
    """Test Ollama connection testing endpoint."""
    
    def test_ollama_connection_test_endpoint_exists(self, client):
        """Test that the Ollama connection test endpoint exists."""
        response = client.post("/api/connections/ollama/test", json={
            "host": "http://localhost:11434",
            "model": "llama3:8b"
        })
        
        # Should not return 404 (endpoint should exist)
        assert response.status_code != 404
    
    @patch('app.services.ollama_service.OllamaService.test_connection')
    def test_ollama_connection_test_success(self, mock_test, client, ollama_connection_settings):
        """Test successful Ollama connection test."""
        # Mock successful connection test
        mock_test.return_value = {
            "status": "success",
            "message": "Successfully connected to Ollama",
            "model": "llama3:8b",
            "version": "0.1.0"
        }
        
        response = client.post("/api/connections/ollama/test", json=ollama_connection_settings)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert "successfully connected" in data["message"].lower()
        assert data["model"] == "llama3:8b"
    
    @patch('app.services.ollama_service.OllamaService.test_connection')
    def test_ollama_connection_test_failure(self, mock_test, client, ollama_connection_settings):
        """Test Ollama connection test failure."""
        from app.services.exceptions import ProviderConnectionError
        
        # Mock connection failure
        mock_test.side_effect = ProviderConnectionError("Failed to connect to Ollama at localhost:11434")
        
        response = client.post("/api/connections/ollama/test", json=ollama_connection_settings)
        
        assert response.status_code == 500
        data = response.json()
        
        assert data["detail"]["status"] == "error"
        assert "failed to connect" in data["detail"]["message"].lower()
        assert "localhost:11434" in data["detail"]["message"]
    
    def test_ollama_connection_test_validation_missing_host(self, client):
        """Test validation for missing host."""
        response = client.post("/api/connections/ollama/test", json={
            "model": "llama3:8b"
        })
        
        assert response.status_code == 422  # Validation error
    
    def test_ollama_connection_test_validation_missing_model(self, client):
        """Test validation for missing model."""
        response = client.post("/api/connections/ollama/test", json={
            "host": "http://localhost:11434"
        })
        
        assert response.status_code == 422  # Validation error


class TestOpenAIConnectionTest:
    """Test OpenAI connection testing endpoint."""
    
    def test_openai_connection_test_endpoint_exists(self, client):
        """Test that the OpenAI connection test endpoint exists."""
        response = client.post("/api/connections/openai/test", json={
            "base_url": "https://api.openai.com/v1",
            "api_key": "sk-test-key",
            "default_model": "gpt-4"
        })
        
        # Should not return 404 (endpoint should exist)
        assert response.status_code != 404
    
    @patch('app.services.openai_service.OpenAIService.test_connection')
    def test_openai_connection_test_success(self, mock_test, client, openai_connection_settings):
        """Test successful OpenAI connection test."""
        # Mock successful connection test
        mock_test.return_value = {
            "status": "success",
            "message": "Successfully connected to OpenAI API",
            "model": "gpt-4",
            "organization": "org-test"
        }
        
        response = client.post("/api/connections/openai/test", json=openai_connection_settings)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success" 
        assert "successfully connected" in data["message"].lower()
        assert data["model"] == "gpt-4"
    
    @patch('app.services.openai_service.OpenAIService.test_connection')
    def test_openai_connection_test_auth_failure(self, mock_test, client, openai_connection_settings):
        """Test OpenAI connection test with authentication failure."""
        from app.services.exceptions import ProviderAuthenticationError
        
        # Mock authentication failure
        mock_test.side_effect = ProviderAuthenticationError("Invalid API key")
        
        response = client.post("/api/connections/openai/test", json=openai_connection_settings)
        
        assert response.status_code == 401
        data = response.json()
        
        assert data["detail"]["status"] == "error"
        assert "invalid api key" in data["detail"]["message"].lower()
    
    @patch('app.services.openai_service.OpenAIService.test_connection')
    def test_openai_connection_test_connection_failure(self, mock_test, client, openai_connection_settings):
        """Test OpenAI connection test with network failure."""
        from app.services.exceptions import ProviderConnectionError
        
        # Mock connection failure
        mock_test.side_effect = ProviderConnectionError("Network timeout")
        
        response = client.post("/api/connections/openai/test", json=openai_connection_settings)
        
        assert response.status_code == 500
        data = response.json()
        
        assert data["detail"]["status"] == "error"
        assert "network timeout" in data["detail"]["message"].lower()
    
    def test_openai_connection_test_validation_missing_api_key(self, client):
        """Test validation for missing API key."""
        response = client.post("/api/connections/openai/test", json={
            "base_url": "https://api.openai.com/v1",
            "default_model": "gpt-4"
        })
        
        assert response.status_code == 422  # Validation error
    
    def test_openai_connection_test_validation_missing_model(self, client):
        """Test validation for missing default model."""
        response = client.post("/api/connections/openai/test", json={
            "base_url": "https://api.openai.com/v1",
            "api_key": "sk-test-key"
        })
        
        assert response.status_code == 422  # Validation error


class TestConnectionTestIntegration:
    """Integration tests for connection testing functionality."""
    
    @patch('app.services.ollama_service.OllamaService.test_connection')
    @patch('app.services.openai_service.OpenAIService.test_connection')
    def test_both_providers_connection_test(self, mock_openai, mock_ollama, client, 
                                          ollama_connection_settings, openai_connection_settings):
        """Test that both provider connection tests work independently."""
        # Mock successful connections for both
        mock_ollama.return_value = {"status": "success", "message": "Ollama OK"}
        mock_openai.return_value = {"status": "success", "message": "OpenAI OK"}
        
        # Test Ollama
        ollama_response = client.post("/api/connections/ollama/test", json=ollama_connection_settings)
        assert ollama_response.status_code == 200
        assert ollama_response.json()["message"] == "Ollama OK"
        
        # Test OpenAI
        openai_response = client.post("/api/connections/openai/test", json=openai_connection_settings)
        assert openai_response.status_code == 200
        assert openai_response.json()["message"] == "OpenAI OK"
        
        # Verify both services were called
        mock_ollama.assert_called_once()
        mock_openai.assert_called_once()