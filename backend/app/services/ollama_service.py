"""
Enhanced Ollama service with session management and cancellation support.

Extends the existing OllamaService to integrate with ChatSessionManager
for proper cancellation and session tracking.
"""

import asyncio
import json
import logging
import uuid
from typing import Dict, Any, List, AsyncIterator, Optional

import aiohttp
from aiohttp import ClientTimeout, ClientConnectorError, ClientError

from .ollama_service_base import OllamaService as BaseOllamaService
from .ai_providers import (
    ChatRequest,
    ChatResponse,
    StreamingChatResponse,
    ProviderType
)
from .exceptions import ProviderConnectionError, ProviderAuthenticationError
from .chat_session_manager import get_chat_session_manager, ChatSessionManager

logger = logging.getLogger(__name__)


class OllamaService(BaseOllamaService):
    """
    Enhanced Ollama service with session management and cancellation support.
    
    Extends the base OllamaService to integrate with ChatSessionManager,
    enabling proper request cancellation and session tracking.
    """
    
    def __init__(self, session_manager: Optional[ChatSessionManager] = None):
        """
        Initialize the enhanced Ollama service.
        
        Args:
            session_manager: Optional session manager instance. If not provided,
                           uses the global instance.
        """
        super().__init__()
        self.session_manager = session_manager or get_chat_session_manager()
        self._current_session_id = None
    
    def set_session_id(self, session_id: str) -> None:
        """
        Set the current session ID for this provider instance.
        
        Args:
            session_id: Session ID to associate with requests
        """
        self._current_session_id = session_id
    
    async def send_message_with_session(
        self,
        request: ChatRequest,
        session_id: Optional[str] = None,
        conversation_id: Optional[str] = None
    ) -> ChatResponse:
        """
        Send message to Ollama with session management and cancellation support.
        
        Args:
            request: Chat request to send
            session_id: Optional session ID for tracking
            conversation_id: Optional conversation ID for context
            
        Returns:
            ChatResponse with the AI response
            
        Raises:
            asyncio.CancelledError: If the request is cancelled
            ProviderConnectionError: If connection fails
        """
        # Generate session ID if not provided
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        # Create the main task
        main_task = asyncio.current_task()
        if main_task is None:
            # Fallback: create a task wrapper
            return await self._execute_with_session_wrapper(
                self.send_message(request), session_id, conversation_id
            )
        
        # Register the current task with session manager
        self.session_manager.register_session(
            session_id=session_id,
            conversation_id=conversation_id,
            asyncio_task=main_task,
            current_stage=3  # Main AI response generation
        )
        
        try:
            # Execute the original send_message method
            response = await super().send_message(request)
            
            # Mark session as completed (remove from active tracking)
            self.session_manager.remove_session(session_id)
            
            return response
            
        except asyncio.CancelledError:
            # Handle cancellation gracefully
            logger.info(f"Ollama request cancelled for session {session_id}")
            # Session will be cleaned up by session manager
            raise
        except Exception as e:
            # Remove session on any error
            self.session_manager.remove_session(session_id)
            raise
    
    async def send_message_stream_with_session(
        self,
        request: ChatRequest,
        session_id: Optional[str] = None,
        conversation_id: Optional[str] = None
    ) -> AsyncIterator[StreamingChatResponse]:
        """
        Send streaming message to Ollama with session management.
        
        Args:
            request: Chat request to send
            session_id: Optional session ID for tracking
            conversation_id: Optional conversation ID for context
            
        Yields:
            StreamingChatResponse chunks
            
        Raises:
            asyncio.CancelledError: If the request is cancelled
        """
        # Generate session ID if not provided
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        # Create the main task
        main_task = asyncio.current_task()
        if main_task is None:
            # Fallback: create task for streaming
            async def stream_wrapper():
                async for chunk in super().send_message_stream(request):
                    yield chunk
            
            async for chunk in self._execute_stream_with_session_wrapper(
                stream_wrapper(), session_id, conversation_id
            ):
                yield chunk
            return
        
        # Register the current task with session manager
        self.session_manager.register_session(
            session_id=session_id,
            conversation_id=conversation_id,
            asyncio_task=main_task,
            current_stage=3  # Main AI response generation
        )
        
        try:
            # Execute the original streaming method
            async for chunk in super().send_message_stream(request):
                # Check for cancellation between chunks
                if main_task.cancelled():
                    logger.info(f"Ollama streaming cancelled for session {session_id}")
                    raise asyncio.CancelledError()
                
                yield chunk
            
            # Mark session as completed
            self.session_manager.remove_session(session_id)
            
        except asyncio.CancelledError:
            logger.info(f"Ollama streaming request cancelled for session {session_id}")
            raise
        except Exception as e:
            # Remove session on any error
            self.session_manager.remove_session(session_id)
            raise
    
    async def _execute_with_session_wrapper(
        self,
        coro,
        session_id: str,
        conversation_id: Optional[str]
    ) -> ChatResponse:
        """
        Wrapper to execute coroutine with session management when no current task exists.
        
        Args:
            coro: Coroutine to execute
            session_id: Session ID for tracking
            conversation_id: Optional conversation ID
            
        Returns:
            ChatResponse from the coroutine
        """
        # Create a task so we can register it
        task = asyncio.create_task(coro)
        
        # Register with session manager
        self.session_manager.register_session(
            session_id=session_id,
            conversation_id=conversation_id,
            asyncio_task=task,
            current_stage=3
        )
        
        try:
            result = await task
            self.session_manager.remove_session(session_id)
            return result
        except asyncio.CancelledError:
            logger.info(f"Ollama task cancelled for session {session_id}")
            raise
        except Exception:
            self.session_manager.remove_session(session_id)
            raise
    
    async def _execute_stream_with_session_wrapper(
        self,
        stream_gen,
        session_id: str,
        conversation_id: Optional[str]
    ) -> AsyncIterator[StreamingChatResponse]:
        """
        Wrapper to execute streaming generator with session management.
        
        Args:
            stream_gen: Async generator to execute
            session_id: Session ID for tracking
            conversation_id: Optional conversation ID
            
        Yields:
            StreamingChatResponse chunks
        """
        # Create a task for the generator
        async def consume_stream():
            chunks = []
            async for chunk in stream_gen:
                chunks.append(chunk)
            return chunks
        
        task = asyncio.create_task(consume_stream())
        
        # Register with session manager
        self.session_manager.register_session(
            session_id=session_id,
            conversation_id=conversation_id,
            asyncio_task=task,
            current_stage=3
        )
        
        try:
            chunks = await task
            for chunk in chunks:
                yield chunk
            self.session_manager.remove_session(session_id)
        except asyncio.CancelledError:
            logger.info(f"Ollama streaming task cancelled for session {session_id}")
            raise
        except Exception:
            self.session_manager.remove_session(session_id)
            raise
    
    # Backward compatibility methods - delegate to session-aware versions
    async def send_message(self, request: ChatRequest) -> ChatResponse:
        """
        Send message with automatic session management.
        
        Uses the set session ID or generates one automatically.
        """
        return await self.send_message_with_session(
            request,
            session_id=self._current_session_id,
            conversation_id=None
        )
    
    async def send_message_stream(self, request: ChatRequest) -> AsyncIterator[StreamingChatResponse]:
        """
        Send streaming message with automatic session management.
        
        Uses the set session ID or generates one automatically.
        """
        async for chunk in self.send_message_stream_with_session(
            request,
            session_id=self._current_session_id,
            conversation_id=None
        ):
            yield chunk


class OllamaServiceFactory:
    """
    Factory for creating OllamaService instances with or without cancellation support.
    
    Provides a way to create enhanced or standard Ollama services based on configuration.
    """
    
    @staticmethod
    def create_service(with_cancellation: bool = True) -> BaseOllamaService:
        """
        Create an Ollama service instance.
        
        Args:
            with_cancellation: Whether to create enhanced service with cancellation support
            
        Returns:
            OllamaService instance (enhanced or standard)
        """
        if with_cancellation:
            return OllamaServiceWithCancellation()
        else:
            return BaseOllamaService()
    
    @staticmethod
    def create_service_with_session_manager(session_manager: ChatSessionManager) -> OllamaService:
        """
        Create enhanced Ollama service with specific session manager.
        
        Args:
            session_manager: ChatSessionManager instance to use
            
        Returns:
            OllamaServiceWithCancellation instance
        """
        return OllamaService(session_manager=session_manager)