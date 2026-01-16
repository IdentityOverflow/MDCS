"""
OpenAI-API compatible request building logic extracted from openai_service_base.py.
"""

import logging
from typing import Dict, Any, List, Union, Optional
from urllib.parse import urljoin

from ...ai_providers import ChatRequest
from ...utils.validation import SettingsValidator
from .models import OpenAIRequest, OpenAIMessage, OpenAIResponseFormat

logger = logging.getLogger(__name__)


class OpenAIRequestBuilder:
    """
    Builds OpenAI-API compatible requests from ChatRequest objects.
    
    Extracted from the original OpenAIRequestBuilder class in openai_service_base.py.
    Works with any OpenAI-API compatible service (OpenAI, OpenRouter, Groq, etc.).
    """
    
    def build_request(self, request: ChatRequest) -> OpenAIRequest:
        """
        Build OpenAI-API compatible request payload from ChatRequest.
        
        Args:
            request: The ChatRequest to convert to OpenAI-API format
            
        Returns:
            OpenAIRequest object ready for JSON serialization
        """
        # Get model - prefer 'model' first, then fallback to 'default_model'
        model = request.provider_settings.get("model") or request.provider_settings.get("default_model")
        if not model:
            raise ValueError("Model must be specified in provider settings")
        
        # Build messages using base logic
        messages = self._build_messages(request)
        
        # Create base request
        openai_request = OpenAIRequest(
            model=model,
            messages=messages,
            stream=self._get_stream_setting(request)
        )
        
        # Add chat control parameters
        self._add_chat_controls(openai_request, request.chat_controls, model)
        
        return openai_request
    
    def build_headers(self, settings: Dict[str, Any]) -> Dict[str, str]:
        """
        Build OpenAI-API compatible headers including authentication.
        
        Args:
            settings: Provider settings containing API key and optional organization
            
        Returns:
            Dictionary of HTTP headers
        """
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {settings['api_key']}"
        }
        
        # Add optional organization header (if supported by the API)
        if "organization" in settings and settings["organization"]:
            headers["OpenAI-Organization"] = settings["organization"]
        
        # Add optional project header (if supported by the API)
        if "project" in settings and settings["project"]:
            headers["OpenAI-Project"] = settings["project"]
        
        return headers
    
    def build_url(self, base_url: str, endpoint: str = "chat/completions") -> str:
        """
        Build the complete OpenAI-API compatible URL.
        
        Args:
            base_url: Base API URL (e.g., "https://api.openai.com/v1", "https://openrouter.ai/api/v1")
            endpoint: API endpoint (default: "chat/completions")
            
        Returns:
            Complete URL for the API endpoint
        """
        base_url = SettingsValidator.normalize_url(base_url)
        return urljoin(base_url + "/", endpoint)
    
    def _build_messages(self, request: ChatRequest) -> List[OpenAIMessage]:
        """
        Build messages array for OpenAI-API format.
        
        Args:
            request: ChatRequest with message and system prompt
            
        Returns:
            List of OpenAIMessage objects
        """
        messages = []
        
        # Add system message if present
        system_message = request.system_prompt or request.chat_controls.get("system_or_instructions")
        
        if system_message:
            messages.append(OpenAIMessage(
                role="system",
                content=system_message
            ))
            logger.debug(f"Added system message with {len(system_message)} characters")
        else:
            logger.debug("No system message found in request")
        
        # Add message with specified role (default: "user")
        message_role = getattr(request, 'message_role', 'user')
        messages.append(OpenAIMessage(
            role=message_role,
            content=request.message
        ))
        
        return messages
    
    def _get_stream_setting(self, request: ChatRequest) -> bool:
        """
        Get streaming setting from request.
        
        Args:
            request: ChatRequest to extract streaming setting from
            
        Returns:
            True if streaming is enabled, False otherwise
        """
        # Check chat controls first, then provider settings
        if "stream" in request.chat_controls:
            return request.chat_controls["stream"]
        return request.provider_settings.get("stream", False)
    
    def _add_chat_controls(self, openai_request: OpenAIRequest, chat_controls: Dict[str, Any], model: str) -> None:
        """
        Add chat control parameters to OpenAI-API request.
        
        Args:
            openai_request: OpenAI request object to modify
            chat_controls: Dictionary of chat control parameters
            model: Model name for model-specific parameter handling
        """
        # Standard parameters
        if "temperature" in chat_controls:
            openai_request.temperature = chat_controls["temperature"]
        if "top_p" in chat_controls:
            openai_request.top_p = chat_controls["top_p"]
        if "presence_penalty" in chat_controls:
            openai_request.presence_penalty = chat_controls["presence_penalty"]
        if "frequency_penalty" in chat_controls:
            openai_request.frequency_penalty = chat_controls["frequency_penalty"]
        if "stop" in chat_controls:
            openai_request.stop = chat_controls["stop"]
        if "seed" in chat_controls:
            openai_request.seed = chat_controls["seed"]
        if "user" in chat_controls:
            openai_request.user = chat_controls["user"]
        if "n" in chat_controls:
            openai_request.n = chat_controls["n"]
        if "logit_bias" in chat_controls:
            openai_request.logit_bias = chat_controls["logit_bias"]
            
        # Token limits - handle both standard and reasoning models
        if "max_tokens" in chat_controls:
            if self._is_reasoning_model(model):
                # Reasoning models use max_completion_tokens
                openai_request.max_completion_tokens = chat_controls["max_tokens"]
            else:
                # Standard models use max_tokens
                openai_request.max_tokens = chat_controls["max_tokens"]
        
        # Reasoning model specific parameters (for models that support reasoning)
        if self._is_reasoning_model(model):
            if "reasoning_effort" in chat_controls:
                openai_request.reasoning_effort = chat_controls["reasoning_effort"]
        
        # JSON mode support
        json_mode = chat_controls.get("json_mode")
        if json_mode in ["json_object", "json_schema"]:
            openai_request.response_format = OpenAIResponseFormat(type=json_mode)
        
        # Tool parameters
        if "tools" in chat_controls:
            openai_request.tools = chat_controls["tools"]
        if "tool_choice" in chat_controls:
            openai_request.tool_choice = chat_controls["tool_choice"]
    
    def _is_reasoning_model(self, model: str) -> bool:
        """
        Check if model supports reasoning features.
        
        Args:
            model: Model name to check
            
        Returns:
            True if model supports reasoning features
        """
        # Check for reasoning model patterns (o1 series and similar)
        reasoning_patterns = ["o1-", "reasoning", "think"]
        return any(pattern in model.lower() for pattern in reasoning_patterns)