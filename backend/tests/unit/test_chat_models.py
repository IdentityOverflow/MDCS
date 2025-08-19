"""
Unit tests for chat API models.
"""

import pytest
from typing import Dict, Any
from pydantic import ValidationError

from app.api.chat_models import (
    ChatSendRequest,
    ChatSendResponse,
    StreamingChatResponse,
    ChatProvider,
    ChatError,
    ChatMetadata
)
from app.services.ai_providers import ProviderType


class TestChatProvider:
    """Test ChatProvider enum and validation."""
    
    def test_chat_provider_values(self):
        """Test ChatProvider enum has correct values."""
        assert ChatProvider.OLLAMA == "ollama"
        assert ChatProvider.OPENAI == "openai"
    
    def test_chat_provider_from_string(self):
        """Test creating ChatProvider from string."""
        assert ChatProvider("ollama") == ChatProvider.OLLAMA
        assert ChatProvider("openai") == ChatProvider.OPENAI
    
    def test_chat_provider_invalid_value(self):
        """Test ChatProvider with invalid value."""
        with pytest.raises(ValueError):
            ChatProvider("invalid")


class TestChatSendRequest:
    """Test ChatSendRequest model validation."""
    
    def test_create_basic_request(self):
        """Test creating a basic chat request."""
        request = ChatSendRequest(
            message="Hello, world!",
            provider=ChatProvider.OLLAMA,
            stream=False
        )
        
        assert request.message == "Hello, world!"
        assert request.provider == ChatProvider.OLLAMA
        assert request.stream is False
        assert request.chat_controls == {}
    
    def test_create_request_with_chat_controls(self):
        """Test creating request with chat controls."""
        request = ChatSendRequest(
            message="Hello",
            provider=ChatProvider.OPENAI,
            stream=True,
            chat_controls={
                "temperature": 0.8,
                "max_tokens": 512,
                "system_or_instructions": "You are a helpful assistant."
            }
        )
        
        assert request.message == "Hello"
        assert request.provider == ChatProvider.OPENAI
        assert request.stream is True
        assert request.chat_controls["temperature"] == 0.8
        assert request.chat_controls["max_tokens"] == 512
        assert request.chat_controls["system_or_instructions"] == "You are a helpful assistant."
    
    def test_empty_message_validation(self):
        """Test that empty messages are rejected."""
        with pytest.raises(ValidationError, match="Message cannot be empty"):
            ChatSendRequest(
                message="",
                provider=ChatProvider.OLLAMA,
                stream=False
            )
    
    def test_whitespace_only_message_validation(self):
        """Test that whitespace-only messages are rejected."""
        with pytest.raises(ValidationError, match="Message cannot be empty"):
            ChatSendRequest(
                message="   ",
                provider=ChatProvider.OLLAMA,
                stream=False
            )
    
    def test_provider_conversion(self):
        """Test that string providers are converted to enum."""
        request = ChatSendRequest(
            message="Hello",
            provider="ollama",  # String instead of enum
            stream=False
        )
        
        assert request.provider == ChatProvider.OLLAMA
    
    def test_invalid_provider_validation(self):
        """Test validation of invalid provider."""
        with pytest.raises(ValidationError):
            ChatSendRequest(
                message="Hello",
                provider="invalid_provider",
                stream=False
            )
    
    def test_chat_controls_default(self):
        """Test that chat_controls defaults to empty dict."""
        request = ChatSendRequest(
            message="Hello",
            provider=ChatProvider.OLLAMA,
            stream=False
        )
        
        assert request.chat_controls == {}
    
    def test_to_provider_request(self):
        """Test conversion to provider ChatRequest."""
        request = ChatSendRequest(
            message="Hello",
            provider=ChatProvider.OLLAMA,
            stream=True,
            chat_controls={"temperature": 0.7},
            provider_settings={
                "host": "http://localhost:11434",
                "model": "llama3:8b"
            }
        )
        
        # This method should convert frontend request to provider request
        provider_request = request.to_provider_request()
        
        assert provider_request.message == "Hello"
        assert provider_request.provider_type == ProviderType.OLLAMA
        assert provider_request.chat_controls["temperature"] == 0.7
        assert provider_request.chat_controls["stream"] is True
        assert provider_request.provider_settings["host"] == "http://localhost:11434"
        assert provider_request.provider_settings["model"] == "llama3:8b"
    
    def test_to_provider_request_with_fallback(self):
        """Test conversion with fallback provider settings."""
        request = ChatSendRequest(
            message="Hello",
            provider=ChatProvider.OPENAI,
            stream=False,
            chat_controls={"temperature": 0.8}
            # No provider_settings in request
        )
        
        # Should use fallback settings
        fallback_settings = {"api_key": "test-key", "model": "gpt-4"}
        provider_request = request.to_provider_request(fallback_settings)
        
        assert provider_request.message == "Hello"
        assert provider_request.provider_type == ProviderType.OPENAI
        assert provider_request.chat_controls["temperature"] == 0.8
        assert provider_request.chat_controls["stream"] is False
        assert provider_request.provider_settings["api_key"] == "test-key"
        assert provider_request.provider_settings["model"] == "gpt-4"


