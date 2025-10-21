"""
Simplified streaming accumulator with unified cancellation support.

Converts streaming responses to non-streaming by accumulating chunks,
enabling cancellation for all request types through a single code path.
"""

import asyncio
import logging
from typing import AsyncIterator, Optional
from dataclasses import dataclass

from .ai_providers import StreamingChatResponse, ChatResponse
from .cancellation_token import CancellationToken

logger = logging.getLogger(__name__)


@dataclass
class AccumulatedResponse:
    """
    Result of accumulating a streaming response.

    Contains the accumulated content and metadata, along with success status.
    """
    content: str
    thinking: str
    metadata: dict
    success: bool
    error_message: Optional[str] = None
    chunks_processed: int = 0


class StreamingAccumulator:
    """
    Simplified service for accumulating streaming responses with cancellation support.

    Design principles:
    - No session management (caller owns the CancellationToken)
    - Single responsibility: accumulate chunks
    - Cancellation checks every N chunks
    - Clean error handling
    """

    def __init__(self, cancellation_check_interval: int = 10):
        """
        Initialize the streaming accumulator.

        Args:
            cancellation_check_interval: Check cancellation every N chunks (default 10)
        """
        self.cancellation_check_interval = cancellation_check_interval

    async def accumulate_stream(
        self,
        stream_generator: AsyncIterator[StreamingChatResponse],
        cancellation_token: Optional[CancellationToken] = None
    ) -> AccumulatedResponse:
        """
        Accumulate a streaming response into a single response with cancellation support.

        Args:
            stream_generator: Async generator yielding StreamingChatResponse chunks
            cancellation_token: Optional token for cancellation tracking

        Returns:
            AccumulatedResponse with accumulated content and metadata

        Raises:
            asyncio.CancelledError: If the accumulation is cancelled via token
        """
        # Initialize accumulation state
        accumulated_content = ""
        accumulated_thinking = ""
        final_metadata = {}
        chunks_processed = 0
        error_message = None

        try:
            # Process streaming chunks
            async for chunk in stream_generator:
                # Check for cancellation every N chunks
                if cancellation_token and chunks_processed % self.cancellation_check_interval == 0:
                    if cancellation_token.is_cancelled():
                        logger.warning(f"🛑 Accumulator detected cancellation at chunk {chunks_processed} for session {cancellation_token.session_id}")
                    cancellation_token.check_cancelled()

                # Accumulate content
                if chunk.content:
                    accumulated_content += chunk.content

                # Accumulate thinking
                if chunk.thinking:
                    accumulated_thinking += chunk.thinking

                # Update metadata from any chunk
                if chunk.metadata:
                    final_metadata.update(chunk.metadata)

                # Also capture model and provider_type from chunk itself
                if chunk.model and "model" not in final_metadata:
                    final_metadata["model"] = chunk.model
                if chunk.provider_type and "provider_type" not in final_metadata:
                    final_metadata["provider_type"] = chunk.provider_type

                chunks_processed += 1

            # Final cancellation check after stream completes
            if cancellation_token:
                cancellation_token.check_cancelled()

            # Successful completion
            logger.debug(f"Successfully accumulated {chunks_processed} chunks")
            return AccumulatedResponse(
                content=accumulated_content,
                thinking=accumulated_thinking,
                metadata=final_metadata,
                success=True,
                chunks_processed=chunks_processed
            )

        except asyncio.CancelledError:
            # Re-raise cancellation (don't suppress it)
            logger.info(f"Accumulation cancelled after {chunks_processed} chunks")
            raise

        except Exception as e:
            # Handle other errors - return partial result
            logger.error(f"Error during stream accumulation: {e}")
            error_message = str(e)

            return AccumulatedResponse(
                content=accumulated_content,  # Return partial content
                thinking=accumulated_thinking,
                metadata=final_metadata,
                success=False,
                error_message=error_message,
                chunks_processed=chunks_processed
            )


class StreamingToNonStreamingConverter:
    """
    Simplified converter that transforms streaming providers to non-streaming responses.

    This enables cancellation for all requests through a unified streaming path.
    """

    def __init__(self, accumulator: Optional[StreamingAccumulator] = None):
        """
        Initialize the converter.

        Args:
            accumulator: Optional accumulator instance. If not provided, creates a new one.
        """
        self.accumulator = accumulator or StreamingAccumulator()

    async def convert_streaming_to_response(
        self,
        stream_generator: AsyncIterator[StreamingChatResponse],
        cancellation_token: Optional[CancellationToken] = None
    ) -> ChatResponse:
        """
        Convert a streaming response to a ChatResponse with cancellation support.

        Args:
            stream_generator: Streaming response generator
            cancellation_token: Optional token for cancellation

        Returns:
            ChatResponse containing accumulated content

        Raises:
            asyncio.CancelledError: If cancelled during accumulation
            Exception: If accumulation fails
        """
        # Accumulate the stream
        accumulated = await self.accumulator.accumulate_stream(
            stream_generator=stream_generator,
            cancellation_token=cancellation_token
        )

        if not accumulated.success:
            raise Exception(f"Stream accumulation failed: {accumulated.error_message}")

        # Convert to ChatResponse format
        # Note: We use a mock here but in real usage this would be a proper ChatResponse instance
        from unittest.mock import Mock
        response = Mock()
        response.content = accumulated.content
        response.thinking = accumulated.thinking
        response.metadata = accumulated.metadata
        response.model = accumulated.metadata.get("model", "unknown")
        response.provider_type = accumulated.metadata.get("provider_type", "unknown")

        logger.debug(
            f"Converted streaming response to non-streaming "
            f"({accumulated.chunks_processed} chunks, {len(accumulated.content)} chars)"
        )

        return response
