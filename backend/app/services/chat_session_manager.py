"""
Chat Session Manager for handling active chat sessions with cancellation tokens.

Provides infrastructure for tracking, cancelling, and managing concurrent chat sessions
across the multi-stage execution pipeline.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional, List
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class SessionStatus(str, Enum):
    """Enumeration of possible session statuses."""
    ACTIVE = "active"
    CANCELLED = "cancelled" 
    COMPLETED = "completed"
    NOT_FOUND = "not_found"


@dataclass
class ChatCancellationToken:
    """
    Token representing an active chat session that can be cancelled.
    
    Tracks the asyncio task and metadata needed for cancellation across
    the 5-stage execution pipeline.
    """
    session_id: str
    conversation_id: Optional[str]
    asyncio_task: asyncio.Task
    current_stage: Optional[int] = None
    cancelled: bool = False
    created_at: datetime = None
    
    def __post_init__(self):
        """Set creation timestamp if not provided."""
        if self.created_at is None:
            self.created_at = datetime.utcnow()
    
    def is_cancelled(self) -> bool:
        """Check if the session has been cancelled."""
        return self.cancelled or self.asyncio_task.cancelled()
    
    def is_completed(self) -> bool:
        """Check if the asyncio task is completed (done and not cancelled)."""
        return self.asyncio_task.done() and not self.asyncio_task.cancelled()
    
    def is_active(self) -> bool:
        """Check if the session is still active (not cancelled and not done)."""
        return not self.is_cancelled() and not self.asyncio_task.done()


class ChatSessionManager:
    """
    Manager for active chat sessions with cancellation capabilities.
    
    Provides thread-safe operations for registering, tracking, and cancelling
    concurrent chat sessions. Essential for implementing interrupt/stop functionality.
    """
    
    def __init__(self, max_concurrent_sessions: int = 10):
        """
        Initialize the session manager.
        
        Args:
            max_concurrent_sessions: Maximum number of concurrent chat sessions allowed
        """
        self.active_sessions: Dict[str, ChatCancellationToken] = {}
        self.max_concurrent_sessions = max_concurrent_sessions
        self._lock = asyncio.Lock()
    
    def register_session(
        self,
        session_id: str,
        conversation_id: Optional[str],
        asyncio_task: asyncio.Task,
        current_stage: Optional[int] = None
    ) -> ChatCancellationToken:
        """
        Register a new chat session with cancellation token.
        
        Args:
            session_id: Unique identifier for this chat session
            conversation_id: Optional conversation ID for context
            asyncio_task: The main asyncio task for this chat session
            current_stage: Current execution stage (1-5)
            
        Returns:
            ChatCancellationToken for the registered session
            
        Raises:
            ValueError: If session_id is already active
            RuntimeError: If max concurrent sessions exceeded
        """
        if session_id in self.active_sessions:
            raise ValueError(f"Session {session_id} already active")
        
        if len(self.active_sessions) >= self.max_concurrent_sessions:
            raise RuntimeError(f"Maximum concurrent sessions ({self.max_concurrent_sessions}) exceeded")
        
        token = ChatCancellationToken(
            session_id=session_id,
            conversation_id=conversation_id,
            asyncio_task=asyncio_task,
            current_stage=current_stage
        )
        
        self.active_sessions[session_id] = token
        logger.info(f"Registered chat session {session_id} (stage {current_stage})")
        
        return token
    
    def get_session(self, session_id: str) -> Optional[ChatCancellationToken]:
        """
        Get a session token by ID.
        
        Args:
            session_id: Session ID to look up
            
        Returns:
            ChatCancellationToken if found, None otherwise
        """
        return self.active_sessions.get(session_id)
    
    def has_active_session(self, session_id: str) -> bool:
        """
        Check if a session ID is currently active.
        
        Args:
            session_id: Session ID to check
            
        Returns:
            True if session exists and is active
        """
        token = self.get_session(session_id)
        return token is not None and token.is_active()
    
    async def cancel_session(self, session_id: str) -> bool:
        """
        Cancel a specific chat session.
        
        Args:
            session_id: Session ID to cancel
            
        Returns:
            True if session was cancelled, False if not found or already cancelled
        """
        async with self._lock:
            token = self.get_session(session_id)
            if token is None:
                logger.warning(f"Cannot cancel session {session_id}: not found")
                return False
            
            if token.is_cancelled():
                logger.info(f"Session {session_id} already cancelled")
                return False
            
            # Cancel the asyncio task
            token.asyncio_task.cancel()
            token.cancelled = True
            
            logger.info(f"Cancelled chat session {session_id} (stage {token.current_stage})")
            return True
    
    def remove_session(self, session_id: str) -> bool:
        """
        Remove a session from active tracking.
        
        Args:
            session_id: Session ID to remove
            
        Returns:
            True if session was removed, False if not found
        """
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            logger.debug(f"Removed session {session_id} from active tracking")
            return True
        return False
    
    async def cleanup_completed_sessions(self) -> int:
        """
        Clean up completed or cancelled sessions from active tracking.
        
        Returns:
            Number of sessions cleaned up
        """
        async with self._lock:
            completed_sessions = []
            
            for session_id, token in self.active_sessions.items():
                if token.is_cancelled() or token.is_completed():
                    completed_sessions.append(session_id)
            
            cleaned_count = 0
            for session_id in completed_sessions:
                if self.remove_session(session_id):
                    cleaned_count += 1
            
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} completed chat sessions")
            
            return cleaned_count
    
    def get_session_status(self, session_id: str) -> SessionStatus:
        """
        Get the current status of a session.
        
        Args:
            session_id: Session ID to check
            
        Returns:
            SessionStatus indicating current state
        """
        token = self.get_session(session_id)
        if token is None:
            return SessionStatus.NOT_FOUND
        
        if token.is_cancelled():
            return SessionStatus.CANCELLED
        elif token.is_completed():
            return SessionStatus.COMPLETED
        else:
            return SessionStatus.ACTIVE
    
    def get_active_session_count(self) -> int:
        """
        Get the count of currently active sessions.
        
        Returns:
            Number of active sessions
        """
        return len(self.active_sessions)
    
    async def cancel_all_sessions(self) -> int:
        """
        Cancel all active chat sessions.
        
        Useful for shutdown or emergency stop scenarios.
        
        Returns:
            Number of sessions that were cancelled
        """
        async with self._lock:
            cancelled_count = 0
            
            for token in self.active_sessions.values():
                if not token.is_cancelled():
                    token.asyncio_task.cancel()
                    token.cancelled = True
                    cancelled_count += 1
            
            if cancelled_count > 0:
                logger.warning(f"Cancelled all {cancelled_count} active chat sessions")
            
            return cancelled_count
    
    def update_session_stage(self, session_id: str, stage: int) -> bool:
        """
        Update the current execution stage for a session.
        
        Args:
            session_id: Session ID to update
            stage: New stage number (1-5)
            
        Returns:
            True if updated successfully, False if session not found
        """
        token = self.get_session(session_id)
        if token is None:
            return False
        
        old_stage = token.current_stage
        token.current_stage = stage
        logger.debug(f"Session {session_id} stage updated: {old_stage} -> {stage}")
        return True
    
    def get_sessions_by_conversation(self, conversation_id: str) -> List[ChatCancellationToken]:
        """
        Get all active sessions for a specific conversation.
        
        Args:
            conversation_id: Conversation ID to filter by
            
        Returns:
            List of active session tokens for the conversation
        """
        return [
            token for token in self.active_sessions.values()
            if token.conversation_id == conversation_id and token.is_active()
        ]


# Global instance for application-wide session management
chat_session_manager = ChatSessionManager()


def get_chat_session_manager() -> ChatSessionManager:
    """
    Get the global chat session manager instance.
    
    Returns:
        ChatSessionManager instance for dependency injection
    """
    return chat_session_manager