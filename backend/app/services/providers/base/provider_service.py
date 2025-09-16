"""
Base provider service using composition over inheritance.

This module replaces the problematic base/enhanced inheritance pattern 
with a clean composition-based architecture that eliminates duplication.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, AsyncIterator, Optional

from ...ai_providers import AIProvider, ChatRequest, ChatResponse, StreamingChatResponse, ProviderType
from ...exceptions import ProviderConnectionError
from .http_client import BaseHTTPClient
from .stream_processor import BaseStreamProcessor


class BaseProviderService(AIProvider):
    """
    Base class for all provider services using composition over inheritance.
    
    Eliminates the base/enhanced service duplication by providing shared 
    functionality through composition rather than inheritance chains.
    
    This replaces the problematic pattern of:
    - ollama_service_base.py (430 lines) + ollama_service.py (331 lines)
    - openai_service_base.py (573 lines) + openai_service.py (333 lines)
    
    With clean composition-based services that share common HTTP and streaming logic.
    """
    
    def __init__(self, provider_name: str, provider_type: ProviderType, timeout: int = 300):
        """
        Initialize base provider service.
        
        Args:
            provider_name: Human-readable name of the provider
            provider_type: ProviderType enum value
            timeout: Default timeout for HTTP requests
        """
        self.provider_name = provider_name
        self.provider_type = provider_type
        self.http_client = BaseHTTPClient(provider_name, timeout)
        # Stream processor will be initialized in subclasses with provider-specific parser
        self._stream_processor = None
    
    def _init_stream_processor(self, chunk_parser) -> None:
        """Initialize stream processor with provider-specific chunk parser."""
        self._stream_processor = BaseStreamProcessor(chunk_parser)
    
    # Abstract methods that subclasses must implement
    @abstractmethod
    def validate_settings(self, settings: Dict[str, Any]) -> bool:
        """Provider-specific settings validation."""
        pass
    
    @abstractmethod
    def _build_request_payload(self, request: ChatRequest) -> Dict[str, Any]:
        """Build provider-specific request payload."""
        pass
    
    @abstractmethod
    def _build_url(self, settings: Dict[str, Any], endpoint: str = "chat/completions") -> str:
        """Build provider-specific URL."""
        pass
    
    @abstractmethod 
    def _build_headers(self, settings: Dict[str, Any]) -> Dict[str, str]:
        """Build provider-specific headers."""
        pass
    
    @abstractmethod
    def _parse_response(self, response_data: Dict[str, Any]) -> ChatResponse:
        """Parse provider-specific response."""
        pass
    
    @abstractmethod
    def _parse_stream_chunk(self, chunk_line: str) -> Optional[StreamingChatResponse]:
        """Parse provider-specific streaming chunk."""
        pass
    
    # Shared implementation using composition
    async def send_message(self, request: ChatRequest) -> ChatResponse:
        """
        Shared send_message implementation using HTTP client composition.
        
        This method provides the complete request lifecycle:
        1. Validate provider settings
        2. Build URL, headers, and payload
        3. Execute HTTP request via shared client
        4. Parse response using provider-specific logic
        5. Add debug metadata for debugger support
        
        Args:
            request: ChatRequest with message and provider settings
            
        Returns:
            ChatResponse with provider's response and debug metadata
            
        Raises:
            ProviderConnectionError: For validation or connection failures
        """
        # Validate settings using provider-specific logic
        if not self.validate_settings(request.provider_settings):
            raise ProviderConnectionError(f"Invalid {self.provider_name} settings")
        
        # Build request components using provider-specific logic
        url = self._build_url(request.provider_settings)
        headers = self._build_headers(request.provider_settings)
        payload = self._build_request_payload(request)
        
        # Execute request using shared HTTP client
        response_data = await self.http_client.post_json(url, payload, headers)
        
        # Parse response using provider-specific logic
        parsed_response = self._parse_response(response_data)
        
        # Add debug metadata for debugger support (matches old provider behavior)
        parsed_response.metadata["debug_api_request"] = payload
        parsed_response.metadata["debug_api_response"] = response_data
        parsed_response.metadata["debug_api_url"] = url
        
        return parsed_response
    
    async def send_message_stream(self, request: ChatRequest, session_id: Optional[str] = None) -> AsyncIterator[StreamingChatResponse]:
        """
        Shared streaming implementation using stream processor composition.
        
        This method provides the complete streaming lifecycle:
        1. Validate provider settings
        2. Build URL, headers, and payload  
        3. Execute streaming request via shared client
        4. Process stream using shared processor with provider-specific parsing
        5. Add debug metadata to final chunk for debugger support
        
        Args:
            request: ChatRequest with message and provider settings
            
        Yields:
            StreamingChatResponse objects from the provider with debug metadata on final chunk
            
        Raises:
            ProviderConnectionError: For validation or connection failures
        """
        # Validate settings using provider-specific logic
        if not self.validate_settings(request.provider_settings):
            raise ProviderConnectionError(f"Invalid {self.provider_name} settings")
        
        # Ensure stream processor is initialized
        if not self._stream_processor:
            self._init_stream_processor(self._parse_stream_chunk)
        
        # Build request components using provider-specific logic
        url = self._build_url(request.provider_settings)  
        headers = self._build_headers(request.provider_settings)
        payload = self._build_request_payload(request)
        
        # Execute streaming request using shared HTTP client
        chunk_stream = self.http_client.stream_post(url, payload, headers)
        
        # Process stream using shared processor with provider-specific parsing
        async for response_chunk in self._stream_processor.process_stream(chunk_stream):
            # Check for cancellation before processing each chunk
            if session_id and self._is_session_cancelled(session_id):
                logger.info(f"Stream cancelled for session {session_id}")
                break
            
            # Add debug metadata to the final chunk (matches old provider behavior)
            if response_chunk.done:
                response_chunk.metadata["debug_api_request"] = payload
                response_chunk.metadata["debug_api_response"] = {}  # We don't have access to raw chunk data here
                response_chunk.metadata["debug_api_url"] = url
            
            yield response_chunk
    
    # Session management support (for Phase 2 integration)
    def set_session_id(self, session_id: Optional[str]) -> None:
        """Set session ID for session management integration."""
        # This will be used in Phase 2 when integrating session management
        pass
    
    def _is_session_cancelled(self, session_id: str) -> bool:
        """Check if a session is cancelled."""
        try:
            from ...chat_session_manager import get_chat_session_manager
            session_manager = get_chat_session_manager()
            token = session_manager.get_session(session_id)
            return token is not None and token.is_cancelled()
        except Exception as e:
            logger.warning(f"Failed to check session cancellation for {session_id}: {e}")
            return False
    
    async def send_message_with_session(self, 
                                      request: ChatRequest, 
                                      session_id: str, 
                                      conversation_id: str) -> ChatResponse:
        """Send message with session management (for Phase 2 integration)."""
        # This will be implemented in Phase 2 when session management is integrated
        return await self.send_message(request)
    
    async def send_message_stream_with_session(self, 
                                             request: ChatRequest, 
                                             session_id: str, 
                                             conversation_id: str) -> AsyncIterator[StreamingChatResponse]:
        """Send streaming message with session management (for Phase 2 integration)."""
        # This will be implemented in Phase 2 when session management is integrated
        async for chunk in self.send_message_stream(request):
            yield chunk