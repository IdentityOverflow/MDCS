"""
Integration tests for the chat API endpoints.
"""

import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, Mock

from app.main import app
from app.api.chat_models import ChatProvider


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def ollama_chat_request():
    """Sample chat request for Ollama provider."""
    return {
        "message": "Hello, world!",
        "provider": "ollama",
        "stream": False,
        "chat_controls": {
            "temperature": 0.7,
            "max_tokens": 100
        },
        "provider_settings": {
            "host": "http://localhost:11434",
            "model": "llama3:8b",
            "route": "/api/chat"
        }
    }


@pytest.fixture
def openai_chat_request():
    """Sample chat request for OpenAI provider."""
    return {
        "message": "Hello, world!",
        "provider": "openai",
        "stream": False,
        "chat_controls": {
            "temperature": 0.8,
            "max_tokens": 150,
            "system_or_instructions": "You are a helpful assistant."
        },
        "provider_settings": {
            "base_url": "https://api.openai.com/v1",
            "api_key": "sk-test-key",
            "default_model": "gpt-4"
        }
    }


@pytest.fixture
def ollama_provider_settings():
    """Ollama provider settings."""
    return {
        "host": "http://localhost:11434",
        "model": "llama3:8b",
        "route": "/api/chat"
    }


@pytest.fixture
def openai_provider_settings():
    """OpenAI provider settings."""
    return {
        "base_url": "https://api.openai.com/v1",
        "api_key": "sk-test-key",
        "default_model": "gpt-4"
    }


class TestChatSendEndpoint:
    """Test the chat send endpoint."""
    
    def test_chat_send_endpoint_exists(self, client):
        """Test that the chat send endpoint exists."""
        response = client.post("/api/chat/send", json={
            "message": "test",
            "provider": "ollama",
            "stream": False
        })
        
        # Should not return 404 (endpoint should exist)
        assert response.status_code != 404
    
    def test_chat_send_missing_provider_settings(self, client):
        """Test chat send with missing provider settings."""
        request_without_settings = {
            "message": "Hello, world!",
            "provider": "ollama",
            "stream": False,
            "chat_controls": {
                "temperature": 0.7,
                "max_tokens": 100
            }
            # No provider_settings field
        }
        
        response = client.post("/api/chat/send", json=request_without_settings)
        
        assert response.status_code == 400
        error_data = response.json()
        assert error_data["detail"]["error_type"] == "configuration_error"
        assert "provider settings not found" in error_data["detail"]["message"].lower()
    
    @patch('app.services.ai_providers.ProviderFactory.create_provider')
    def test_chat_send_ollama_success(self, mock_factory, client, ollama_chat_request):
        """Test successful chat send with Ollama provider."""
        # Mock provider response
        from app.services.ai_providers import StreamingChatResponse, ProviderType
        
        # Create mock streaming responses
        async def mock_stream():
            yield StreamingChatResponse(
                content="Hello! How can I help you?",
                done=True,
                model="llama3:8b",
                provider_type=ProviderType.OLLAMA,
                metadata={"eval_count": 15}
            )
        
        mock_provider = AsyncMock()
        mock_provider.send_message_stream_with_session = Mock(return_value=mock_stream())
        mock_provider.send_message_stream = Mock(return_value=mock_stream())
        mock_provider.set_session_id = Mock()
        mock_factory.return_value = mock_provider
        
        response = client.post("/api/chat/send", json=ollama_chat_request)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["content"] == "Hello! How can I help you?"
        assert data["metadata"]["model"] == "llama3:8b"
        assert data["metadata"]["provider"] == "ollama"
        assert data["metadata"]["tokens_used"] == 15
    
    @patch('app.services.ai_providers.ProviderFactory.create_provider')
    def test_chat_send_openai_success(self, mock_factory, client, openai_chat_request):
        """Test successful chat send with OpenAI provider."""
        from app.services.ai_providers import StreamingChatResponse, ProviderType
        
        # Create mock streaming responses
        async def mock_stream():
            yield StreamingChatResponse(
                content="Hello! How can I help you today?",
                done=True,
                model="gpt-4",
                provider_type=ProviderType.OPENAI,
                metadata={
                    "usage": {"total_tokens": 25},
                    "finish_reason": "stop"
                }
            )
        
        mock_provider = AsyncMock()
        mock_provider.send_message_stream_with_session = Mock(return_value=mock_stream())
        mock_provider.send_message_stream = Mock(return_value=mock_stream())
        mock_provider.set_session_id = Mock()
        mock_factory.return_value = mock_provider
        
        response = client.post("/api/chat/send", json=openai_chat_request)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["content"] == "Hello! How can I help you today?"
        assert data["metadata"]["model"] == "gpt-4"
        assert data["metadata"]["provider"] == "openai"
        assert data["metadata"]["tokens_used"] == 25
        assert data["metadata"]["finish_reason"] == "stop"
    
    def test_chat_send_validation_empty_message(self, client):
        """Test validation for empty message."""
        response = client.post("/api/chat/send", json={
            "message": "",
            "provider": "ollama",
            "stream": False
        })
        
        assert response.status_code == 422
        error_data = response.json()
        # Pydantic validation error format
        assert "detail" in error_data
    
    def test_chat_send_validation_invalid_provider(self, client):
        """Test validation for invalid provider."""
        response = client.post("/api/chat/send", json={
            "message": "Hello",
            "provider": "invalid_provider",
            "stream": False
        })
        
        assert response.status_code == 422
    
    @patch('app.services.ai_providers.ProviderFactory.create_provider')
    def test_chat_send_provider_connection_error(self, mock_factory, client, ollama_chat_request):
        """Test handling of provider connection errors."""
        from app.services.exceptions import ProviderConnectionError
        
        mock_provider = AsyncMock()
        mock_provider.send_message.side_effect = ProviderConnectionError("Failed to connect to Ollama")
        mock_factory.return_value = mock_provider
        
        response = client.post("/api/chat/send", json=ollama_chat_request)
        
        assert response.status_code == 500
        error_data = response.json()
        assert error_data["detail"]["error_type"] == "provider_connection_error"
        assert "Failed to connect to Ollama" in error_data["detail"]["message"]
    
    @patch('app.services.ai_providers.ProviderFactory.create_provider')
    def test_chat_send_provider_authentication_error(self, mock_factory, client, openai_chat_request):
        """Test handling of provider authentication errors."""
        from app.services.exceptions import ProviderAuthenticationError
        
        mock_provider = AsyncMock()
        mock_provider.send_message.side_effect = ProviderAuthenticationError("Invalid API key")
        mock_factory.return_value = mock_provider
        
        response = client.post("/api/chat/send", json=openai_chat_request)
        
        assert response.status_code == 401
        error_data = response.json()
        assert error_data["detail"]["error_type"] == "provider_authentication_error"
        assert "Invalid API key" in error_data["detail"]["message"]


