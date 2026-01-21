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
            Uses buffering to handle incomplete JSON chunks that arrive across HTTP boundaries.
            Failed chunk parsing is logged as warnings but doesn't stop the stream.
            Empty or invalid chunks are automatically filtered out.
            Cancellation is checked every N chunks (configurable).
        """
        chunk_count = 0
        buffer = ""  # Buffer to accumulate incomplete JSON

        async for chunk in chunk_iterator:
            # Check for cancellation every N chunks
            self._check_cancellation(cancellation_token, chunk_count)

            if not chunk:
                continue

            # Decode chunk and add to buffer
            chunk_text = self._decode_chunk(chunk)
            if not chunk_text:
                continue

            buffer += chunk_text

            # Process complete lines from buffer and yield parsed chunks
            buffer, parsed_count = self._process_complete_lines(buffer)
            chunk_count += parsed_count

            # Yield all parsed chunks
            for parsed_chunk in self._parsed_chunks:
                yield parsed_chunk

        # Process any remaining data in buffer
        final_chunk = self._process_final_buffer(buffer)
        if final_chunk:
            yield final_chunk

        # Final cancellation check after stream completes
        self._check_cancellation(cancellation_token, chunk_count)

    def _check_cancellation(
        self,
        cancellation_token: Optional[CancellationToken],
        chunk_count: int
    ) -> None:
        """Check if operation should be cancelled."""
        if cancellation_token and chunk_count % self.cancellation_check_interval == 0:
            cancellation_token.check_cancelled()

    def _decode_chunk(self, chunk: bytes) -> Optional[str]:
        """Decode a chunk of bytes to UTF-8 string."""
        try:
            return chunk.decode('utf-8')
        except UnicodeDecodeError as e:
            logger.warning(f"Failed to decode chunk as UTF-8: {e}")
            return None

    def _process_complete_lines(self, buffer: str) -> tuple[str, int]:
        """
        Extract and parse complete lines from buffer.

        Returns:
            Tuple of (remaining_buffer, parsed_count)
        """
        self._parsed_chunks = []
        parsed_count = 0

        while '\n' in buffer:
            line_end = buffer.index('\n')
            line = buffer[:line_end].strip()
            buffer = buffer[line_end + 1:]

            if not line:
                continue

            parsed_chunk = self._try_parse_line(line)
            if parsed_chunk:
                self._parsed_chunks.append(parsed_chunk)
                parsed_count += 1

        return buffer, parsed_count

    def _try_parse_line(self, line: str) -> Optional[StreamingChatResponse]:
        """Attempt to parse a single line as a streaming chunk."""
        try:
            return self.chunk_parser(line)
        except Exception as e:
            # Only log if it's not a JSON parsing error (those are logged in chunk_parser)
            if "JSON" not in str(e):
                logger.warning(f"Failed to parse streaming chunk line '{line[:100]}...': {e}")
            return None

    def _process_final_buffer(self, buffer: str) -> Optional[StreamingChatResponse]:
        """Process any remaining data in buffer at end of stream."""
        if not buffer.strip():
            return None

        try:
            return self.chunk_parser(buffer.strip())
        except Exception as e:
            logger.debug(f"Failed to parse final buffer content: {e}")
            return None
    
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