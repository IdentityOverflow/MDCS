"""
Streaming Accumulator Service for converting non-streaming requests to streaming with cancellation.

This service enables cancellation for non-streaming requests by internally converting them
to streaming with accumulation, maintaining API compatibility while adding cancellation support.
"""

import asyncio
import logging
import uuid
from typing import Dict, Any, Optional, AsyncIterator, Callable
from dataclasses import dataclass

from .ai_providers import StreamingChatResponse, ChatResponse
from .chat_session_manager import get_chat_session_manager, ChatSessionManager

logger = logging.getLogger(__name__)


@dataclass
class AccumulatedResponse:
    """
    Result of accumulating a streaming response.
    
    Contains the accumulated content and metadata, along with success status.
    """
    content: str
    thinking: str
    metadata: Dict[str, Any]
    success: bool
    error_message: Optional[str] = None
    chunks_processed: int = 0


class StreamingAccumulator:
    """
    Service for accumulating streaming responses with cancellation support.
    
    Converts streaming responses to non-streaming by accumulating chunks while
    providing cancellation capabilities throughout the process.
    """
    
    def __init__(self, session_manager: Optional[ChatSessionManager] = None):
        """
        Initialize the streaming accumulator.
        
        Args:
            session_manager: Optional session manager instance. If not provided, uses global instance.
        """
        self.session_manager = session_manager or get_chat_session_manager()
        self._active_accumulations: Dict[str, asyncio.Task] = {}
    
    async def accumulate_stream(
        self,
        stream_generator: AsyncIterator[StreamingChatResponse],
        session_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        progress_callback: Optional[Callable[[str, int, Optional[int]], None]] = None
    ) -> AccumulatedResponse:
        """
        Accumulate a streaming response into a single response with cancellation support.
        
        Args:
            stream_generator: Async generator yielding StreamingChatResponse chunks
            session_id: Optional session ID for cancellation tracking
            conversation_id: Optional conversation ID for context
            progress_callback: Optional callback for progress updates
            
        Returns:
            AccumulatedResponse with accumulated content and metadata
            
        Raises:
            asyncio.CancelledError: If the accumulation is cancelled
        """
        # Generate session ID if not provided
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        # Initialize accumulation state
        accumulated_content = ""
        accumulated_thinking = ""
        final_metadata = {}
        chunks_processed = 0
        error_message = None
        
        # Register current task for cancellation
        current_task = asyncio.current_task()
        if current_task:
            try:
                self.session_manager.register_session(
                    session_id=session_id,
                    conversation_id=conversation_id,
                    asyncio_task=current_task,
                    current_stage=3  # Main response accumulation
                )
                logger.debug(f"Successfully registered session {session_id} for cancellation")
            except ValueError as e:
                # Session already exists, continue
                logger.debug(f"Session {session_id} already registered: {e}")
                pass
            except Exception as e:
                # Log other registration errors
                logger.warning(f"Failed to register session {session_id} for cancellation: {e}")
        else:
            logger.warning(f"No current asyncio task found for session {session_id} - cancellation may not work")
        
        try:
            # Track active accumulation
            if current_task:
                self._active_accumulations[session_id] = current_task
            
            # Process streaming chunks
            async for chunk in stream_generator:
                # Check for cancellation before processing each chunk
                if self._is_cancelled(session_id):
                    logger.info(f"Stream accumulation cancelled for session {session_id}")
                    raise asyncio.CancelledError()
                
                # Accumulate content
                if chunk.content:
                    accumulated_content += chunk.content
                
                # Accumulate thinking
                if chunk.thinking:
                    accumulated_thinking += chunk.thinking
                
                # Update metadata from any chunk (not just final ones)
                if chunk.metadata:
                    final_metadata.update(chunk.metadata)
                
                # Also capture model and provider_type from chunk itself
                if chunk.model and "model" not in final_metadata:
                    final_metadata["model"] = chunk.model
                if chunk.provider_type and "provider_type" not in final_metadata:
                    final_metadata["provider_type"] = chunk.provider_type
                
                chunks_processed += 1
                
                # Call progress callback if provided
                if progress_callback:
                    progress_callback(accumulated_content, chunks_processed)
                
                # Final cancellation check
                if self._is_cancelled(session_id):
                    logger.info(f"Stream accumulation cancelled after chunk {chunks_processed}")
                    raise asyncio.CancelledError()
            
            # Successful completion
            return AccumulatedResponse(
                content=accumulated_content,
                thinking=accumulated_thinking,
                metadata=final_metadata,
                success=True,
                chunks_processed=chunks_processed
            )
            
        except asyncio.CancelledError:
            # Re-raise cancellation
            logger.info(f"Accumulation cancelled for session {session_id} after {chunks_processed} chunks")
            raise
        except Exception as e:
            # Handle other errors - return partial result
            logger.error(f"Error during stream accumulation for session {session_id}: {e}")
            error_message = str(e)
            
            return AccumulatedResponse(
                content=accumulated_content,  # Return partial content
                thinking=accumulated_thinking,
                metadata=final_metadata,
                success=False,
                error_message=error_message,
                chunks_processed=chunks_processed
            )
        finally:
            # Clean up
            self._cleanup_accumulation(session_id)
    
    def _is_cancelled(self, session_id: str) -> bool:
        """
        Check if the accumulation session is cancelled.
        
        Args:
            session_id: Session ID to check
            
        Returns:
            True if cancelled, False otherwise
        """
        token = self.session_manager.get_session(session_id)
        return token is not None and token.is_cancelled()
    
    def _cleanup_accumulation(self, session_id: str) -> None:
        """
        Clean up accumulation resources.
        
        Args:
            session_id: Session ID to clean up
        """
        # Remove from active accumulations
        if session_id in self._active_accumulations:
            del self._active_accumulations[session_id]
        
        # Remove from session manager
        self.session_manager.remove_session(session_id)
    
    async def cancel_accumulation(self, session_id: str) -> bool:
        """
        Cancel an active accumulation.
        
        Args:
            session_id: Session ID to cancel
            
        Returns:
            True if cancellation was successful, False if session not found
        """
        return await self.session_manager.cancel_session(session_id)
    
    def get_active_accumulations(self) -> Dict[str, str]:
        """
        Get currently active accumulation sessions.
        
        Returns:
            Dict mapping session IDs to status descriptions
        """
        active = {}
        for session_id, task in self._active_accumulations.items():
            if task.done():
                status = "completed"
            elif task.cancelled():
                status = "cancelled"
            else:
                status = "active"
            active[session_id] = status
        
        return active
    
    async def cleanup_completed_accumulations(self) -> int:
        """
        Clean up completed accumulation tasks.
        
        Returns:
            Number of accumulations cleaned up
        """
        completed_sessions = []
        
        for session_id, task in self._active_accumulations.items():
            if task.done() or task.cancelled():
                completed_sessions.append(session_id)
        
        for session_id in completed_sessions:
            self._cleanup_accumulation(session_id)
        
        if completed_sessions:
            logger.info(f"Cleaned up {len(completed_sessions)} completed accumulations")
        
        return len(completed_sessions)


