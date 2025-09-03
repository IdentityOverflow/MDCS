"""
OpenAI service implementation for AI chat functionality.
"""

import json
import logging
from typing import Dict, Any, List, AsyncIterator, Optional

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


class OpenAIRequestBuilder:
    """Builds OpenAI API requests from chat requests."""
    
    def __init__(self, service: 'OpenAIService'):
        """Initialize with reference to parent service for base methods."""
        self.service = service
    
    def build_request(self, request: ChatRequest) -> Dict[str, Any]:
        """Build OpenAI API request payload."""
        # Use selected model from provider settings, falling back to default_model
        model_name = request.provider_settings.get("model") or request.provider_settings.get("default_model")
        
        # Start with basic request structure
        openai_request = {
            "model": model_name,
            "messages": self._build_messages(request),
            "stream": self._get_stream_setting(request)
        }
        
        # Add optional parameters
        self._add_optional_params(openai_request, request.chat_controls)
        
        return openai_request
    
    def _build_messages(self, request: ChatRequest) -> List[Dict[str, str]]:
        """Build messages array for OpenAI using base implementation."""
        return self.service._build_base_messages(request)
    
    def _get_stream_setting(self, request: ChatRequest) -> bool:
        """Get streaming setting from request."""
        return request.chat_controls.get("stream", False)
    
    def _add_optional_params(self, request_dict: Dict[str, Any], chat_controls: Dict[str, Any]):
        """Add optional parameters to the request."""
        thinking_enabled = chat_controls.get("thinking_enabled", False)
        
        # Always try to add standard parameters first
        if "temperature" in chat_controls and chat_controls["temperature"] is not None:
            request_dict["temperature"] = chat_controls["temperature"]
        if "top_p" in chat_controls and chat_controls["top_p"] is not None:
            request_dict["top_p"] = chat_controls["top_p"]
        if "presence_penalty" in chat_controls and chat_controls["presence_penalty"] is not None:
            request_dict["presence_penalty"] = chat_controls["presence_penalty"]
        if "frequency_penalty" in chat_controls and chat_controls["frequency_penalty"] is not None:
            request_dict["frequency_penalty"] = chat_controls["frequency_penalty"]
        
        # Handle max_tokens - some reasoning models prefer max_completion_tokens
        if "max_tokens" in chat_controls and chat_controls["max_tokens"] is not None:
            max_tokens = chat_controls["max_tokens"]
            # Try both parameter names - the API will use whichever it supports
            request_dict["max_tokens"] = max_tokens
            if thinking_enabled:
                # Also add max_completion_tokens for reasoning models that prefer it
                request_dict["max_completion_tokens"] = max_tokens
        
        # Add reasoning-specific parameters when thinking is enabled
        if thinking_enabled:
            # Add reasoning effort parameter if specified
            if "reasoning_effort" in chat_controls and chat_controls["reasoning_effort"]:
                effort = chat_controls["reasoning_effort"]
                if effort in ["low", "medium", "high"]:
                    request_dict["reasoning_effort"] = effort
        
        # Common parameters for all models
        if "seed" in chat_controls and chat_controls["seed"] is not None:
            request_dict["seed"] = chat_controls["seed"]
        if "stop" in chat_controls and chat_controls["stop"]:
            request_dict["stop"] = chat_controls["stop"]
        
        # JSON mode - try to add it, let the API decide if it's supported
        json_mode = chat_controls.get("json_mode")
        if json_mode == "json_object":
            request_dict["response_format"] = {"type": "json_object"}
        elif json_mode == "json_schema":
            # For now, just use json_object mode
            request_dict["response_format"] = {"type": "json_object"}
        
        # Tool usage - try to add it, let the API decide if it's supported
        if "tools" in chat_controls and chat_controls["tools"]:
            request_dict["tools"] = chat_controls["tools"]
        if "tool_choice" in chat_controls and chat_controls["tool_choice"]:
            request_dict["tool_choice"] = chat_controls["tool_choice"]
    
    def build_headers(self, api_key: str, organization: Optional[str], project: Optional[str]) -> Dict[str, str]:
        """Build headers for OpenAI API request."""
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        if organization:
            headers["OpenAI-Organization"] = organization
        if project:
            headers["OpenAI-Project"] = project
        
        return headers
    
    def build_url(self, base_url: str) -> str:
        """Build the full URL for OpenAI API."""
        # Remove trailing slash from base_url
        base_url = base_url.rstrip('/')
        return f"{base_url}/chat/completions"


