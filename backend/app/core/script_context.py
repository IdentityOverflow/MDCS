"""
Script Execution Context for Advanced Modules.

Provides the execution context object that advanced module scripts receive,
giving them access to conversation data, database sessions, and plugin functions.
"""

import inspect
import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.core.script_plugins import plugin_registry

logger = logging.getLogger(__name__)


class ScriptExecutionContext:
    """
    Context object available to scripts as 'ctx'.
    
    Provides access to conversation data, database session, plugin functions,
    and trigger information for advanced module script execution.
    """
    
    def __init__(
        self, 
        conversation_id: str, 
        persona_id: str, 
        db_session: Session,
        trigger_data: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize script execution context.
        
        Args:
            conversation_id: ID of the conversation this script is executing for
            persona_id: ID of the persona using this module
            db_session: Database session for accessing conversation data
            trigger_data: Information about what triggered this module execution
        """
        self.conversation_id = conversation_id
        self.persona_id = persona_id
        self.db_session = db_session
        self.trigger_data = trigger_data or {}
        
        # Load plugin functions
        self._plugin_functions = plugin_registry.get_context()
        
        logger.debug(f"Initialized script context for conversation {conversation_id}")
    
    def __getattr__(self, name: str):
        """
        Provide attribute access to plugin functions.
        
        Args:
            name: Name of the plugin function to access
            
        Returns:
            Plugin function wrapper with db_session injection
            
        Raises:
            AttributeError: If plugin function doesn't exist
        """
        if name in self._plugin_functions:
            func = self._plugin_functions[name]
            
            # Create wrapper function that auto-injects db_session if needed
            def wrapper(*args, **kwargs):
                """Wrapper function that handles db_session injection."""
                try:
                    # Check if function accepts db_session parameter
                    sig = inspect.signature(func)
                    if 'db_session' in sig.parameters and 'db_session' not in kwargs:
                        kwargs['db_session'] = self.db_session
                    
                    return func(*args, **kwargs)
                    
                except Exception as e:
                    logger.error(f"Error executing plugin function '{name}': {e}")
                    raise
            
            return wrapper
        
        raise AttributeError(f"Function '{name}' not available in script context")
    
    def get_available_functions(self) -> Dict[str, str]:
        """
        Get information about available plugin functions.
        
        Returns:
            Dictionary mapping function names to their docstrings
        """
        return {
            name: func.__doc__ or "No description available"
            for name, func in self._plugin_functions.items()
        }
    
    def has_function(self, name: str) -> bool:
        """
        Check if a plugin function is available.
        
        Args:
            name: Name of the function to check
            
        Returns:
            True if function is available
        """
        return name in self._plugin_functions