"""
Ollama service implementation for AI chat functionality.
"""

import json
import logging
from typing import Dict, Any, List, AsyncIterator
from urllib.parse import urljoin

import aiohttp
from aiohttp import ClientTimeout, ClientConnectorError, ClientError

from .ai_providers import (
    AIProvider,
    ChatRequest,
    ChatResponse,
    StreamingChatResponse,
    ProviderType
)
from .exceptions import ProviderConnectionError, ProviderAuthenticationError

logger = logging.getLogger(__name__)


class OllamaRequestBuilder:
    """Builds Ollama API requests from chat requests."""
    
    def __init__(self, service: 'OllamaService'):
        """Initialize with reference to parent service for base methods."""
        self.service = service
    
    def build_request(self, request: ChatRequest) -> Dict[str, Any]:
        """Build Ollama API request payload."""
        # Get model from either 'model' or 'default_model' field
        model = request.provider_settings.get("model") or request.provider_settings.get("default_model")
        logger.info(f"Using model: {model} (from provider_settings: {request.provider_settings})")
        
        # Build messages first so we can log them
        messages = self._build_messages(request)
        logger.info(f"Built {len(messages)} messages for Ollama:")
        for i, msg in enumerate(messages):
            logger.info(f"  Message {i+1}: {msg['role']} - '{msg['content'][:100]}{'...' if len(msg['content']) > 100 else ''}'")
        
        # Start with basic request structure
        ollama_request = {
            "model": model,
            "messages": messages,
            "stream": self._get_stream_setting(request),
            "options": self._build_options(request.chat_controls)
        }
        
        # Add optional fields
        if "keep_alive" in request.provider_settings:
            ollama_request["keep_alive"] = request.provider_settings["keep_alive"]
        
        format_setting = self._get_format_setting(request)
        if format_setting:
            ollama_request["format"] = format_setting
        
        # Add thinking support
        thinking_enabled = request.chat_controls.get("thinking_enabled", False)
        
        if thinking_enabled:
            ollama_request["think"] = True
        return ollama_request
    
    def _build_messages(self, request: ChatRequest) -> List[Dict[str, str]]:
        """Build messages array for Ollama using base implementation."""
        return self.service._build_base_messages(request)
    
    def _get_stream_setting(self, request: ChatRequest) -> bool:
        """Get streaming setting from request."""
        # Check chat controls first, then provider settings
        if "stream" in request.chat_controls:
            return request.chat_controls["stream"]
        return request.provider_settings.get("stream", False)
    
    def _get_format_setting(self, request: ChatRequest) -> str:
        """Get format setting for JSON mode."""
        # Check provider settings first
        if "format" in request.provider_settings and request.provider_settings["format"]:
            return request.provider_settings["format"]
        
        # Check chat controls
        json_mode = request.chat_controls.get("json_mode")
        if json_mode in ["json_object", "json_schema"]:
            return "json"
        
        return None
    
    def _build_options(self, chat_controls: Dict[str, Any]) -> Dict[str, Any]:
        """Build options object for Ollama."""
        options = {}
        
        # Map standard parameters
        if "temperature" in chat_controls:
            options["temperature"] = chat_controls["temperature"]
        if "top_p" in chat_controls:
            options["top_p"] = chat_controls["top_p"]
        if "max_tokens" in chat_controls:
            options["num_predict"] = chat_controls["max_tokens"]
        if "seed" in chat_controls and chat_controls["seed"] is not None:
            options["seed"] = chat_controls["seed"]
        if "stop" in chat_controls and chat_controls["stop"]:
            options["stop"] = chat_controls["stop"]
        
        # Map Ollama-specific parameters
        if "ollama_top_k" in chat_controls:
            options["top_k"] = chat_controls["ollama_top_k"]
        if "ollama_repeat_penalty" in chat_controls:
            options["repeat_penalty"] = chat_controls["ollama_repeat_penalty"]
        if "ollama_mirostat" in chat_controls:
            options["mirostat"] = chat_controls["ollama_mirostat"]
        if "ollama_num_ctx" in chat_controls:
            options["num_ctx"] = chat_controls["ollama_num_ctx"]
        
        return options
    
    def build_url(self, host: str, route: str = None) -> str:
        """Build the full URL for Ollama API."""
        # Remove trailing slash from host
        host = host.rstrip('/')
        
        # Use default route if not specified
        if not route:
            route = "/api/chat"
        
        return f"{host}{route}"


