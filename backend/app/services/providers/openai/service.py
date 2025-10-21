"""
Unified OpenAI-API compatible service using composition over inheritance.

This replaces both openai_service_base.py (573 lines) and openai_service.py (333 lines)
with a clean composition-based architecture that eliminates duplication.
"""

import logging
from typing import Dict, Any, AsyncIterator, Optional, List

from ...ai_providers import ChatRequest, ChatResponse, StreamingChatResponse, ProviderType
from ...utils.validation import SettingsValidator
from ...exceptions import ProviderConnectionError, ProviderAuthenticationError
from ..base import BaseProviderService
from .request_builder import OpenAIRequestBuilder
from .response_parser import OpenAIResponseParser, OpenAIStreamParser
from .models import OpenAIModelsResponse, OpenAIModelInfo

logger = logging.getLogger(__name__)


class OpenAIService(BaseProviderService):
    """
    Unified OpenAI-API compatible service using composition over inheritance.
    
    Replaces the problematic base/enhanced inheritance pattern with clean composition.
    Combines functionality from both openai_service_base.py and openai_service.py
    while eliminating duplication and complexity.
    
    Works with any OpenAI-API compatible service (OpenAI, OpenRouter, Groq, etc.).
    """
    
    def __init__(self):
        """
        Initialize OpenAI-API compatible service with composition-based architecture.
        """
        super().__init__("OpenAI-Compatible", ProviderType.OPENAI, timeout=300)

        # Compose functionality using focused components
        self.request_builder = OpenAIRequestBuilder()
        self.response_parser = OpenAIResponseParser()
        self.stream_parser = OpenAIStreamParser()

        # Initialize stream processor with OpenAI-specific parser
        self._init_stream_processor(self._parse_stream_chunk)
    
    def validate_settings(self, settings: Dict[str, Any]) -> bool:
        """
        Validate OpenAI-API compatible settings.
        
        Args:
            settings: Provider settings to validate
            
        Returns:
            True if settings are valid, False otherwise
        """
        # Only base_url is truly required for OpenAI-compatible APIs
        # api_key and default_model are optional for local APIs like LMStudio
        required_fields = ["base_url"]
        if not SettingsValidator.validate_required_fields(settings, required_fields):
            return False
        
        # Validate URL format
        if not SettingsValidator.validate_url_format(settings["base_url"]):
            return False
        
        return True
    
    def _build_request_payload(self, request: ChatRequest) -> Dict[str, Any]:
        """
        Build OpenAI-API compatible request payload.
        
        Args:
            request: ChatRequest to convert
            
        Returns:
            Dictionary ready for JSON serialization
        """
        openai_request = self.request_builder.build_request(request)
        return openai_request.model_dump(exclude_none=True)
    
    def _build_url(self, settings: Dict[str, Any], endpoint: str = "chat/completions") -> str:
        """
        Build OpenAI-API compatible URL.
        
        Args:
            settings: Provider settings containing base_url
            endpoint: API endpoint to append
            
        Returns:
            Complete URL for the request
        """
        return self.request_builder.build_url(settings["base_url"], endpoint)
    
    def _build_headers(self, settings: Dict[str, Any]) -> Dict[str, str]:
        """
        Build OpenAI-API compatible headers.
        
        Args:
            settings: Provider settings with authentication info
            
        Returns:
            Dictionary of HTTP headers
        """
        return self.request_builder.build_headers(settings)
    
    def _parse_response(self, response_data: Dict[str, Any]) -> ChatResponse:
        """
        Parse OpenAI-API compatible response.
        
        Args:
            response_data: Raw JSON response from OpenAI-API service
            
        Returns:
            Parsed ChatResponse
        """
        return self.response_parser.parse_response(response_data)
    
    def _parse_stream_chunk(self, chunk_line: str) -> Optional[StreamingChatResponse]:
        """
        Parse OpenAI-API compatible streaming chunk.
        
        Args:
            chunk_line: Single line from streaming response
            
        Returns:
            Parsed StreamingChatResponse or None if invalid
        """
        return self.stream_parser.parse_chunk(chunk_line)
    
    # Additional OpenAI-API specific functionality
    async def list_models(self, settings: Dict[str, Any]) -> List[str]:
        """
        List available models from OpenAI-API compatible service.
        
        Args:
            settings: Provider settings with authentication info
            
        Returns:
            List of model names available from the service
            
        Raises:
            ProviderConnectionError: If unable to connect or retrieve models
            ProviderAuthenticationError: If authentication fails
        """
        if not self.validate_settings(settings):
            raise ProviderConnectionError("Invalid OpenAI-API settings")
        
        url = self._build_url(settings, "models")
        headers = self._build_headers(settings)
        
        try:
            response_data = await self.http_client.get_json(url, headers)
            models_response = OpenAIModelsResponse(**response_data)
            return [model.id for model in models_response.data]
        except ProviderAuthenticationError:
            raise  # Re-raise auth errors
        except Exception as e:
            logger.error(f"Failed to list OpenAI-API models: {e}")
            raise ProviderConnectionError(f"Failed to retrieve model list: {str(e)}")
    
    async def test_connection(self, settings: Dict[str, Any]) -> bool:
        """
        Test connection to OpenAI-API compatible service.
        
        Args:
            settings: Provider settings to test
            
        Returns:
            True if connection successful, False otherwise
        """
        try:
            models = await self.list_models(settings)
            return len(models) > 0
        except Exception as e:
            logger.warning(f"OpenAI-API connection test failed: {e}")
            return False
    


class OpenAIServiceFactory:
    """
    Factory for creating OpenAI-API compatible service instances.

    Maintains backward compatibility with existing factory pattern.
    """

    @classmethod
    def create_service(cls) -> OpenAIService:
        """
        Create an OpenAI-API compatible service instance.

        Returns:
            Configured OpenAIService instance
        """
        return OpenAIService()