class ThinkingExtractor:
    """Utility class for extracting thinking/reasoning content from API responses."""
    
    @staticmethod
    def extract_from_choice(choice: Dict[str, Any]) -> Optional[str]:
        """
        Extract thinking/reasoning content from a choice object.
        
        Tries various common locations where reasoning models might store thinking content.
        """
        # Try message.reasoning (common in OpenAI reasoning models)
        if "message" in choice and isinstance(choice["message"], dict):
            message = choice["message"]
            if "reasoning" in message and message["reasoning"]:
                return str(message["reasoning"])
            if "thinking" in message and message["thinking"]:
                return str(message["thinking"])
        
        # Try choice.reasoning (alternative location)
        if "reasoning" in choice and choice["reasoning"]:
            return str(choice["reasoning"])
        
        # Try choice.thinking (alternative location)
        if "thinking" in choice and choice["thinking"]:
            return str(choice["thinking"])
        
        return None
    
    @staticmethod
    def extract_from_delta(delta: Dict[str, Any]) -> str:
        """
        Extract thinking content from a delta object in streaming responses.
        """
        # Try delta.reasoning (common in streaming reasoning responses)
        if "reasoning" in delta and delta["reasoning"]:
            return str(delta["reasoning"])
        
        # Try delta.thinking (alternative location)
        if "thinking" in delta and delta["thinking"]:
            return str(delta["thinking"])
        
        return ""


class OpenAIResponseParser:
    """Parses OpenAI API responses."""
    
    def parse_response(self, response_data: Dict[str, Any]) -> ChatResponse:
        """Parse non-streaming OpenAI response."""
        content = ""
        finish_reason = None
        thinking = None
        
        if "choices" in response_data and response_data["choices"]:
            choice = response_data["choices"][0]
            if "message" in choice and "content" in choice["message"]:
                content = choice["message"]["content"] or ""
            if "finish_reason" in choice:
                finish_reason = choice["finish_reason"]
            
            # Try to extract thinking/reasoning content from various possible locations
            thinking = ThinkingExtractor.extract_from_choice(choice)
        
        # Extract metadata
        metadata = {}
        if "usage" in response_data:
            metadata["usage"] = response_data["usage"]
        if finish_reason:
            metadata["finish_reason"] = finish_reason
        if "id" in response_data:
            metadata["id"] = response_data["id"]
        
        return ChatResponse(
            content=content,
            model=response_data.get("model", "unknown"),
            provider_type=ProviderType.OPENAI,
            metadata=metadata,
            thinking=thinking
        )


class OpenAIStreamParser:
    """Parses OpenAI streaming responses."""
    
    def parse_chunk(self, chunk_line: str) -> Optional[StreamingChatResponse]:
        """Parse individual streaming chunk."""
        # Remove 'data: ' prefix and whitespace
        if not chunk_line.startswith("data: "):
            return None
        
        data_part = chunk_line[6:].strip()
        
        # Handle [DONE] message
        if data_part == "[DONE]":
            return None
        
        # Skip empty lines
        if not data_part:
            return None
        
        try:
            chunk_data = json.loads(data_part)
        except json.JSONDecodeError:
            return None
        
        content = ""
        thinking = ""
        finish_reason = None
        done = False
        
        if "choices" in chunk_data and chunk_data["choices"]:
            choice = chunk_data["choices"][0]
            if "delta" in choice:
                delta = choice["delta"]
                # Extract content
                if "content" in delta:
                    content = delta["content"] or ""
                
                # Extract thinking content from delta (for streaming thinking)
                thinking = ThinkingExtractor.extract_from_delta(delta)
            
            if "finish_reason" in choice and choice["finish_reason"]:
                finish_reason = choice["finish_reason"]
                done = True
        
        # Extract metadata for final chunk
        metadata = {}
        if done:
            if finish_reason:
                metadata["finish_reason"] = finish_reason
            if "usage" in chunk_data:
                metadata["usage"] = chunk_data["usage"]
            if "id" in chunk_data:
                metadata["id"] = chunk_data["id"]
        
        return StreamingChatResponse(
            content=content,
            done=done,
            model=chunk_data.get("model", "unknown"),
            provider_type=ProviderType.OPENAI,
            metadata=metadata,
            thinking=thinking if thinking else None
        )


