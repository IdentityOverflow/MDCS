"""
OpenAI-API compatible response parsing logic extracted from openai_service_base.py.
"""

import json
import logging
from typing import Optional, Dict, Any

from ...ai_providers import ChatResponse, StreamingChatResponse, ProviderType
from .models import OpenAIResponse, OpenAIStreamChunk, OpenAIChoice, OpenAIDelta

logger = logging.getLogger(__name__)


class ThinkingExtractor:
    """
    Utility for extracting thinking/reasoning content from OpenAI-API responses.
    
    Extracted from the original ThinkingExtractor class in openai_service_base.py.
    Handles multiple locations where thinking content might appear.
    """
    
    @staticmethod
    def extract_from_choice(choice: OpenAIChoice) -> Optional[str]:
        """
        Extract thinking content from a choice object.
        
        Args:
            choice: OpenAI choice object that might contain thinking content
            
        Returns:
            Thinking content string or None if not found
        """
        # Check choice.reasoning first (some models)
        if hasattr(choice, 'reasoning') and choice.reasoning:
            return choice.reasoning
        
        # Check choice.message.reasoning (other models)
        if choice.message and hasattr(choice.message, 'reasoning') and choice.message.reasoning:
            return choice.message.reasoning
        
        return None
    
    @staticmethod
    def extract_from_delta(delta: OpenAIDelta) -> Optional[str]:
        """
        Extract thinking content from a streaming delta object.
        
        Args:
            delta: OpenAI delta object that might contain thinking content
            
        Returns:
            Thinking content string or None if not found
        """
        if hasattr(delta, 'reasoning') and delta.reasoning:
            return delta.reasoning
        
        return None


class OpenAIResponseParser:
    """
    Parses OpenAI-API compatible non-streaming responses.
    
    Extracted from the original OpenAIResponseParser class in openai_service_base.py.
    """
    
    def parse_response(self, response_data: Dict[str, Any]) -> ChatResponse:
        """
        Parse OpenAI-API non-streaming response into ChatResponse.
        
        Args:
            response_data: Raw JSON response from OpenAI-API compatible service
            
        Returns:
            ChatResponse object with parsed content
            
        Raises:
            ValueError: If required response fields are missing
        """
        try:
            openai_response = OpenAIResponse(**response_data)
        except Exception as e:
            raise ValueError(f"Invalid OpenAI-API response format: {e}")
        
        # Get the first choice (most common case)
        if not openai_response.choices:
            raise ValueError("OpenAI-API response contains no choices")
        
        choice = openai_response.choices[0]
        if not choice.message or not choice.message.content:
            raise ValueError("OpenAI-API response missing message content")
        
        content = choice.message.content
        
        # Extract thinking content if present
        thinking = ThinkingExtractor.extract_from_choice(choice)
        
        # Build metadata
        metadata = {
            "id": openai_response.id,
            "created": openai_response.created,
            "finish_reason": choice.finish_reason,
            "choice_index": choice.index
        }
        
        # Add usage information if available
        if openai_response.usage:
            metadata["usage"] = {
                "prompt_tokens": openai_response.usage.prompt_tokens,
                "completion_tokens": openai_response.usage.completion_tokens,
                "total_tokens": openai_response.usage.total_tokens
            }
            
            # Add detailed usage if available
            if openai_response.usage.completion_tokens_details:
                metadata["usage"]["completion_tokens_details"] = openai_response.usage.completion_tokens_details
            if openai_response.usage.prompt_tokens_details:
                metadata["usage"]["prompt_tokens_details"] = openai_response.usage.prompt_tokens_details
        
        # Add system fingerprint if available
        if openai_response.system_fingerprint:
            metadata["system_fingerprint"] = openai_response.system_fingerprint
        
        return ChatResponse(
            content=content,
            model=openai_response.model,
            provider_type=ProviderType.OPENAI,
            metadata=metadata,
            thinking=thinking
        )


class OpenAIStreamParser:
    """
    Parses OpenAI-API compatible streaming responses.
    
    Extracted from the original OpenAIStreamParser class in openai_service_base.py.
    """
    
    def parse_chunk(self, chunk_line: str) -> Optional[StreamingChatResponse]:
        """
        Parse a single streaming chunk from OpenAI-API.

        Args:
            chunk_line: Single line from the streaming response

        Returns:
            StreamingChatResponse or None if chunk should be skipped
        """
        # Handle Server-Sent Events format
        line = chunk_line.strip()
        if line.startswith('data: '):
            line = line[6:]  # Remove "data: " prefix

        # Skip control messages
        if line in ['[DONE]', '']:
            return None

        try:
            chunk_data = json.loads(line)
        except json.JSONDecodeError as e:
            # Log the actual line content to debug buffering issues
            logger.warning(f"Failed to parse OpenAI-API chunk as JSON: {e}. Line content: '{line[:100]}'")
            return None
        
        try:
            openai_chunk = OpenAIStreamChunk(**chunk_data)
        except Exception as e:
            logger.warning(f"Invalid OpenAI-API chunk format: {e}")
            return None
        
        # Get the first choice (most common case)
        if not openai_chunk.choices:
            return None

        choice = openai_chunk.choices[0]

        # Handle both delta (standard streaming) and message (final chunk in some APIs)
        content = ""
        thinking = None

        if choice.delta:
            # Standard streaming chunk with delta
            content = choice.delta.content or ""
            thinking = ThinkingExtractor.extract_from_delta(choice.delta)
        elif choice.message:
            # Final chunk with message instead of delta (some OpenAI-compatible APIs)
            content = choice.message.content or ""
            thinking = choice.message.reasoning if hasattr(choice.message, 'reasoning') else None
        else:
            # No delta or message - skip this chunk
            return None
        
        # Determine if this is the final chunk
        done = choice.finish_reason is not None
        
        # Build metadata
        metadata = {
            "id": openai_chunk.id,
            "created": openai_chunk.created,
            "choice_index": choice.index
        }
        
        # Add finish reason if present
        if choice.finish_reason:
            metadata["finish_reason"] = choice.finish_reason
        
        # Add usage information if available (typically only in final chunk)
        if openai_chunk.usage:
            metadata["usage"] = {
                "prompt_tokens": openai_chunk.usage.prompt_tokens,
                "completion_tokens": openai_chunk.usage.completion_tokens,
                "total_tokens": openai_chunk.usage.total_tokens
            }
        
        # Add system fingerprint if available
        if openai_chunk.system_fingerprint:
            metadata["system_fingerprint"] = openai_chunk.system_fingerprint
        
        return StreamingChatResponse(
            content=content,
            done=done,
            model=openai_chunk.model,
            provider_type=ProviderType.OPENAI,
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
            if line.startswith('data: '):
                line = line[6:]  # Remove Server-Sent Events prefix
            
            if line in ['[DONE]', '']:
                return None
                
            return json.loads(line)
        except json.JSONDecodeError:
            return None