class TestChatMetadata:
    """Test ChatMetadata model."""
    
    def test_create_basic_metadata(self):
        """Test creating basic metadata."""
        metadata = ChatMetadata(
            model="gpt-4",
            provider=ChatProvider.OPENAI,
            tokens_used=25
        )
        
        assert metadata.model == "gpt-4"
        assert metadata.provider == ChatProvider.OPENAI
        assert metadata.tokens_used == 25
        assert metadata.finish_reason is None
        assert metadata.response_time is None
    
    def test_create_full_metadata(self):
        """Test creating metadata with all fields."""
        metadata = ChatMetadata(
            model="llama3:8b",
            provider=ChatProvider.OLLAMA,
            tokens_used=15,
            finish_reason="stop",
            response_time=1.23
        )
        
        assert metadata.model == "llama3:8b"
        assert metadata.provider == ChatProvider.OLLAMA
        assert metadata.tokens_used == 15
        assert metadata.finish_reason == "stop"
        assert metadata.response_time == 1.23
    
    def test_from_provider_response(self):
        """Test creating metadata from provider response."""
        # Mock provider response metadata
        provider_metadata = {
            "usage": {"total_tokens": 25},
            "finish_reason": "stop",
            "id": "chatcmpl-123"
        }
        
        metadata = ChatMetadata.from_provider_response(
            model="gpt-4",
            provider=ChatProvider.OPENAI,
            provider_metadata=provider_metadata,
            response_time=1.5
        )
        
        assert metadata.model == "gpt-4"
        assert metadata.provider == ChatProvider.OPENAI
        assert metadata.tokens_used == 25
        assert metadata.finish_reason == "stop"
        assert metadata.response_time == 1.5


class TestChatSendResponse:
    """Test ChatSendResponse model."""
    
    def test_create_basic_response(self):
        """Test creating a basic chat response."""
        metadata = ChatMetadata(
            model="gpt-4",
            provider=ChatProvider.OPENAI,
            tokens_used=25
        )
        
        response = ChatSendResponse(
            content="Hello! How can I help you?",
            metadata=metadata
        )
        
        assert response.content == "Hello! How can I help you?"
        assert response.metadata.model == "gpt-4"
        assert response.metadata.tokens_used == 25
    
    def test_from_provider_response(self):
        """Test creating response from provider response."""
        # This would be a provider ChatResponse object
        from app.services.ai_providers import ChatResponse, ProviderType
        
        provider_response = ChatResponse(
            content="Hello! How can I help?",
            model="gpt-4",
            provider_type=ProviderType.OPENAI,
            metadata={
                "usage": {"total_tokens": 25},
                "finish_reason": "stop"
            }
        )
        
        response = ChatSendResponse.from_provider_response(
            provider_response=provider_response,
            response_time=1.2
        )
        
        assert response.content == "Hello! How can I help?"
        assert response.metadata.model == "gpt-4"
        assert response.metadata.provider == ChatProvider.OPENAI
        assert response.metadata.tokens_used == 25
        assert response.metadata.finish_reason == "stop"
        assert response.metadata.response_time == 1.2


