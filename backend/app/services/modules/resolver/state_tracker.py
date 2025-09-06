"""
SystemPromptState tracking component for the staged module resolver.

Handles state tracking for AI plugins and debug information collection.
"""

import logging
from typing import Optional, Dict, Any

from ....services.system_prompt_state import SystemPromptState, PromptStateManager

logger = logging.getLogger(__name__)


class ResolverStateTracker:
    """
    State tracking component for the staged module resolver.
    
    Manages SystemPromptState tracking for AI plugins and provides debug capabilities.
    """
    
    def __init__(self):
        """Initialize the state tracker."""
        self._state_tracking_enabled: bool = False
        self._prompt_state_manager: Optional[PromptStateManager] = None
    
    def enable_state_tracking(self) -> None:
        """Enable SystemPromptState tracking for AI plugins."""
        self._state_tracking_enabled = True
        self._prompt_state_manager = PromptStateManager()
        logger.debug("SystemPromptState tracking enabled")
    
    def disable_state_tracking(self) -> None:
        """Disable SystemPromptState tracking."""
        self._state_tracking_enabled = False
        self._prompt_state_manager = None
        logger.debug("SystemPromptState tracking disabled")
    
    def is_state_tracking_enabled(self) -> bool:
        """Check if state tracking is enabled."""
        return self._state_tracking_enabled
    
    def get_current_state(self) -> Optional[SystemPromptState]:
        """Get current SystemPromptState if tracking is enabled."""
        return self._prompt_state_manager.get_current_state() if self._prompt_state_manager else None
    
    def get_debug_summary(self) -> Optional[Dict[str, Any]]:
        """Get debug summary if state tracking is enabled."""
        return self._prompt_state_manager.get_debug_summary() if self._prompt_state_manager else None
    
    def get_performance_summary(self) -> Optional[Dict[str, Any]]:
        """Get performance summary if state tracking is enabled."""
        return self._prompt_state_manager.get_performance_summary() if self._prompt_state_manager else None
    
    def get_state_manager(self) -> Optional[PromptStateManager]:
        """Get the underlying state manager if tracking is enabled."""
        return self._prompt_state_manager