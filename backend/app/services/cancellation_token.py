"""
Unified cancellation token for session management.

This replaces the dual ChatCancellationToken/SimpleCancellationToken system
with a single, simple, robust implementation.
"""

import asyncio
import logging
from datetime import datetime
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class TokenState(str, Enum):
    """Enumeration of cancellation token states."""
    CREATED = "created"
    ACTIVE = "active"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class CancellationToken:
    """
    Unified cancellation token with simple atomic state management.

    Design principles:
    - No asyncio.Task dependency (too fragile)
    - Simple boolean flag + lock for thread safety
    - Clear state machine: CREATED → ACTIVE → [CANCELLED | COMPLETED]
    - Reference counting for nested operations
    - Guaranteed cleanup on state transitions

    This token is passed through the entire request pipeline from API layer
    down to HTTP client, allowing cancellation at any point.
    """

    def __init__(self, session_id: str, conversation_id: Optional[str] = None):
        """
        Initialize cancellation token.

        Args:
            session_id: Unique identifier for this session
            conversation_id: Optional conversation ID for context
        """
        self.session_id = session_id
        self.conversation_id = conversation_id
        self.created_at = datetime.utcnow()

        # State management
        self._state = TokenState.CREATED
        self._lock = asyncio.Lock()

        # Reference counting for nested operations
        self._active_operations = 0

        # Metadata
        self.current_stage: Optional[int] = None
        self.metadata: dict = {}

        logger.debug(f"Created cancellation token for session {session_id}")

    @property
    def state(self) -> TokenState:
        """Get current token state (thread-safe read)."""
        return self._state

    def is_created(self) -> bool:
        """Check if token is in CREATED state."""
        return self._state == TokenState.CREATED

    def is_active(self) -> bool:
        """Check if token is in ACTIVE state."""
        return self._state == TokenState.ACTIVE

    def is_cancelled(self) -> bool:
        """Check if token has been cancelled."""
        return self._state == TokenState.CANCELLED

    def is_completed(self) -> bool:
        """Check if token has completed normally."""
        return self._state == TokenState.COMPLETED

    def is_finished(self) -> bool:
        """Check if token is in a terminal state (cancelled or completed)."""
        return self._state in (TokenState.CANCELLED, TokenState.COMPLETED)

    async def activate(self) -> bool:
        """
        Transition token from CREATED to ACTIVE state.

        Returns:
            True if transition successful, False if already in another state
        """
        async with self._lock:
            if self._state == TokenState.CREATED:
                self._state = TokenState.ACTIVE
                logger.debug(f"Activated token for session {self.session_id}")
                return True
            else:
                logger.warning(f"Cannot activate token in state {self._state}")
                return False

    async def cancel(self) -> bool:
        """
        Cancel the token (can be called from any state).

        Returns:
            True if successfully cancelled, False if already in terminal state
        """
        async with self._lock:
            if self._state == TokenState.CANCELLED:
                logger.debug(f"Token {self.session_id} already cancelled")
                return False

            if self._state == TokenState.COMPLETED:
                logger.debug(f"Token {self.session_id} already completed, cannot cancel")
                return False

            old_state = self._state
            self._state = TokenState.CANCELLED
            logger.info(f"Cancelled token {self.session_id} (was {old_state})")
            return True

    async def complete(self) -> bool:
        """
        Mark token as completed successfully.

        Returns:
            True if successfully completed, False if already cancelled
        """
        async with self._lock:
            if self._state == TokenState.CANCELLED:
                logger.debug(f"Cannot complete cancelled token {self.session_id}")
                return False

            if self._state == TokenState.COMPLETED:
                logger.debug(f"Token {self.session_id} already completed")
                return False

            old_state = self._state
            self._state = TokenState.COMPLETED
            logger.debug(f"Completed token {self.session_id} (was {old_state})")
            return True

    def check_cancelled(self) -> None:
        """
        Check if token is cancelled and raise exception if so.

        Raises:
            asyncio.CancelledError: If token has been cancelled
        """
        if self.is_cancelled():
            logger.debug(f"Cancellation check failed for session {self.session_id}")
            raise asyncio.CancelledError(f"Session {self.session_id} was cancelled")

    async def enter_operation(self) -> None:
        """
        Register the start of a nested operation (for reference counting).

        Raises:
            asyncio.CancelledError: If token is already cancelled
        """
        async with self._lock:
            self.check_cancelled()
            self._active_operations += 1
            logger.debug(f"Session {self.session_id}: active operations = {self._active_operations}")

    async def exit_operation(self) -> None:
        """
        Register the completion of a nested operation.
        """
        async with self._lock:
            self._active_operations = max(0, self._active_operations - 1)
            logger.debug(f"Session {self.session_id}: active operations = {self._active_operations}")

    def has_active_operations(self) -> bool:
        """Check if there are any active nested operations."""
        return self._active_operations > 0

    def set_stage(self, stage: int) -> None:
        """
        Update the current execution stage.

        Args:
            stage: Stage number (1-5)
        """
        old_stage = self.current_stage
        self.current_stage = stage
        logger.debug(f"Session {self.session_id} stage: {old_stage} → {stage}")

    def get_age_seconds(self) -> float:
        """Get the age of this token in seconds."""
        return (datetime.utcnow() - self.created_at).total_seconds()

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"CancellationToken(session_id={self.session_id}, "
            f"state={self._state}, stage={self.current_stage}, "
            f"age={self.get_age_seconds():.1f}s)"
        )


class CancelledException(Exception):
    """
    Exception raised when an operation is cancelled via cancellation token.

    This is separate from asyncio.CancelledError to allow for more controlled
    handling and clearer error messages.
    """

    def __init__(self, session_id: str, message: Optional[str] = None):
        """
        Initialize cancellation exception.

        Args:
            session_id: Session ID that was cancelled
            message: Optional custom message
        """
        self.session_id = session_id
        if message:
            super().__init__(message)
        else:
            super().__init__(f"Session {session_id} was cancelled")
