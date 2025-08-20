"""
Pydantic models for the internal chat API.
"""

from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator

from ..services.ai_providers import ChatRequest, ChatResponse, ProviderType
from ..services.ai_providers import StreamingChatResponse as ProviderStreamingResponse
from ..services.exceptions import ProviderConnectionError, ProviderAuthenticationError, UnsupportedProviderError


class ChatProvider(str, Enum):
    """Chat provider enumeration for the API."""
    OLLAMA = "ollama"
    OPENAI = "openai"


class ChatSendRequest(BaseModel):
    """Request model for sending chat messages."""
    message: str = Field(..., description="The message to send")
    provider: ChatProvider = Field(..., description="The AI provider to use")
    stream: bool = Field(default=False, description="Whether to stream the response")
    chat_controls: Dict[str, Any] = Field(default_factory=dict, description="Chat control parameters")
    provider_settings: Optional[Dict[str, Any]] = Field(None, description="Provider connection settings")
    
    @field_validator('message')
    def validate_message(cls, v):
        if not v or not v.strip():
            raise ValueError("Message cannot be empty")
        return v
    
    def to_provider_request(self, fallback_settings: Optional[Dict[str, Any]] = None) -> ChatRequest:
        """Convert to provider ChatRequest."""
        provider_type = ProviderType.OLLAMA if self.provider == ChatProvider.OLLAMA else ProviderType.OPENAI
        
        # Use provider settings from request, or fallback if not provided
        settings = self.provider_settings or fallback_settings or {}
        
        # Add stream setting to chat controls
        chat_controls = self.chat_controls.copy()
        chat_controls["stream"] = self.stream
        
        return ChatRequest(
            message=self.message,
            provider_type=provider_type,
            provider_settings=settings,
            chat_controls=chat_controls
        )


class ChatMetadata(BaseModel):
    """Metadata for chat responses."""
    model: str = Field(..., description="The model used for generation")
    provider: ChatProvider = Field(..., description="The provider that generated the response")
    tokens_used: Optional[int] = Field(None, description="Number of tokens used")
    finish_reason: Optional[str] = Field(None, description="Reason generation finished")
    response_time: Optional[float] = Field(None, description="Response time in seconds")
    
    @classmethod
    def from_provider_response(cls, model: str, provider: ChatProvider, 
                             provider_metadata: Dict[str, Any], 
                             response_time: Optional[float] = None) -> "ChatMetadata":
        """Create metadata from provider response."""
        tokens_used = None
        if "usage" in provider_metadata and "total_tokens" in provider_metadata["usage"]:
            tokens_used = provider_metadata["usage"]["total_tokens"]
        elif "eval_count" in provider_metadata:
            # Ollama style token counting
            tokens_used = provider_metadata["eval_count"]
        
        finish_reason = provider_metadata.get("finish_reason")
        
        return cls(
            model=model,
            provider=provider,
            tokens_used=tokens_used,
            finish_reason=finish_reason,
            response_time=response_time
        )


class ChatSendResponse(BaseModel):
    """Response model for chat messages."""
    content: str = Field(..., description="The response content")
    metadata: ChatMetadata = Field(..., description="Response metadata")
    thinking: Optional[str] = Field(None, description="The model's reasoning/thinking process")
    
    @classmethod
    def from_provider_response(cls, provider_response: ChatResponse, 
                             response_time: Optional[float] = None) -> "ChatSendResponse":
        """Create response from provider response."""
        provider = ChatProvider.OLLAMA if provider_response.provider_type == ProviderType.OLLAMA else ChatProvider.OPENAI
        
        metadata = ChatMetadata.from_provider_response(
            model=provider_response.model,
            provider=provider,
            provider_metadata=provider_response.metadata,
            response_time=response_time
        )
        
        return cls(
            content=provider_response.content,
            metadata=metadata,
            thinking=provider_response.thinking
        )


class StreamingChatResponse(BaseModel):
    """Response model for streaming chat messages."""
    content: str = Field(..., description="The chunk content")
    done: bool = Field(..., description="Whether this is the final chunk")
    metadata: Optional[ChatMetadata] = Field(None, description="Metadata (only present in final chunk)")
    thinking: Optional[str] = Field(None, description="The model's reasoning/thinking process (if available)")
    
    @classmethod
    def from_provider_chunk(cls, provider_chunk: ProviderStreamingResponse, 
                          response_time: Optional[float] = None) -> "StreamingChatResponse":
        """Create from provider streaming response."""
        metadata = None
        
        # Only include metadata in the final chunk
        if provider_chunk.done:
            provider = ChatProvider.OLLAMA if provider_chunk.provider_type == ProviderType.OLLAMA else ChatProvider.OPENAI
            metadata = ChatMetadata.from_provider_response(
                model=provider_chunk.model,
                provider=provider,
                provider_metadata=provider_chunk.metadata,
                response_time=response_time
            )
        
        return cls(
            content=provider_chunk.content,
            done=provider_chunk.done,
            metadata=metadata,
            thinking=provider_chunk.thinking
        )


class ChatError(BaseModel):
    """Error response model."""
    error_type: str = Field(..., description="Type of error")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    
    @classmethod
    def from_exception(cls, exception: Exception) -> "ChatError":
        """Create error from exception."""
        error_type = "unknown_error"
        
        if isinstance(exception, ProviderConnectionError):
            error_type = "provider_connection_error"
        elif isinstance(exception, ProviderAuthenticationError):
            error_type = "provider_authentication_error"
        elif isinstance(exception, UnsupportedProviderError):
            error_type = "unsupported_provider_error"
        elif isinstance(exception, ValueError):
            error_type = "validation_error"
        
        return cls(
            error_type=error_type,
            message=str(exception)
        )
    
    @classmethod
    def from_validation_error(cls, validation_error) -> "ChatError":
        """Create error from Pydantic validation error."""
        # Extract meaningful error message from validation error
        error_messages = []
        for error in validation_error.errors():
            field = " -> ".join(str(loc) for loc in error["loc"])
            message = error["msg"]
            error_messages.append(f"{field}: {message}")
        
        return cls(
            error_type="validation_error",
            message="; ".join(error_messages),
            details={"validation_errors": validation_error.errors()}
        )