class TestChatStreamEndpoint:
    """Test the chat streaming endpoint."""
    
    def test_chat_stream_endpoint_exists(self, client):
        """Test that the chat stream endpoint exists."""
        response = client.post("/api/chat/stream", json={
            "message": "test",
            "provider": "ollama",
            "stream": True
        })
        
        # Should not return 404 (endpoint should exist)
        assert response.status_code != 404
    
    @patch('app.services.ai_providers.ProviderFactory.create_provider')
    def test_chat_stream_ollama_success(self, mock_factory, client):
        """Test successful streaming chat with Ollama."""
        from app.services.ai_providers import StreamingChatResponse, ProviderType
        
        # Mock streaming response  
        mock_responses = [
            StreamingChatResponse(
                content="Hello",
                done=False,
                model="llama3:8b",
                provider_type=ProviderType.OLLAMA
            ),
            StreamingChatResponse(
                content=" there!",
                done=False,
                model="llama3:8b",
                provider_type=ProviderType.OLLAMA
            ),
            StreamingChatResponse(
                content="",
                done=True,
                model="llama3:8b",
                provider_type=ProviderType.OLLAMA,
                metadata={"eval_count": 10}
            )
        ]
        
        # Create async iterator manually
        class MockAsyncIterator:
            def __init__(self, responses):
                self.responses = responses
                self.index = 0
                
            def __aiter__(self):
                return self
                
            async def __anext__(self):
                if self.index >= len(self.responses):
                    raise StopAsyncIteration
                response = self.responses[self.index]
                self.index += 1
                return response
        
        from unittest.mock import Mock
        
        mock_provider = Mock()
        mock_provider.send_message_stream_with_session = Mock(return_value=MockAsyncIterator(mock_responses))
        mock_provider.send_message_stream = Mock(return_value=MockAsyncIterator(mock_responses))
        mock_provider.set_session_id = Mock()
        mock_factory.return_value = mock_provider
        
        response = client.post("/api/chat/stream", json={
            "message": "Hello",
            "provider": "ollama",
            "stream": True,
            "provider_settings": {
                "host": "http://localhost:11434",
                "model": "llama3:8b",
                "route": "/api/chat"
            }
        })
        
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        
        # Parse Server-Sent Events
        content = response.text
        assert "data: " in content
        assert "Hello" in content
        assert " there!" in content
    
    def test_chat_stream_validation_non_streaming_request(self, client):
        """Test that stream endpoint validates stream=True."""
        response = client.post("/api/chat/stream", json={
            "message": "Hello",
            "provider": "ollama",
            "stream": False  # Should be True for stream endpoint
        })
        
        assert response.status_code == 400
        error_data = response.json()
        assert error_data["detail"]["error_type"] == "validation_error"
        assert "stream must be true" in error_data["detail"]["message"].lower()