class OllamaResponseParser:
    """Parses Ollama API responses."""
    
    def parse_response(self, response_data: Dict[str, Any]) -> ChatResponse:
        """Parse non-streaming Ollama response."""
        logger.info(f"Parsing Ollama response: {response_data}")
        
        content = ""
        if "message" in response_data and "content" in response_data["message"]:
            content = response_data["message"]["content"]
        
        # Extract thinking content if available
        thinking = None
        if "message" in response_data and "thinking" in response_data["message"]:
            thinking = response_data["message"]["thinking"]
        
        # Extract metadata
        metadata = {}
        for field in ["total_duration", "load_duration", "prompt_eval_count", "eval_count"]:
            if field in response_data:
                metadata[field] = response_data[field]
        
        return ChatResponse(
            content=content,
            model=response_data.get("model", "unknown"),
            provider_type=ProviderType.OLLAMA,
            metadata=metadata,
            thinking=thinking
        )


class OllamaStreamParser:
    """Parses Ollama streaming responses."""
    
    def parse_chunk(self, chunk_data: Dict[str, Any]) -> StreamingChatResponse:
        """Parse individual streaming chunk."""
        content = ""
        if "message" in chunk_data and "content" in chunk_data["message"]:
            content = chunk_data["message"]["content"]
        
        # Extract thinking content if available
        thinking = None
        if "message" in chunk_data and "thinking" in chunk_data["message"]:
            thinking = chunk_data["message"]["thinking"]
        
        done = chunk_data.get("done", False)
        
        # Extract metadata for final chunk
        metadata = {}
        if done:
            for field in ["total_duration", "load_duration", "prompt_eval_count", "eval_count"]:
                if field in chunk_data:
                    metadata[field] = chunk_data[field]
        
        return StreamingChatResponse(
            content=content,
            done=done,
            model=chunk_data.get("model", "unknown"),
            provider_type=ProviderType.OLLAMA,
            metadata=metadata,
            thinking=thinking
        )


