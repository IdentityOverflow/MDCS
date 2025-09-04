"""
Ollama request building logic extracted from ollama_service_base.py.
"""

import logging
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin

from ...ai_providers import ChatRequest
from ...utils.validation import SettingsValidator
from .models import OllamaRequest, OllamaOptions

logger = logging.getLogger(__name__)


class OllamaRequestBuilder:
    """
    Builds Ollama API requests from ChatRequest objects.
    
    Extracted from the original OllamaRequestBuilder class in ollama_service_base.py.
    Focuses solely on request construction without HTTP concerns.
    """
    
    def build_request(self, request: ChatRequest) -> OllamaRequest:
        """
        Build Ollama API request payload from ChatRequest.
        
        Args:
            request: The ChatRequest to convert to Ollama format
            
        Returns:
            OllamaRequest object ready for JSON serialization
        """
        # Get model from either 'model' or 'default_model' field
        model = request.provider_settings.get("model") or request.provider_settings.get("default_model")
        
        # Build messages using shared base logic
        messages = self._build_messages(request)
        
        # Create the base request
        ollama_request = OllamaRequest(
            model=model,
            messages=messages,
            stream=self._get_stream_setting(request),
            options=self._build_options(request.chat_controls)
        )
        
        # Add optional fields
        if "keep_alive" in request.provider_settings:
            ollama_request.keep_alive = request.provider_settings["keep_alive"]
        
        format_setting = self._get_format_setting(request)
        if format_setting:
            ollama_request.format = format_setting
        
        # Add thinking support
        thinking_enabled = request.chat_controls.get("thinking_enabled", False)
        if thinking_enabled:
            ollama_request.think = True
            
        return ollama_request
    
    def build_url(self, base_url: str, endpoint: str = "api/chat") -> str:
        """
        Build the complete Ollama API URL.
        
        Args:
            base_url: Base Ollama server URL (e.g., "http://localhost:11434")
            endpoint: API endpoint (default: "api/chat")
            
        Returns:
            Complete URL for the API endpoint
        """
        base_url = SettingsValidator.normalize_url(base_url)
        return urljoin(base_url + "/", endpoint)
    
    def _build_messages(self, request: ChatRequest) -> List[Dict[str, str]]:
        """
        Build messages array for Ollama using standard format.
        
        Args:
            request: ChatRequest with message and system prompt
            
        Returns:
            List of message dictionaries in Ollama format
        """
        messages = []
        
        # Add system message if present
        system_message = request.system_prompt or request.chat_controls.get("system_or_instructions")
        
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
    
    def _get_format_setting(self, request: ChatRequest) -> Optional[str]:
        """
        Get format setting for JSON mode.
        
        Args:
            request: ChatRequest to extract format setting from
            
        Returns:
            Format string for Ollama or None
        """
        # Check provider settings first
        if "format" in request.provider_settings and request.provider_settings["format"]:
            return request.provider_settings["format"]
        
        # Check chat controls for JSON mode
        json_mode = request.chat_controls.get("json_mode")
        if json_mode in ["json_object", "json_schema"]:
            return "json"
        
        return None
    
    def _build_options(self, chat_controls: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build Ollama options object from chat controls.
        
        Args:
            chat_controls: Dictionary of chat control parameters
            
        Returns:
            Dictionary of Ollama-specific options
        """
        options = {}
        
        # Map standard parameters to Ollama format
        if "temperature" in chat_controls:
            options["temperature"] = chat_controls["temperature"]
        if "top_p" in chat_controls:
            options["top_p"] = chat_controls["top_p"]
        if "max_tokens" in chat_controls:
            options["num_predict"] = chat_controls["max_tokens"]  # Ollama uses num_predict
        if "top_k" in chat_controls:
            options["top_k"] = chat_controls["top_k"]
        if "repeat_penalty" in chat_controls:
            options["repeat_penalty"] = chat_controls["repeat_penalty"]
        if "seed" in chat_controls:
            options["seed"] = chat_controls["seed"]
        if "stop" in chat_controls:
            options["stop"] = chat_controls["stop"]
            
        # Map Ollama-specific parameters
        ollama_specific = [
            "tfs_z", "num_thread", "num_ctx", "num_batch", "num_gqa",
            "num_gpu", "main_gpu", "low_vram", "f16_kv", "logits_all",
            "vocab_only", "use_mmap", "use_mlock", "embedding_only",
            "rope_frequency_base", "rope_frequency_scale", "num_keep",
            "typical_p", "presence_penalty", "frequency_penalty",
            "mirostat", "mirostat_tau", "mirostat_eta", "penalize_newline", "numa"
        ]
        
        for param in ollama_specific:
            if param in chat_controls:
                options[param] = chat_controls[param]
        
        return options if options else None