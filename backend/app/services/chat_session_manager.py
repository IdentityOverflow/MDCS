"""
Simplified chat session manager using unified CancellationToken.

This replaces the complex dual-token system with a simple registry
that manages CancellationToken instances.
"""

import asyncio
import logging
from typing import Dict, Optional, List
from enum import Enum

from .cancellation_token import CancellationToken, TokenState

logger = logging.getLogger(__name__)


class SessionStatus(str, Enum):
    """Enumeration of possible session statuses."""
    ACTIVE = "active"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    NOT_FOUND = "not_found"


class ChatSessionManager:
    """
    Simplified session manager that acts as a registry for CancellationToken instances.

    Design principles:
    - No asyncio.Task management (tokens handle their own state)
    - Simple dictionary registry
    - Thread-safe operations
    - Clear ownership: API layer creates tokens, manager just tracks them
    """

    def __init__(self, max_concurrent_sessions: int = 100):
        """
        Initialize the session manager.

        Args:
            max_concurrent_sessions: Maximum number of concurrent chat sessions allowed
        """
        self.active_sessions: Dict[str, CancellationToken] = {}
        self.max_concurrent_sessions = max_concurrent_sessions
        self._lock = asyncio.Lock()

        logger.info(f"Initialized ChatSessionManager (max sessions: {max_concurrent_sessions})")

    async def register_session(
        self,
        session_id: str,
        conversation_id: Optional[str] = None
    ) -> CancellationToken:
        """
        Register a new chat session with cancellation token.

        Args:
            session_id: Unique identifier for this chat session
            conversation_id: Optional conversation ID for context

        Returns:
            CancellationToken for the registered session

        Raises:
            ValueError: If session_id is already active
            RuntimeError: If max concurrent sessions exceeded
        """
        async with self._lock:
            if session_id in self.active_sessions:
                raise ValueError(f"Session {session_id} already registered")

            if len(self.active_sessions) >= self.max_concurrent_sessions:
                raise RuntimeError(
                    f"Maximum concurrent sessions ({self.max_concurrent_sessions}) exceeded"
                )

            token = CancellationToken(
                session_id=session_id,
                conversation_id=conversation_id
            )

            # Activate the token immediately
            await token.activate()

            self.active_sessions[session_id] = token
            logger.debug(
                f"Registered session {session_id} "
                f"(total active: {len(self.active_sessions)})"
            )

            return token

    def get_session(self, session_id: str) -> Optional[CancellationToken]:
        """
        Get a session token by ID.

        Args:
            session_id: Session ID to look up

        Returns:
            CancellationToken if found, None otherwise
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
            True if session was cancelled, False if not found or already finished
        """
        async with self._lock:
            logger.info(f"🔍 cancel_session called for: {session_id}")
            logger.info(f"🔍 Active sessions: {list(self.active_sessions.keys())}")

            token = self.get_session(session_id)

            if token is None:
                logger.warning(f"Cannot cancel session {session_id}: not found in active sessions")
                return False

            logger.info(f"🔍 Found token: {token}, state={token.state}")

            if token.is_finished():
                logger.debug(f"Session {session_id} already finished (state: {token.state})")
                return False

            # Cancel the token
            logger.info(f"🔍 Calling token.cancel() for session {session_id}")
            success = await token.cancel()

            if success:
                logger.info(f"✅ Cancelled session {session_id}, token state now: {token.state}")
            else:
                logger.warning(f"❌ token.cancel() returned False for session {session_id}")

            return success

    async def complete_session(self, session_id: str) -> bool:
        """
        Mark a session as completed successfully.

        Args:
            session_id: Session ID to complete

        Returns:
            True if session was completed, False if not found or already cancelled
        """
        async with self._lock:
            token = self.get_session(session_id)

            if token is None:
                logger.warning(f"Cannot complete session {session_id}: not found")
                return False

            success = await token.complete()

            if success:
                logger.debug(f"Completed session {session_id}")

            return success

    async def remove_session(self, session_id: str) -> bool:
        """
        Remove a session from active tracking.

        This should be called after the session is finished (cancelled or completed).

        Args:
            session_id: Session ID to remove

        Returns:
            True if session was removed, False if not found
        """
        async with self._lock:
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
                logger.debug(
                    f"Removed session {session_id} "
                    f"(remaining: {len(self.active_sessions)})"
                )
                return True
            else:
                logger.warning(f"Cannot remove session {session_id}: not found")
                return False

    async def cleanup_finished_sessions(self) -> int:
        """
        Clean up finished sessions (cancelled or completed) from active tracking.

        Returns:
            Number of sessions cleaned up
        """
        async with self._lock:
            finished_sessions = []

            for session_id, token in self.active_sessions.items():
                if token.is_finished():
                    finished_sessions.append(session_id)

            cleaned_count = 0
            for session_id in finished_sessions:
                del self.active_sessions[session_id]
                cleaned_count += 1

            if cleaned_count > 0:
                logger.info(
                    f"Cleaned up {cleaned_count} finished sessions "
                    f"(remaining: {len(self.active_sessions)})"
                )

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
                if not token.is_finished():
                    await token.cancel()
                    cancelled_count += 1

            if cancelled_count > 0:
                logger.warning(f"Cancelled all {cancelled_count} active sessions")

            return cancelled_count

    def get_sessions_by_conversation(self, conversation_id: str) -> List[CancellationToken]:
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

    def get_session_summary(self) -> Dict[str, any]:
        """
        Get a summary of all active sessions for debugging.

        Returns:
            Dictionary with session statistics and details
        """
        total = len(self.active_sessions)
        by_state = {
            "active": 0,
            "cancelled": 0,
            "completed": 0
        }

        sessions_detail = []

        for session_id, token in self.active_sessions.items():
            if token.is_active():
                by_state["active"] += 1
            elif token.is_cancelled():
                by_state["cancelled"] += 1
            elif token.is_completed():
                by_state["completed"] += 1

            sessions_detail.append({
                "session_id": session_id,
                "conversation_id": token.conversation_id,
                "state": token.state.value,
                "stage": token.current_stage,
                "age_seconds": token.get_age_seconds()
            })

        return {
            "total_sessions": total,
            "by_state": by_state,
            "sessions": sessions_detail
        }


# Global instance for application-wide session management
_chat_session_manager = ChatSessionManager()


def get_chat_session_manager() -> ChatSessionManager:
    """
    Get the global chat session manager instance.

    Returns:
        ChatSessionManager instance for dependency injection
    """
    return _chat_session_manager
