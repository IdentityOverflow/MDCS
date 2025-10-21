"""
Shared streaming response processing logic for AI providers.

This module eliminates the duplicate streaming logic found across
ollama_service_base.py and openai_service_base.py.
"""

import asyncio
import json
import logging
from typing import AsyncIterator, Optional, Callable, Any, Dict

from app.services.ai_providers import StreamingChatResponse
from app.services.cancellation_token import CancellationToken

logger = logging.getLogger(__name__)


class BaseStreamProcessor:
    """
    Shared streaming response processing logic with cancellation support.

    Eliminates ~120 lines of duplicate streaming code across provider base classes.
    Provides consistent chunk parsing, error handling, and response formatting.
    """

    def __init__(
        self,
        chunk_parser: Callable[[str], Optional[StreamingChatResponse]],
        cancellation_check_interval: int = 1
    ):
        """
        Initialize stream processor with provider-specific chunk parser.

        Args:
            chunk_parser: Function to parse individual chunks into StreamingChatResponse
                         Should return None for chunks that should be skipped
            cancellation_check_interval: Check for cancellation every N chunks (default 1 for immediate response)
        """
        self.chunk_parser = chunk_parser
        self.cancellation_check_interval = cancellation_check_interval

    async def process_stream(
        self,
        chunk_iterator: AsyncIterator[bytes],
        cancellation_token: Optional[CancellationToken] = None
    ) -> AsyncIterator[StreamingChatResponse]:
        """
        Process streaming chunks with provider-specific parsing and cancellation support.

        Args:
            chunk_iterator: Async iterator of raw bytes from HTTP stream
            cancellation_token: Optional token for cancellation support

        Yields:
            StreamingChatResponse objects from successfully parsed chunks

        Raises:
            asyncio.CancelledError: If cancellation token is cancelled during streaming

        Note:
            Failed chunk parsing is logged as warnings but doesn't stop the stream.
            Empty or invalid chunks are automatically filtered out.
            Cancellation is checked every N chunks (configurable).
        """
        chunk_count = 0

        async for chunk in chunk_iterator:
            # Check for cancellation every N chunks
            if cancellation_token and chunk_count % self.cancellation_check_interval == 0:
                cancellation_token.check_cancelled()

            if not chunk:
                continue

            try:
                # Decode bytes to string and split into lines
                chunk_text = chunk.decode('utf-8').strip()
                if not chunk_text:
                    continue

                # Process each line separately (some providers send multiple JSON objects per chunk)
                lines = chunk_text.split('\n')
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        parsed_chunk = self.chunk_parser(line)
                        if parsed_chunk:
                            chunk_count += 1
                            yield parsed_chunk
                    except Exception as e:
                        logger.warning(f"Failed to parse streaming chunk line '{line[:100]}...': {e}")
                        continue

            except UnicodeDecodeError as e:
                logger.warning(f"Failed to decode chunk as UTF-8: {e}")
                continue
            except Exception as e:
                logger.warning(f"Unexpected error processing chunk: {e}")
                continue

        # Final cancellation check after stream completes
        if cancellation_token:
            cancellation_token.check_cancelled()
    
    @staticmethod
    def parse_json_line(line: str) -> Optional[Dict[str, Any]]:
        """
        Helper method to safely parse JSON from a line.
        
        Args:
            line: String that should contain JSON
            
        Returns:
            Parsed JSON dictionary or None if parsing fails
        """
        try:
            # Handle Server-Sent Events format (lines starting with "data: ")
            if line.startswith('data: '):
                line = line[6:]  # Remove "data: " prefix
                
            # Skip SSE control messages
            if line in ['[DONE]', '']:
                return None
                
            return json.loads(line)
        except json.JSONDecodeError:
            return None
    
    def create_error_chunk(self, error_message: str, model: str = "unknown") -> StreamingChatResponse:
        """
        Create an error chunk for when something goes wrong during streaming.
        
        Args:
            error_message: Error description
            model: Model name for the response
            
        Returns:
            StreamingChatResponse indicating an error occurred
        """
        from ...ai_providers import ProviderType
        
        return StreamingChatResponse(
            content=f"Error: {error_message}",
            done=True,
            model=model,
            provider_type=ProviderType.OLLAMA,  # Will be overridden by specific providers
            metadata={"error": True, "error_message": error_message}
        )