class TestStreamingChatResponse:
    """Test StreamingChatResponse model."""
    
    def test_create_streaming_chunk(self):
        """Test creating a streaming response chunk."""
        response = StreamingChatResponse(
            content="Hello",
            done=False,
            metadata=None
        )
        
        assert response.content == "Hello"
        assert response.done is False
        assert response.metadata is None
    
    def test_create_final_streaming_chunk(self):
        """Test creating final streaming chunk with metadata."""
        metadata = ChatMetadata(
            model="llama3:8b",
            provider=ChatProvider.OLLAMA,
            tokens_used=10,
            finish_reason="stop"
        )
        
        response = StreamingChatResponse(
            content="",
            done=True,
            metadata=metadata
        )
        
        assert response.content == ""
        assert response.done is True
        assert response.metadata.tokens_used == 10
        assert response.metadata.finish_reason == "stop"
    
    def test_from_provider_chunk(self):
        """Test creating from provider streaming response."""
        from app.services.ai_providers import StreamingChatResponse as ProviderChunk, ProviderType
        
        provider_chunk = ProviderChunk(
            content="Hello",
            done=False,
            model="llama3:8b",
            provider_type=ProviderType.OLLAMA
        )
        
        response = StreamingChatResponse.from_provider_chunk(provider_chunk)
        
        assert response.content == "Hello"
        assert response.done is False
        # Metadata should be None for non-final chunks
        assert response.metadata is None
    
    def test_from_provider_final_chunk(self):
        """Test creating from final provider streaming response."""
        from app.services.ai_providers import StreamingChatResponse as ProviderChunk, ProviderType
        
        provider_chunk = ProviderChunk(
            content="",
            done=True,
            model="llama3:8b",
            provider_type=ProviderType.OLLAMA,
            metadata={"eval_count": 10, "total_duration": 1234567}
        )
        
        response = StreamingChatResponse.from_provider_chunk(provider_chunk)
        
        assert response.content == ""
        assert response.done is True
        assert response.metadata is not None
        assert response.metadata.model == "llama3:8b"
        assert response.metadata.provider == ChatProvider.OLLAMA


class TestChatError:
    """Test ChatError model."""
    
    def test_create_basic_error(self):
        """Test creating a basic error."""
        error = ChatError(
            error_type="connection_error",
            message="Failed to connect to provider"
        )
        
        assert error.error_type == "connection_error"
        assert error.message == "Failed to connect to provider"
        assert error.details is None
    
    def test_create_error_with_details(self):
        """Test creating error with additional details."""
        error = ChatError(
            error_type="validation_error",
            message="Invalid request parameters",
            details={
                "field": "temperature",
                "value": 3.0,
                "constraint": "must be between 0.0 and 2.0"
            }
        )
        
        assert error.error_type == "validation_error"
        assert error.message == "Invalid request parameters"
        assert error.details["field"] == "temperature"
    
    def test_from_exception(self):
        """Test creating error from exception."""
        from app.services.exceptions import ProviderConnectionError
        
        exception = ProviderConnectionError("Connection timeout")
        error = ChatError.from_exception(exception)
        
        assert error.error_type == "provider_connection_error"
        assert error.message == "Connection timeout"
    
    def test_from_validation_error(self):
        """Test creating error from Pydantic validation error."""
        try:
            ChatSendRequest(
                message="",  # This should fail validation
                provider=ChatProvider.OLLAMA,
                stream=False
            )
        except ValidationError as e:
            error = ChatError.from_validation_error(e)
            
            assert error.error_type == "validation_error"
            assert "Message cannot be empty" in error.message
            assert error.details is not None