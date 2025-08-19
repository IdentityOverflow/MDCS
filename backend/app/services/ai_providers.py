"""
AI Provider base classes and factory for handling different AI providers.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, Optional, AsyncIterator, List
from pydantic import BaseModel, Field, field_validator

from .exceptions import UnsupportedProviderError, ProviderConnectionError, ProviderAuthenticationError


class ProviderType(str, Enum):
    """Enumeration of supported AI providers."""
    OLLAMA = "ollama"
    OPENAI = "openai"


class ChatRequest(BaseModel):
    """Request model for chat messages."""
    message: str = Field(..., description="The message to send to the AI")
    provider_type: ProviderType = Field(..., description="The AI provider to use")
    provider_settings: Dict[str, Any] = Field(..., description="Provider-specific settings")
    chat_controls: Dict[str, Any] = Field(default_factory=dict, description="Chat control parameters")
    
    @field_validator('message')
    def validate_message(cls, v):
        if not v or not v.strip():
            raise ValueError("Message cannot be empty")
        return v
    
    @field_validator('provider_settings')
    def validate_provider_settings(cls, v):
        if not v:
            raise ValueError("Provider settings are required")
        return v


class ChatResponse(BaseModel):
    """Response model for chat messages."""
    content: str = Field(..., description="The response content")
    model: str = Field(..., description="The model used for generation")
    provider_type: ProviderType = Field(..., description="The provider that generated the response")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional response metadata")


class StreamingChatResponse(BaseModel):
    """Response model for streaming chat messages."""
    content: str = Field(..., description="The chunk content")
    done: bool = Field(..., description="Whether this is the final chunk")
    model: str = Field(..., description="The model used for generation")
    provider_type: ProviderType = Field(..., description="The provider that generated the response")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional chunk metadata")


class AIProvider(ABC):
    """Abstract base class for AI providers."""
    
    @abstractmethod
    def validate_settings(self, settings: Dict[str, Any]) -> bool:
        """Validate provider-specific settings."""
        pass
    
    @abstractmethod
    async def send_message(self, request: ChatRequest) -> ChatResponse:
        """Send a message and get a complete response."""
        pass
    
    @abstractmethod
    async def send_message_stream(self, request: ChatRequest) -> AsyncIterator[StreamingChatResponse]:
        """Send a message and get a streaming response."""
        pass


# Placeholder class for backwards compatibility
class OpenAIProvider(AIProvider):
    """OpenAI-compatible provider implementation."""
    
    def validate_settings(self, settings: Dict[str, Any]) -> bool:
        """Validate OpenAI-specific settings."""
        required_fields = ["base_url", "api_key", "default_model"]
        return all(field in settings for field in required_fields)
    
    async def send_message(self, request: ChatRequest) -> ChatResponse:
        """Send message to OpenAI-compatible provider."""
        # Placeholder implementation - will be expanded later
        raise NotImplementedError("OpenAI provider not yet implemented")
    
    async def send_message_stream(self, request: ChatRequest) -> AsyncIterator[StreamingChatResponse]:
        """Stream message from OpenAI-compatible provider."""
        # Placeholder implementation - will be expanded later
        raise NotImplementedError("OpenAI streaming not yet implemented")
        yield  # Make this a generator function


class ProviderFactory:
    """Factory for creating AI provider instances."""
    
    @classmethod
    def create_provider(cls, provider_type: ProviderType) -> AIProvider:
        """Create a provider instance."""
        # Import here to avoid circular imports
        from .ollama_service import OllamaService
        from .openai_service import OpenAIService
        
        _providers = {
            ProviderType.OLLAMA: OllamaService,
            ProviderType.OPENAI: OpenAIService,
        }
        
        if provider_type not in _providers:
            raise UnsupportedProviderError(str(provider_type))
        
        provider_class = _providers[provider_type]
        return provider_class()
    
    @classmethod
    def get_available_providers(cls) -> List[ProviderType]:
        """Get list of available provider types."""
        return [ProviderType.OLLAMA, ProviderType.OPENAI]