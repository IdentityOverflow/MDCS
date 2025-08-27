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
    system_prompt: str = Field(default="", description="System prompt to use for the conversation")
    
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
    thinking: Optional[str] = Field(None, description="The model's reasoning/thinking process (if available)")


class StreamingChatResponse(BaseModel):
    """Response model for streaming chat messages."""
    content: str = Field(..., description="The chunk content")
    done: bool = Field(..., description="Whether this is the final chunk")
    model: str = Field(..., description="The model used for generation")
    provider_type: ProviderType = Field(..., description="The provider that generated the response")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional chunk metadata")
    thinking: Optional[str] = Field(None, description="The model's reasoning/thinking process (if available)")


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
    
    def _build_base_messages(self, request: ChatRequest) -> List[Dict[str, str]]:
        """
        Build base messages array with system prompt handling.
        
        This centralizes system prompt logic and provides a consistent
        message format across all providers. Providers can override
        this method if they need custom message formatting.
        
        Args:
            request: Chat request with message and system prompt
            
        Returns:
            List of message dictionaries in standard format
        """
        messages = []
        
        # Add system message if present (from resolved persona template or legacy chat controls)
        system_message = request.system_prompt or request.chat_controls.get("system_or_instructions")
        
        # Debug logging for system prompt handling
        import logging
        logger = logging.getLogger(__name__)
        
        if system_message:
            messages.append({
                "role": "system",
                "content": system_message
            })
            logger.info(f"Added system message with {len(system_message)} characters")
        else:
            logger.warning("No system message found in request")
        
        # Add user message
        messages.append({
            "role": "user",
            "content": request.message
        })
        
        return messages


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