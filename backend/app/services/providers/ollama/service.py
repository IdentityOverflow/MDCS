"""
Unified Ollama service using composition over inheritance.

This replaces both ollama_service_base.py (430 lines) and ollama_service.py (331 lines)
with a clean composition-based architecture that eliminates duplication.
"""

import logging
from typing import Dict, Any, AsyncIterator, Optional, List

from ...ai_providers import ChatRequest, ChatResponse, StreamingChatResponse, ProviderType
from ...utils.validation import SettingsValidator
from ...exceptions import ProviderConnectionError
from ..base import BaseProviderService
from .request_builder import OllamaRequestBuilder
from .response_parser import OllamaResponseParser, OllamaStreamParser
from .models import OllamaModelsResponse, OllamaModelInfo

logger = logging.getLogger(__name__)


class OllamaService(BaseProviderService):
    """
    Unified Ollama service using composition over inheritance.
    
    Replaces the problematic base/enhanced inheritance pattern with clean composition.
    Combines functionality from both ollama_service_base.py and ollama_service.py
    while eliminating duplication and complexity.
    """
    
    def __init__(self):
        """
        Initialize Ollama service with composition-based architecture.
        """
        super().__init__("Ollama", ProviderType.OLLAMA, timeout=300)

        # Compose functionality using focused components
        self.request_builder = OllamaRequestBuilder()
        self.response_parser = OllamaResponseParser()
        self.stream_parser = OllamaStreamParser()

        # Initialize stream processor with Ollama-specific parser
        self._init_stream_processor(self._parse_stream_chunk)
    
    def validate_settings(self, settings: Dict[str, Any]) -> bool:
        """
        Validate Ollama-specific settings.
        
        Args:
            settings: Provider settings to validate
            
        Returns:
            True if settings are valid, False otherwise
        """
        required_fields = ["host", "model"]
        if not SettingsValidator.validate_required_fields(settings, required_fields):
            return False
        
        # Validate URL format
        if not SettingsValidator.validate_url_format(settings["host"]):
            return False
        
        return True
    
    def _build_request_payload(self, request: ChatRequest) -> Dict[str, Any]:
        """
        Build Ollama-specific request payload.
        
        Args:
            request: ChatRequest to convert
            
        Returns:
            Dictionary ready for JSON serialization
        """
        ollama_request = self.request_builder.build_request(request)
        return ollama_request.model_dump(exclude_none=True)
    
    def _build_url(self, settings: Dict[str, Any], endpoint: str = "api/chat") -> str:
        """
        Build Ollama-specific URL.
        
        Args:
            settings: Provider settings containing host
            endpoint: API endpoint to append
            
        Returns:
            Complete URL for the request
        """
        return self.request_builder.build_url(settings["host"], endpoint)
    
    def _build_headers(self, settings: Dict[str, Any]) -> Dict[str, str]:
        """
        Build Ollama-specific headers.
        
        Args:
            settings: Provider settings (Ollama doesn't require auth headers)
            
        Returns:
            Dictionary of HTTP headers
        """
        return {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    def _parse_response(self, response_data: Dict[str, Any]) -> ChatResponse:
        """
        Parse Ollama-specific response.
        
        Args:
            response_data: Raw JSON response from Ollama
            
        Returns:
            Parsed ChatResponse
        """
        return self.response_parser.parse_response(response_data)
    
    def _parse_stream_chunk(self, chunk_line: str) -> Optional[StreamingChatResponse]:
        """
        Parse Ollama-specific streaming chunk.
        
        Args:
            chunk_line: Single line of JSON from stream
            
        Returns:
            Parsed StreamingChatResponse or None if invalid
        """
        return self.stream_parser.parse_chunk(chunk_line)
    
    # Additional Ollama-specific functionality
    async def list_models(self, settings: Dict[str, Any]) -> List[str]:
        """
        List available models from Ollama server.
        
        Args:
            settings: Provider settings with host information
            
        Returns:
            List of model names available on the server
            
        Raises:
            ProviderConnectionError: If unable to connect or retrieve models
        """
        if not self.validate_settings({"host": settings.get("host"), "model": "dummy"}):
            raise ProviderConnectionError("Invalid Ollama host settings")
        
        url = self._build_url(settings, "api/tags")
        headers = self._build_headers(settings)
        
        try:
            response_data = await self.http_client.get_json(url, headers)
            models_response = OllamaModelsResponse(**response_data)
            return [model.name for model in models_response.models]
        except Exception as e:
            logger.error(f"Failed to list Ollama models: {e}")
            raise ProviderConnectionError(f"Failed to retrieve model list: {str(e)}")
    
    async def test_connection(self, settings: Dict[str, Any]) -> bool:
        """
        Test connection to Ollama server.
        
        Args:
            settings: Provider settings to test
            
        Returns:
            True if connection successful, False otherwise
        """
        try:
            models = await self.list_models(settings)
            return len(models) > 0
        except Exception as e:
            logger.warning(f"Ollama connection test failed: {e}")
            return False
    


class OllamaServiceFactory:
    """
    Factory for creating Ollama service instances.

    Maintains backward compatibility with existing factory pattern.
    """

    @classmethod
    def create_service(cls) -> OllamaService:
        """
        Create an Ollama service instance.

        Returns:
            Configured OllamaService instance
        """
        return OllamaService()