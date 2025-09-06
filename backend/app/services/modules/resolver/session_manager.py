"""
Session management and cancellation logic for the staged module resolver.

Handles session ID tracking, cancellation checks, and integration with the chat session manager.
"""

import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ResolverSessionManager:
    """
    Session management component for the staged module resolver.
    
    Provides session tracking and cancellation support across all 5 execution stages.
    """
    
    def __init__(self, session_manager=None):
        """
        Initialize resolver session manager.
        
        Args:
            session_manager: Optional chat session manager for cancellation support
        """
        # Session management and cancellation support
        from ....services.chat_session_manager import get_chat_session_manager
        self.session_manager = session_manager or get_chat_session_manager()
        self._current_session_id: Optional[str] = None
    
    def set_session_id(self, session_id: str) -> None:
        """
        Set the current session ID for this resolver instance.
        
        Args:
            session_id: Session ID to associate with operations
        """
        self._current_session_id = session_id
        logger.debug(f"Resolver session ID set to: {session_id}")
    
    def get_current_session_id(self) -> Optional[str]:
        """Get the current session ID."""
        return self._current_session_id
    
    def check_cancellation(self, session_id: Optional[str] = None) -> None:
        """
        Check if the current operation should be cancelled.
        
        Args:
            session_id: Session ID to check, uses current session if not provided
            
        Raises:
            asyncio.CancelledError: If the session has been cancelled
        """
        check_session_id = session_id or self._current_session_id
        if check_session_id and self.session_manager:
            token = self.session_manager.get_session(check_session_id)
            if token and token.is_cancelled():
                logger.info(f"Operation cancelled for session {check_session_id}")
                raise asyncio.CancelledError()
    
    def is_session_active(self, session_id: Optional[str] = None) -> bool:
        """
        Check if the session is still active.
        
        Args:
            session_id: Session ID to check, uses current session if not provided
            
        Returns:
            True if session is active, False if cancelled or not found
        """
        check_session_id = session_id or self._current_session_id
        if check_session_id and self.session_manager:
            token = self.session_manager.get_session(check_session_id)
            return token is not None and not token.is_cancelled()
        return True  # No session tracking, assume active