class OllamaService(AIProvider):
    """Ollama AI provider implementation."""
    
    def __init__(self):
        self.request_builder = OllamaRequestBuilder(self)
        self.response_parser = OllamaResponseParser()
        self.stream_parser = OllamaStreamParser()
    
    def validate_settings(self, settings: Dict[str, Any]) -> bool:
        """Validate Ollama-specific settings."""
        required_fields = ["host"]
        # Model can be either 'model' (for chat requests) or 'default_model' (for connection settings)
        has_model = any(field in settings and settings[field] for field in ["model", "default_model"])
        return all(field in settings and settings[field] for field in required_fields) and has_model
    
    async def send_message(self, request: ChatRequest) -> ChatResponse:
        """Send message to Ollama and get complete response."""
        if not self.validate_settings(request.provider_settings):
            raise ProviderConnectionError("Invalid Ollama settings: missing host or model")
        
        url = self.request_builder.build_url(
            request.provider_settings["host"],
            request.provider_settings.get("route")
        )
        
        # Force non-streaming for this method
        request_copy = ChatRequest(
            message=request.message,
            provider_type=request.provider_type,
            provider_settings=request.provider_settings,
            chat_controls={**request.chat_controls, "stream": False},
            system_prompt=request.system_prompt
        )
        
        payload = self.request_builder.build_request(request_copy)
        
        try:
            timeout = self._get_timeout()
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        error_msg = self._format_error_message(error_text, response.status)
                        raise ProviderConnectionError(error_msg)
                    
                    response_data = await response.json()
                    return self.response_parser.parse_response(response_data)
        
        except ClientConnectorError as e:
            logger.error(f"Failed to connect to Ollama: {e}")
            raise ProviderConnectionError(f"Failed to connect to Ollama at {url}: {str(e)}")
        except ClientError as e:
            logger.error(f"Ollama client error: {e}")
            raise ProviderConnectionError(f"Ollama client error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error communicating with Ollama: {e}")
            raise ProviderConnectionError(f"Unexpected error: {str(e)}")
    
    async def send_message_stream(self, request: ChatRequest) -> AsyncIterator[StreamingChatResponse]:
        """Send message to Ollama and get streaming response."""
        if not self.validate_settings(request.provider_settings):
            raise ProviderConnectionError("Invalid Ollama settings: missing host or model")
        
        url = self.request_builder.build_url(
            request.provider_settings["host"],
            request.provider_settings.get("route")
        )
        
        # Force streaming for this method
        request_copy = ChatRequest(
            message=request.message,
            provider_type=request.provider_type,
            provider_settings=request.provider_settings,
            chat_controls={**request.chat_controls, "stream": True},
            system_prompt=request.system_prompt
        )
        
        payload = self.request_builder.build_request(request_copy)
        
        try:
            timeout = self._get_timeout()
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        error_msg = self._format_error_message(error_text, response.status)
                        raise ProviderConnectionError(error_msg)
                    
                    async for chunk in response.content.iter_chunked(8192):
                        if chunk:
                            # Split chunk by newlines and process each JSON line
                            lines = chunk.decode('utf-8').strip().split('\n')
                            for line in lines:
                                if line.strip():
                                    try:
                                        chunk_data = json.loads(line)
                                        yield self.stream_parser.parse_chunk(chunk_data)
                                    except json.JSONDecodeError:
                                        # Skip invalid JSON lines
                                        continue
        
        except ClientConnectorError as e:
            logger.error(f"Failed to connect to Ollama: {e}")
            raise ProviderConnectionError(f"Failed to connect to Ollama at {url}: {str(e)}")
        except ClientError as e:
            logger.error(f"Ollama client error: {e}")
            raise ProviderConnectionError(f"Ollama client error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error communicating with Ollama: {e}")
            raise ProviderConnectionError(f"Unexpected error: {str(e)}")
    
    def _get_timeout(self) -> ClientTimeout:
        """Get timeout configuration for requests."""
        return ClientTimeout(total=300)  # 5 minutes
    
    def _format_error_message(self, error_text: str, status_code: int) -> str:
        """Format error message for better user experience."""
        return f"Ollama request failed with status {status_code}: {error_text}"
    
    async def test_connection(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Test connection to Ollama server."""
        if not self.validate_settings(settings):
            raise ProviderConnectionError("Invalid Ollama settings: missing host or model")
        
        url = self.request_builder.build_url(settings["host"], settings.get("route"))
        
        # Get model from either 'model' or 'default_model' field  
        model = settings.get("model") or settings.get("default_model")
        
        # Create a minimal test request
        test_payload = {
            "model": model,
            "messages": [{"role": "user", "content": "test"}],
            "stream": False,
            "options": {"num_predict": 1}  # Minimal response
        }
        
        try:
            timeout = ClientTimeout(total=30)  # Shorter timeout for connection test
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, json=test_payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        error_msg = self._format_error_message(error_text, response.status)
                        raise ProviderConnectionError(error_msg)
                    
                    response_data = await response.json()
                    
                    return {
                        "status": "success",
                        "message": f"Successfully connected to Ollama at {settings['host']}",
                        "model": response_data.get("model", model),
                        "version": response_data.get("version", "unknown")
                    }
        
        except ClientConnectorError as e:
            logger.error(f"Failed to connect to Ollama: {e}")
            raise ProviderConnectionError(f"Failed to connect to Ollama at {settings['host']}: {str(e)}")
        except ClientError as e:
            logger.error(f"Ollama client error: {e}")
            raise ProviderConnectionError(f"Ollama client error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error testing Ollama connection: {e}")
            raise ProviderConnectionError(f"Unexpected error: {str(e)}")
    
    async def list_models(self, settings: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        List available models from Ollama using the /v1/models endpoint.
        
        Args:
            settings: Optional connection settings (uses default host if not provided)
            
        Returns:
            List of model information dicts
            
        Raises:
            ProviderConnectionError: If connection fails
        """
        # Use provided settings or get from default connection
        host = settings.get("host", "http://localhost:11434") if settings else "http://localhost:11434"
        url = urljoin(host, "/v1/models")
        
        try:
            timeout = ClientTimeout(total=30)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        error_msg = self._format_error_message(error_text, response.status)
                        raise ProviderConnectionError(f"Failed to fetch models: {error_msg}")
                    
                    response_data = await response.json()
                    
                    # Ollama /v1/models returns OpenAI-compatible format
                    models = response_data.get("data", [])
                    
                    # Ensure consistent format for frontend
                    formatted_models = []
                    for model in models:
                        formatted_models.append({
                            "id": model.get("id", ""),
                            "name": model.get("id", ""),  # Use id as name for Ollama
                            "object": model.get("object", "model"),
                            "created": model.get("created", 0),
                            "owned_by": model.get("owned_by", "ollama")
                        })
                    
                    return formatted_models
        
        except ClientConnectorError as e:
            logger.error(f"Failed to connect to Ollama models endpoint: {e}")
            raise ProviderConnectionError(f"Failed to connect to Ollama at {host}: {str(e)}")
        except ClientError as e:
            logger.error(f"Ollama models client error: {e}")
            raise ProviderConnectionError(f"Ollama client error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error fetching Ollama models: {e}")
            raise ProviderConnectionError(f"Unexpected error: {str(e)}")