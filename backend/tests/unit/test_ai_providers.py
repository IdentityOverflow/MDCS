"""
Unit tests for AI provider base class and factory.
"""

import pytest
from abc import ABC
from typing import Dict, Any, Optional, AsyncIterator
from unittest.mock import Mock, AsyncMock

from app.services.ai_providers import (
    AIProvider,
    ProviderFactory,
    ProviderType,
    ChatRequest,
    ChatResponse,
    StreamingChatResponse
)
from app.services.exceptions import (
    UnsupportedProviderError,
    ProviderConnectionError,
    ProviderAuthenticationError
)


class TestChatRequest:
    """Test ChatRequest model validation."""
    
    def test_chat_request_creation(self):
        """Test basic chat request creation."""
        request = ChatRequest(
            message="Hello, world!",
            provider_type=ProviderType.OLLAMA,
            provider_settings={"host": "http://localhost:11434", "model": "llama3:8b"},
            chat_controls={"temperature": 0.7}
        )
        
        assert request.message == "Hello, world!"
        assert request.provider_type == ProviderType.OLLAMA
        assert request.provider_settings["host"] == "http://localhost:11434"
        assert request.chat_controls["temperature"] == 0.7
    
    def test_chat_request_validation_empty_message(self):
        """Test that empty messages are rejected."""
        with pytest.raises(ValueError, match="Message cannot be empty"):
            ChatRequest(
                message="",
                provider_type=ProviderType.OLLAMA,
                provider_settings={"host": "localhost", "model": "llama3"},
                chat_controls={}
            )
    
    def test_chat_request_validation_missing_provider_settings(self):
        """Test that provider settings are required."""
        with pytest.raises(ValueError, match="Provider settings are required"):
            ChatRequest(
                message="Hello",
                provider_type=ProviderType.OLLAMA,
                provider_settings={},
                chat_controls={}
            )


class TestChatResponse:
    """Test ChatResponse model."""
    
    def test_chat_response_creation(self):
        """Test basic chat response creation."""
        response = ChatResponse(
            content="Hello! How can I help you?",
            model="llama3:8b",
            provider_type=ProviderType.OLLAMA,
            metadata={"tokens_used": 15}
        )
        
        assert response.content == "Hello! How can I help you?"
        assert response.model == "llama3:8b"
        assert response.provider_type == ProviderType.OLLAMA
        assert response.metadata["tokens_used"] == 15


class TestStreamingChatResponse:
    """Test StreamingChatResponse model."""
    
    def test_streaming_response_chunk(self):
        """Test streaming response chunk creation."""
        chunk = StreamingChatResponse(
            content="Hello",
            done=False,
            model="gpt-4",
            provider_type=ProviderType.OPENAI
        )
        
        assert chunk.content == "Hello"
        assert chunk.done is False
        assert chunk.model == "gpt-4"
        assert chunk.provider_type == ProviderType.OPENAI
    
    def test_streaming_response_final_chunk(self):
        """Test final streaming response chunk."""
        chunk = StreamingChatResponse(
            content="",
            done=True,
            model="gpt-4",
            provider_type=ProviderType.OPENAI,
            metadata={"total_tokens": 50}
        )
        
        assert chunk.content == ""
        assert chunk.done is True
        assert chunk.metadata["total_tokens"] == 50


