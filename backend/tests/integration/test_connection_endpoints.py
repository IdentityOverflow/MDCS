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


# Models endpoint tests
class TestModelsEndpoints:
    """Test cases for provider models listing endpoints."""
    
    @patch('app.services.ollama_service.OllamaService.list_models')
    def test_ollama_models_success(self, mock_list_models, client):
        """Test successful Ollama models listing."""
        mock_models = [
            {"id": "llama3:8b", "name": "llama3:8b", "object": "model", "created": 1234567890, "owned_by": "ollama"},
            {"id": "mistral:7b", "name": "mistral:7b", "object": "model", "created": 1234567891, "owned_by": "ollama"}
        ]
        mock_list_models.return_value = mock_models
        
        request_data = {"host": "http://localhost:11434"}
        response = client.post("/api/connections/ollama/models", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["object"] == "list"
        assert len(data["data"]) == 2
        assert data["data"][0]["id"] == "llama3:8b"
        assert data["data"][1]["id"] == "mistral:7b"
        
        mock_list_models.assert_called_once_with({"host": "http://localhost:11434"})
    
    @patch('app.services.openai_service.OpenAIService.list_models')
    def test_openai_models_success(self, mock_list_models, client):
        """Test successful OpenAI models listing."""
        mock_models = [
            {"id": "gpt-4o", "name": "gpt-4o", "object": "model", "created": 1234567890, "owned_by": "openai"},
            {"id": "gpt-3.5-turbo", "name": "gpt-3.5-turbo", "object": "model", "created": 1234567891, "owned_by": "openai"}
        ]
        mock_list_models.return_value = mock_models
        
        request_data = {
            "base_url": "https://api.openai.com/v1",
            "api_key": "sk-test-key",
            "organization": "",
            "project": ""
        }
        response = client.post("/api/connections/openai/models", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["object"] == "list"
        assert len(data["data"]) == 2
        assert data["data"][0]["id"] == "gpt-4o"
        assert data["data"][1]["id"] == "gpt-3.5-turbo"
        
        mock_list_models.assert_called_once()
    
    def test_unsupported_provider_models(self, client):
        """Test models endpoint with unsupported provider."""
        request_data = {"host": "http://localhost:11434"}
        response = client.post("/api/connections/invalid/models", json=request_data)
        
        assert response.status_code == 400
        assert response.json()["detail"]["error_type"] == "validation_error"
        assert "Unsupported provider: invalid" in response.json()["detail"]["message"]
    
    @patch('app.services.ollama_service.OllamaService.list_models')
    def test_ollama_models_connection_error(self, mock_list_models, client):
        """Test Ollama models listing with connection error."""
        from app.services.exceptions import ProviderConnectionError
        mock_list_models.side_effect = ProviderConnectionError("Failed to connect to Ollama")
        
        request_data = {"host": "http://invalid-host:11434"}
        response = client.post("/api/connections/ollama/models", json=request_data)
        
        assert response.status_code == 500
        assert response.json()["detail"]["error_type"] == "connection_error"
        assert "Failed to connect to Ollama" in response.json()["detail"]["message"]
    
    @patch('app.services.openai_service.OpenAIService.list_models')
    def test_openai_models_authentication_error(self, mock_list_models, client):
        """Test OpenAI models listing with authentication error."""
        from app.services.exceptions import ProviderAuthenticationError
        mock_list_models.side_effect = ProviderAuthenticationError("Invalid API key")
        
        request_data = {
            "base_url": "https://api.openai.com/v1",
            "api_key": "invalid-key",
            "organization": "",
            "project": ""
        }
        response = client.post("/api/connections/openai/models", json=request_data)
        
        assert response.status_code == 500  # Connection errors are mapped to 500
        assert response.json()["detail"]["error_type"] == "connection_error"
        assert "Invalid API key" in response.json()["detail"]["message"]
    
    @patch('app.services.openai_service.OpenAIService.list_models')
    def test_openai_models_unexpected_error(self, mock_list_models, client):
        """Test OpenAI models listing with unexpected error."""
        mock_list_models.side_effect = Exception("Unexpected error occurred")
        
        request_data = {
            "base_url": "https://api.openai.com/v1",
            "api_key": "sk-test-key",
            "organization": "",
            "project": ""
        }
        response = client.post("/api/connections/openai/models", json=request_data)
        
        assert response.status_code == 500
        assert response.json()["detail"]["error_type"] == "internal_error"
        assert "Unexpected error occurred" in response.json()["detail"]["message"]
    
    def test_ollama_models_empty_host(self, client):
        """Test Ollama models with empty host."""
        request_data = {"host": ""}
        response = client.post("/api/connections/ollama/models", json=request_data)
        
        # This should work fine - the service will use default host
        # But let's test it with a mock to avoid actual network calls
        with patch('app.services.ollama_service.OllamaService.list_models') as mock_list_models:
            mock_list_models.return_value = []
            response = client.post("/api/connections/ollama/models", json=request_data)
            assert response.status_code == 200
    
    def test_openai_models_missing_api_key(self, client):
        """Test OpenAI models with missing API key."""
        request_data = {
            "base_url": "https://api.openai.com/v1",
            "api_key": "",
            "organization": "",
            "project": ""
        }
        
        with patch('app.services.openai_service.OpenAIService.list_models') as mock_list_models:
            from app.services.exceptions import ProviderConnectionError
            mock_list_models.side_effect = ProviderConnectionError("Invalid OpenAI settings: missing required fields")
            
            response = client.post("/api/connections/openai/models", json=request_data)
            assert response.status_code == 500
            assert "missing required fields" in response.json()["detail"]["message"]