class OpenAIService(AIProvider):
    """OpenAI AI provider implementation."""
    
    def __init__(self):
        self.request_builder = OpenAIRequestBuilder(self)
        self.response_parser = OpenAIResponseParser()
        self.stream_parser = OpenAIStreamParser()
    
    def validate_settings(self, settings: Dict[str, Any], require_model: bool = True) -> bool:
        """Validate OpenAI-specific settings."""
        base_fields = ["base_url", "api_key"]
        required_fields = base_fields + (["default_model"] if require_model else [])
        return all(field in settings and settings[field] for field in required_fields)
    
    async def send_message(self, request: ChatRequest) -> ChatResponse:
        """Send message to OpenAI and get complete response."""
        if not self.validate_settings(request.provider_settings):
            raise ProviderConnectionError("Invalid OpenAI settings: missing required fields")
        
        url = self.request_builder.build_url(request.provider_settings["base_url"])
        headers = self.request_builder.build_headers(
            request.provider_settings["api_key"],
            request.provider_settings.get("organization"),
            request.provider_settings.get("project")
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
                async with session.post(url, json=payload, headers=headers) as response:
                    response_text = await response.text()
                    
                    if response.status == 401:
                        raise ProviderAuthenticationError(f"OpenAI authentication failed: {response_text}")
                    elif response.status != 200:
                        error_msg = self._format_error_message(response_text, response.status)
                        raise ProviderConnectionError(error_msg)
                    
                    response_data = json.loads(response_text)
                    parsed_response = self.response_parser.parse_response(response_data)
                    
                    # Add debug information - actual API request payload and response
                    parsed_response.metadata["debug_api_request"] = payload
                    parsed_response.metadata["debug_api_response"] = response_data
                    parsed_response.metadata["debug_api_url"] = url
                    
                    return parsed_response
        
        except ClientConnectorError as e:
            logger.error(f"Failed to connect to OpenAI: {e}")
            raise ProviderConnectionError(f"Failed to connect to OpenAI at {url}: {str(e)}")
        except ClientError as e:
            logger.error(f"OpenAI client error: {e}")
            raise ProviderConnectionError(f"OpenAI client error: {str(e)}")
        except ProviderAuthenticationError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error communicating with OpenAI: {e}")
            raise ProviderConnectionError(f"Unexpected error: {str(e)}")
    
    async def send_message_stream(self, request: ChatRequest) -> AsyncIterator[StreamingChatResponse]:
        """Send message to OpenAI and get streaming response."""
        if not self.validate_settings(request.provider_settings):
            raise ProviderConnectionError("Invalid OpenAI settings: missing required fields")
        
        url = self.request_builder.build_url(request.provider_settings["base_url"])
        headers = self.request_builder.build_headers(
            request.provider_settings["api_key"],
            request.provider_settings.get("organization"),
            request.provider_settings.get("project")
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
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status == 401:
                        response_text = await response.text()
                        raise ProviderAuthenticationError(f"OpenAI authentication failed: {response_text}")
                    elif response.status != 200:
                        response_text = await response.text()
                        error_msg = self._format_error_message(response_text, response.status)
                        raise ProviderConnectionError(error_msg)
                    
                    async for chunk in response.content.iter_chunked(8192):
                        if chunk:
                            # Decode chunk and split by lines
                            lines = chunk.decode('utf-8').strip().split('\n')
                            for line in lines:
                                line = line.strip()
                                if line:
                                    parsed_chunk = self.stream_parser.parse_chunk(line)
                                    if parsed_chunk:
                                        # Add debug information to the final chunk
                                        if parsed_chunk.done:
                                            parsed_chunk.metadata["debug_api_request"] = payload
                                            # Parse the line to get the actual response data
                                            if line.startswith("data: ") and not line[6:].strip() == "[DONE]":
                                                try:
                                                    chunk_data = json.loads(line[6:].strip())
                                                    parsed_chunk.metadata["debug_api_response"] = chunk_data
                                                except json.JSONDecodeError:
                                                    parsed_chunk.metadata["debug_api_response"] = {"raw_line": line}
                                            else:
                                                parsed_chunk.metadata["debug_api_response"] = {"raw_line": line}
                                            parsed_chunk.metadata["debug_api_url"] = url
                                        
                                        yield parsed_chunk
        
        except ClientConnectorError as e:
            logger.error(f"Failed to connect to OpenAI: {e}")
            raise ProviderConnectionError(f"Failed to connect to OpenAI at {url}: {str(e)}")
        except ClientError as e:
            logger.error(f"OpenAI client error: {e}")
            raise ProviderConnectionError(f"OpenAI client error: {str(e)}")
        except ProviderAuthenticationError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error communicating with OpenAI: {e}")
            raise ProviderConnectionError(f"Unexpected error: {str(e)}")
    
    def _get_timeout(self) -> ClientTimeout:
        """Get timeout configuration for requests."""
        return ClientTimeout(total=60)  # 1 minute for OpenAI
    
    def _format_error_message(self, error_text: str, status_code: int) -> str:
        """Format error message for better user experience."""
        return f"OpenAI request failed with status {status_code}: {error_text}"
    
    async def test_connection(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Test connection to OpenAI API."""
        if not self.validate_settings(settings):
            raise ProviderConnectionError("Invalid OpenAI settings: missing required fields")
        
        url = self.request_builder.build_url(settings["base_url"])
        headers = self.request_builder.build_headers(
            settings["api_key"],
            settings.get("organization"),
            settings.get("project")
        )
        
        # Create a minimal test request
        test_payload = {
            "model": settings["default_model"],
            "messages": [{"role": "user", "content": "test"}],
            "stream": False,
            "max_tokens": 1  # Minimal response
        }
        
        try:
            timeout = ClientTimeout(total=30)  # Shorter timeout for connection test
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, json=test_payload, headers=headers) as response:
                    response_text = await response.text()
                    
                    if response.status == 401:
                        raise ProviderAuthenticationError(f"OpenAI authentication failed: Invalid API key")
                    elif response.status != 200:
                        error_msg = self._format_error_message(response_text, response.status)
                        raise ProviderConnectionError(error_msg)
                    
                    response_data = json.loads(response_text)
                    
                    return {
                        "status": "success",
                        "message": f"Successfully connected to OpenAI API at {settings['base_url']}",
                        "model": response_data.get("model", settings["default_model"]),
                        "organization": settings.get("organization", "default")
                    }
        
        except ClientConnectorError as e:
            logger.error(f"Failed to connect to OpenAI: {e}")
            raise ProviderConnectionError(f"Failed to connect to OpenAI at {settings['base_url']}: {str(e)}")
        except ClientError as e:
            logger.error(f"OpenAI client error: {e}")
            raise ProviderConnectionError(f"OpenAI client error: {str(e)}")
        except ProviderAuthenticationError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error testing OpenAI connection: {e}")
            raise ProviderConnectionError(f"Unexpected error: {str(e)}")
    
    async def list_models(self, settings: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        List available models from OpenAI using the /v1/models endpoint.
        
        Args:
            settings: Connection settings with base_url and api_key
            
        Returns:
            List of model information dicts
            
        Raises:
            ProviderConnectionError: If connection fails
            ProviderAuthenticationError: If authentication fails
        """
        if not settings or not self.validate_settings(settings, require_model=False):
            raise ProviderConnectionError("Invalid OpenAI settings: missing required fields (base_url, api_key)")
        
        base_url = settings["base_url"].rstrip('/')
        url = f"{base_url}/models"
        
        headers = self.request_builder.build_headers(
            settings["api_key"],
            settings.get("organization"),
            settings.get("project")
        )
        
        logger.info(f"Fetching models from URL: {url}")
        logger.info(f"Using headers: {dict(headers)}")
        
        try:
            timeout = ClientTimeout(total=30)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers=headers) as response:
                    response_text = await response.text()
                    
                    logger.info(f"Models response status: {response.status}")
                    logger.info(f"Models response text (first 200 chars): {response_text[:200]}")
                    
                    if response.status == 401:
                        raise ProviderAuthenticationError(f"OpenAI authentication failed: Invalid API key")
                    elif response.status != 200:
                        error_msg = self._format_error_message(response_text, response.status)
                        raise ProviderConnectionError(f"Failed to fetch models: {error_msg}")
                    
                    # Better JSON parsing with error handling
                    if not response_text.strip():
                        raise ProviderConnectionError("Empty response from models endpoint")
                    
                    try:
                        response_data = json.loads(response_text)
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse models response as JSON: {response_text[:200]}...")
                        raise ProviderConnectionError(f"Invalid JSON response from models endpoint: {str(e)}")
                    
                    # Check if response contains an error (like OpenRouter error format)
                    if "error" in response_data:
                        error_info = response_data["error"]
                        if isinstance(error_info, dict):
                            error_message = error_info.get("message", "Unknown error")
                            error_code = error_info.get("code", "unknown")
                            if error_code == 401:
                                raise ProviderAuthenticationError(f"API authentication failed: {error_message}")
                            else:
                                raise ProviderConnectionError(f"API error ({error_code}): {error_message}")
                        else:
                            raise ProviderConnectionError(f"API error: {error_info}")
                    
                    # OpenAI returns data in standard format
                    models = response_data.get("data", [])
                    
                    # Ensure consistent format for frontend
                    formatted_models = []
                    for model in models:
                        formatted_models.append({
                            "id": model.get("id", ""),
                            "name": model.get("id", ""),  # Use id as name
                            "object": model.get("object", "model"),
                            "created": model.get("created", 0),
                            "owned_by": model.get("owned_by", "openai")
                        })
                    
                    return formatted_models
        
        except ClientConnectorError as e:
            logger.error(f"Failed to connect to OpenAI models endpoint: {e}")
            raise ProviderConnectionError(f"Failed to connect to OpenAI at {base_url}: {str(e)}")
        except ClientError as e:
            logger.error(f"OpenAI models client error: {e}")
            raise ProviderConnectionError(f"OpenAI client error: {str(e)}")
        except ProviderAuthenticationError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching OpenAI models: {e}")
            raise ProviderConnectionError(f"Unexpected error: {str(e)}")