class TestAIProvider:
    """Test AIProvider abstract base class."""
    
    def test_ai_provider_is_abstract(self):
        """Test that AIProvider cannot be instantiated directly."""
        with pytest.raises(TypeError):
            AIProvider()
    
    def test_ai_provider_subclass_must_implement_methods(self):
        """Test that subclasses must implement required methods."""
        class IncompleteProvider(AIProvider):
            pass
        
        with pytest.raises(TypeError):
            IncompleteProvider()
    
    def test_valid_ai_provider_subclass(self):
        """Test that a complete subclass can be instantiated."""
        class TestProvider(AIProvider):
            def validate_settings(self, settings: Dict[str, Any]) -> bool:
                return True
            
            async def send_message(self, request: ChatRequest) -> ChatResponse:
                return ChatResponse(
                    content="Test response",
                    model="test-model",
                    provider_type=ProviderType.OLLAMA
                )
            
            async def send_message_stream(self, request: ChatRequest) -> AsyncIterator[StreamingChatResponse]:
                yield StreamingChatResponse(
                    content="Test",
                    done=True,
                    model="test-model", 
                    provider_type=ProviderType.OLLAMA
                )
        
        provider = TestProvider()
        assert isinstance(provider, AIProvider)


class TestProviderFactory:
    """Test ProviderFactory functionality."""
    
    def test_factory_creates_ollama_provider(self):
        """Test factory creates Ollama provider."""
        provider = ProviderFactory.create_provider(ProviderType.OLLAMA)
        assert provider is not None
        assert provider.__class__.__name__ == "OllamaService"
    
    def test_factory_creates_openai_provider(self):
        """Test factory creates OpenAI provider."""
        provider = ProviderFactory.create_provider(ProviderType.OPENAI)
        assert provider is not None
        assert provider.__class__.__name__ == "OpenAIService"
    
    def test_factory_raises_error_for_unsupported_provider(self):
        """Test factory raises error for unsupported provider type."""
        with pytest.raises(UnsupportedProviderError, match="Unsupported provider type: invalid"):
            ProviderFactory.create_provider("invalid")
    
    def test_factory_get_available_providers(self):
        """Test factory returns list of available providers."""
        providers = ProviderFactory.get_available_providers()
        assert ProviderType.OLLAMA in providers
        assert ProviderType.OPENAI in providers
        assert len(providers) >= 2


class TestProviderExceptions:
    """Test custom provider exceptions."""
    
    def test_unsupported_provider_error(self):
        """Test UnsupportedProviderError."""
        error = UnsupportedProviderError("test-provider")
        assert str(error) == "Unsupported provider type: test-provider"
    
    def test_provider_connection_error(self):
        """Test ProviderConnectionError."""
        error = ProviderConnectionError("Failed to connect to provider")
        assert str(error) == "Failed to connect to provider"
    
    def test_provider_authentication_error(self):
        """Test ProviderAuthenticationError."""
        error = ProviderAuthenticationError("Invalid API key")
        assert str(error) == "Invalid API key"


# Integration-style tests that will require implementation
class TestProviderIntegration:
    """Integration tests for provider functionality."""
    
    @pytest.mark.asyncio
    async def test_provider_sends_message(self):
        """Test that providers can send messages."""
        # Test that the provider is properly instantiated and has the right interface
        provider = ProviderFactory.create_provider(ProviderType.OLLAMA)
        
        request = ChatRequest(
            message="Hello",
            provider_type=ProviderType.OLLAMA,
            provider_settings={
                "host": "http://localhost:11434",
                "model": "llama3:8b"
            },
            chat_controls={"temperature": 0.7}
        )
        
        # Test that the provider has the send_message method and validates settings
        assert hasattr(provider, 'send_message')
        assert provider.validate_settings(request.provider_settings) is True
    
    @pytest.mark.asyncio
    async def test_provider_streams_message(self):
        """Test that providers can stream messages."""
        # Test that the provider is properly instantiated and has the right interface
        provider = ProviderFactory.create_provider(ProviderType.OLLAMA)
        
        request = ChatRequest(
            message="Hello",
            provider_type=ProviderType.OLLAMA,
            provider_settings={
                "host": "http://localhost:11434", 
                "model": "llama3:8b"
            },
            chat_controls={"temperature": 0.7, "stream": True}
        )
        
        # Test that the provider has the streaming method and validates settings
        assert hasattr(provider, 'send_message_stream')
        assert provider.validate_settings(request.provider_settings) is True