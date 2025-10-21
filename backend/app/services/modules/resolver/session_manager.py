"""
Session management and cancellation logic for the staged module resolver.

Simplified to use the unified CancellationToken system.
"""

import logging
from typing import Optional

from app.services.cancellation_token import CancellationToken

logger = logging.getLogger(__name__)


class ResolverSessionManager:
    """
    Simplified session management component for the staged module resolver.

    Provides session tracking and cancellation support across all 5 execution stages.
    Now uses the unified CancellationToken instead of managing its own tokens.
    """

    def __init__(self, cancellation_token: Optional[CancellationToken] = None):
        """
        Initialize resolver session manager.

        Args:
            cancellation_token: Optional cancellation token for this resolver instance
        """
        self.cancellation_token = cancellation_token

    def set_cancellation_token(self, token: CancellationToken) -> None:
        """
        Set the cancellation token for this resolver instance.

        Args:
            token: CancellationToken to use for cancellation checks
        """
        self.cancellation_token = token
        logger.debug(f"Resolver using cancellation token for session {token.session_id}")

    def check_cancellation(self, session_id: Optional[str] = None) -> None:
        """
        Check if the current operation should be cancelled.

        Args:
            session_id: Ignored, kept for API compatibility

        Raises:
            asyncio.CancelledError: If the session has been cancelled
        """
        if self.cancellation_token:
            self.cancellation_token.check_cancelled()

    def is_session_active(self, session_id: Optional[str] = None) -> bool:
        """
        Check if the session is still active.

        Args:
            session_id: Ignored, kept for API compatibility

        Returns:
            True if session is active, False if cancelled or not found
        """
        if self.cancellation_token:
            return self.cancellation_token.is_active()
        return True  # No token, assume active
