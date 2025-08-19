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
    
    def build_request(self, request: ChatRequest) -> Dict[str, Any]:
        """Build Ollama API request payload."""
        # Start with basic request structure
        ollama_request = {
            "model": request.provider_settings["model"],
            "messages": self._build_messages(request),
            "stream": self._get_stream_setting(request),
            "options": self._build_options(request.chat_controls)
        }
        
        # Add optional fields
        if "keep_alive" in request.provider_settings:
            ollama_request["keep_alive"] = request.provider_settings["keep_alive"]
        
        format_setting = self._get_format_setting(request)
        if format_setting:
            ollama_request["format"] = format_setting
        
        return ollama_request
    
    def _build_messages(self, request: ChatRequest) -> List[Dict[str, str]]:
        """Build messages array for Ollama."""
        messages = []
        
        # Add system message if present
        system_message = request.chat_controls.get("system_or_instructions")
        if system_message:
            messages.append({
                "role": "system",
                "content": system_message
            })
        
        # Add user message
        messages.append({
            "role": "user",
            "content": request.message
        })
        
        return messages
    
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
        content = ""
        if "message" in response_data and "content" in response_data["message"]:
            content = response_data["message"]["content"]
        
        # Extract metadata
        metadata = {}
        for field in ["total_duration", "load_duration", "prompt_eval_count", "eval_count"]:
            if field in response_data:
                metadata[field] = response_data[field]
        
        return ChatResponse(
            content=content,
            model=response_data.get("model", "unknown"),
            provider_type=ProviderType.OLLAMA,
            metadata=metadata
        )


class OllamaStreamParser:
    """Parses Ollama streaming responses."""
    
    def parse_chunk(self, chunk_data: Dict[str, Any]) -> StreamingChatResponse:
        """Parse individual streaming chunk."""
        content = ""
        if "message" in chunk_data and "content" in chunk_data["message"]:
            content = chunk_data["message"]["content"]
        
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
            metadata=metadata
        )


class OllamaService(AIProvider):
    """Ollama AI provider implementation."""
    
    def __init__(self):
        self.request_builder = OllamaRequestBuilder()
        self.response_parser = OllamaResponseParser()
        self.stream_parser = OllamaStreamParser()
    
    def validate_settings(self, settings: Dict[str, Any]) -> bool:
        """Validate Ollama-specific settings."""
        required_fields = ["host", "model"]
        return all(field in settings and settings[field] for field in required_fields)
    
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
            chat_controls={**request.chat_controls, "stream": False}
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
            chat_controls={**request.chat_controls, "stream": True}
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