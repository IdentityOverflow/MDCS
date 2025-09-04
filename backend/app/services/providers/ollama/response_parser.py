"""
Ollama response parsing logic extracted from ollama_service_base.py.
"""

import json
import logging
from typing import Optional, Dict, Any

from ...ai_providers import ChatResponse, StreamingChatResponse, ProviderType
from .models import OllamaResponse, OllamaStreamChunk

logger = logging.getLogger(__name__)


class OllamaResponseParser:
    """
    Parses Ollama API non-streaming responses.
    
    Extracted from the original OllamaResponseParser class in ollama_service_base.py.
    """
    
    def parse_response(self, response_data: Dict[str, Any]) -> ChatResponse:
        """
        Parse Ollama non-streaming response into ChatResponse.
        
        Args:
            response_data: Raw JSON response from Ollama API
            
        Returns:
            ChatResponse object with parsed content
            
        Raises:
            ValueError: If required response fields are missing
        """
        try:
            ollama_response = OllamaResponse(**response_data)
        except Exception as e:
            raise ValueError(f"Invalid Ollama response format: {e}")
        
        # Extract content from message
        if not ollama_response.message or "content" not in ollama_response.message:
            raise ValueError("Ollama response missing message content")
        
        content = ollama_response.message["content"]
        
        # Extract thinking content if present
        thinking = None
        if "thinking" in ollama_response.message:
            thinking = ollama_response.message["thinking"]
        
        # Build metadata
        metadata = {
            "created_at": ollama_response.created_at,
            "done": ollama_response.done
        }
        
        # Add performance metrics if available
        if ollama_response.total_duration:
            metadata["total_duration"] = ollama_response.total_duration
        if ollama_response.load_duration:
            metadata["load_duration"] = ollama_response.load_duration
        if ollama_response.prompt_eval_count:
            metadata["prompt_eval_count"] = ollama_response.prompt_eval_count
        if ollama_response.prompt_eval_duration:
            metadata["prompt_eval_duration"] = ollama_response.prompt_eval_duration
        if ollama_response.eval_count:
            metadata["eval_count"] = ollama_response.eval_count
        if ollama_response.eval_duration:
            metadata["eval_duration"] = ollama_response.eval_duration
        
        return ChatResponse(
            content=content,
            model=ollama_response.model,
            provider_type=ProviderType.OLLAMA,
            metadata=metadata,
            thinking=thinking
        )


class OllamaStreamParser:
    """
    Parses Ollama API streaming responses.
    
    Extracted from the original OllamaStreamParser class in ollama_service_base.py.
    """
    
    def parse_chunk(self, chunk_line: str) -> Optional[StreamingChatResponse]:
        """
        Parse a single streaming chunk from Ollama.
        
        Args:
            chunk_line: Single line of JSON from the streaming response
            
        Returns:
            StreamingChatResponse or None if chunk should be skipped
        """
        try:
            chunk_data = json.loads(chunk_line.strip())
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse Ollama chunk as JSON: {e}")
            return None
        
        try:
            ollama_chunk = OllamaStreamChunk(**chunk_data)
        except Exception as e:
            logger.warning(f"Invalid Ollama chunk format: {e}")
            return None
        
        # Extract content from message
        content = ""
        thinking = None
        
        if ollama_chunk.message:
            content = ollama_chunk.message.get("content", "")
            thinking = ollama_chunk.message.get("thinking")
        
        # Build metadata
        metadata = {
            "created_at": ollama_chunk.created_at,
        }
        
        # Add performance metrics if available (typically only in final chunk)
        if ollama_chunk.total_duration:
            metadata["total_duration"] = ollama_chunk.total_duration
        if ollama_chunk.load_duration:
            metadata["load_duration"] = ollama_chunk.load_duration
        if ollama_chunk.prompt_eval_count:
            metadata["prompt_eval_count"] = ollama_chunk.prompt_eval_count
        if ollama_chunk.prompt_eval_duration:
            metadata["prompt_eval_duration"] = ollama_chunk.prompt_eval_duration
        if ollama_chunk.eval_count:
            metadata["eval_count"] = ollama_chunk.eval_count
        if ollama_chunk.eval_duration:
            metadata["eval_duration"] = ollama_chunk.eval_duration
        
        return StreamingChatResponse(
            content=content,
            done=ollama_chunk.done,
            model=ollama_chunk.model,
            provider_type=ProviderType.OLLAMA,
            metadata=metadata,
            thinking=thinking
        )
    
    def parse_json_line(self, line: str) -> Optional[Dict[str, Any]]:
        """
        Helper method to safely parse JSON from a streaming line.
        
        Args:
            line: String that should contain JSON
            
        Returns:
            Parsed JSON dictionary or None if parsing fails
        """
        try:
            line = line.strip()
            if not line:
                return None
            return json.loads(line)
        except json.JSONDecodeError:
            return None