class TestChatControlsIntegration:
    """Test integration of chat controls with providers."""
    
    @patch('app.services.ai_providers.ProviderFactory.create_provider')
    def test_chat_controls_passed_to_provider(self, mock_factory, client):
        """Test that chat controls are properly passed to the provider."""
        from app.services.ai_providers import ChatResponse, ProviderType
        
        mock_response = ChatResponse(
            content="Response",
            model="llama3:8b",
            provider_type=ProviderType.OLLAMA
        )
        
        mock_provider = AsyncMock()
        mock_provider.send_message.return_value = mock_response
        mock_factory.return_value = mock_provider
        
        chat_request = {
            "message": "Test message",
            "provider": "ollama",
            "stream": False,
            "chat_controls": {
                "temperature": 0.9,
                "max_tokens": 256,
                "ollama_top_k": 50,
                "seed": 42
            },
            "provider_settings": {
                "host": "http://localhost:11434",
                "model": "llama3:8b",
                "route": "/api/chat"
            }
        }
        
        response = client.post("/api/chat/send", json=chat_request)
        
        assert response.status_code == 200
        
        # Verify provider was called with correct parameters
        mock_provider.send_message.assert_called_once()
        call_args = mock_provider.send_message.call_args[0][0]  # First argument (ChatRequest)
        
        assert call_args.message == "Test message"
        assert call_args.chat_controls["temperature"] == 0.9
        assert call_args.chat_controls["max_tokens"] == 256
        assert call_args.chat_controls["ollama_top_k"] == 50
        assert call_args.chat_controls["seed"] == 42
        assert call_args.chat_controls["stream"] is False


class TestProviderSettingsIntegration:
    """Test integration with provider settings."""
    
    def test_provider_settings_from_request(self, client):
        """Test that provider settings are extracted from request correctly."""
        # Test that missing provider settings returns error
        response = client.post("/api/chat/send", json={
            "message": "test",
            "provider": "ollama",
            "stream": False
            # No provider_settings
        })
        
        assert response.status_code == 400
        error_data = response.json()
        assert error_data["detail"]["error_type"] == "configuration_error"
    
    def test_different_providers_use_their_settings(self, client):
        """Test that different providers use their respective settings in the request."""
        with patch('app.services.ai_providers.ProviderFactory.create_provider') as mock_factory:
            from app.services.ai_providers import ChatResponse, ProviderType
            
            mock_response = ChatResponse(content="test", model="test", provider_type=ProviderType.OLLAMA)
            mock_provider = AsyncMock()
            mock_provider.send_message.return_value = mock_response
            mock_factory.return_value = mock_provider
            
            # Test Ollama
            response = client.post("/api/chat/send", json={
                "message": "test",
                "provider": "ollama",
                "stream": False,
                "provider_settings": {
                    "host": "http://localhost:11434",
                    "model": "llama3:8b"
                }
            })
            
            assert response.status_code == 200
            
            # Verify the provider was called with Ollama settings
            call_args = mock_provider.send_message.call_args[0][0]
            assert call_args.provider_settings["host"] == "http://localhost:11434"
            assert call_args.provider_settings["model"] == "llama3:8b"