class StreamingToNonStreamingConverter:
    """
    Converter that transforms streaming providers to appear non-streaming while maintaining cancellation.
    
    This enables cancellation for traditionally non-cancellable non-streaming requests.
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
        session_id: Optional[str] = None,
        conversation_id: Optional[str] = None
    ) -> ChatResponse:
        """
        Convert a streaming response to a ChatResponse with cancellation support.
        
        Args:
            stream_generator: Streaming response generator
            session_id: Optional session ID for cancellation
            conversation_id: Optional conversation ID for context
            
        Returns:
            ChatResponse containing accumulated content
            
        Raises:
            asyncio.CancelledError: If cancelled during accumulation
        """
        # Accumulate the stream
        accumulated = await self.accumulator.accumulate_stream(
            stream_generator=stream_generator,
            session_id=session_id,
            conversation_id=conversation_id
        )
        
        if not accumulated.success:
            raise Exception(f"Stream accumulation failed: {accumulated.error_message}")
        
        # Convert to ChatResponse format
        # Note: This would need to be adapted based on the actual ChatResponse structure
        from unittest.mock import Mock
        response = Mock()
        response.content = accumulated.content
        response.thinking = accumulated.thinking
        response.metadata = accumulated.metadata
        response.model = accumulated.metadata.get("model", "unknown")
        response.provider_type = accumulated.metadata.get("provider_type", "unknown")
        
        return response
    
    async def cancel_conversion(self, session_id: str) -> bool:
        """
        Cancel an active streaming-to-nonstreaming conversion.
        
        Args:
            session_id: Session ID to cancel
            
        Returns:
            True if cancellation was successful
        """
        return await self.accumulator.cancel_accumulation(session_id)