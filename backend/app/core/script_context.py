"""
Script Execution Context for Advanced Modules.

Provides the execution context object that advanced module scripts receive,
giving them access to conversation data, database sessions, and plugin functions.
Includes reflection safety mechanisms to prevent infinite loops.
"""

import inspect
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from app.core.script_plugins import plugin_registry
from app.models import ExecutionTiming

logger = logging.getLogger(__name__)

# Reflection safety constants
MAX_REFLECTION_DEPTH = 3
MAX_REFLECTION_CHAIN_LENGTH = 10


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
        trigger_data: Optional[Dict[str, Any]] = None,
        current_provider: Optional[str] = None,
        current_provider_settings: Optional[Dict[str, Any]] = None,
        current_chat_controls: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize script execution context.
        
        Args:
            conversation_id: ID of the conversation this script is executing for
            persona_id: ID of the persona using this module
            db_session: Database session for accessing conversation data
            trigger_data: Information about what triggered this module execution
            current_provider: Current chat session provider ("ollama" or "openai")
            current_provider_settings: Current provider connection settings
            current_chat_controls: Current chat control parameters (temperature, max_tokens, etc.)
        """
        self.conversation_id = conversation_id
        self.persona_id = persona_id
        self.db_session = db_session
        self.trigger_data = trigger_data or {}
        
        # Current chat session context
        self.current_provider = current_provider
        self.current_provider_settings = current_provider_settings or {}
        self.current_chat_controls = current_chat_controls or {}
        
        # Reflection safety tracking
        self.reflection_depth = 0
        self.module_resolution_stack = []
        self.reflection_chain = []
        
        # Auto-load plugins if not already loaded (make it truly automatic)
        if not plugin_registry._functions:
            plugin_registry.load_all_plugins()
        
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
            
            # Create wrapper function that auto-injects db_session and script context if needed
            def wrapper(*args, **kwargs):
                """Wrapper function that handles db_session and script context injection."""
                try:
                    # Check if function accepts db_session or _script_context parameters
                    sig = inspect.signature(func)
                    if 'db_session' in sig.parameters and 'db_session' not in kwargs:
                        kwargs['db_session'] = self.db_session
                    if '_script_context' in sig.parameters and '_script_context' not in kwargs:
                        kwargs['_script_context'] = self
                    
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
    
    def can_reflect(self, current_module_id: Optional[str], timing: ExecutionTiming) -> bool:
        """
        Check if reflection is allowed based on current safety constraints.
        
        Args:
            current_module_id: ID of the module attempting to reflect
            timing: Execution timing of the module
            
        Returns:
            True if reflection is safe to proceed
        """
        # Handle None/empty module ID
        if not current_module_id:
            logger.debug("Reflection blocked: No module ID provided")
            return False
        
        # Hard limit on reflection depth
        if self.reflection_depth >= MAX_REFLECTION_DEPTH:
            logger.debug(f"Reflection blocked: Max depth ({MAX_REFLECTION_DEPTH}) reached")
            return False
        
        # Prevent recursive module calls during reflection
        # A module can reflect during its own execution (depth 0), but cannot call another module
        # that would then try to resolve the original module again (depth > 0)
        if current_module_id in self.module_resolution_stack and self.reflection_depth > 0:
            logger.debug(f"Reflection blocked: Recursive module resolution detected for module {current_module_id} at depth {self.reflection_depth}")
            return False
        
        # Timing-based restrictions for nested reflections
        if timing == ExecutionTiming.BEFORE and self.reflection_depth > 0:
            logger.debug("Reflection blocked: Nested BEFORE timing reflection not allowed")
            return False
        
        logger.debug(f"Reflection allowed for module {current_module_id} with timing {timing}")
        return True
    
    def enter_reflection(self, module_id: str, instructions: str) -> None:
        """
        Enter reflection mode - increment depth and add to chain.
        
        Args:
            module_id: ID of the module entering reflection
            instructions: Reflection instructions for audit trail
        """
        self.reflection_depth += 1
        
        # Add to reflection chain with timestamp
        reflection_entry = {
            "module_id": module_id,
            "instructions": instructions,
            "timestamp": datetime.now().isoformat(),
            "depth": self.reflection_depth
        }
        
        self.reflection_chain.append(reflection_entry)
        
        # Limit chain length to prevent memory issues
        if len(self.reflection_chain) > MAX_REFLECTION_CHAIN_LENGTH:
            self.reflection_chain = self.reflection_chain[-MAX_REFLECTION_CHAIN_LENGTH:]
        
        logger.debug(f"Entered reflection for module {module_id} at depth {self.reflection_depth}")
    
    def exit_reflection(self) -> None:
        """Exit reflection mode - decrement depth."""
        if self.reflection_depth > 0:
            self.reflection_depth -= 1
            logger.debug(f"Exited reflection, depth now {self.reflection_depth}")
        else:
            logger.warning("Attempted to exit reflection when depth was already 0")
    
    def add_module_to_resolution_stack(self, module_id: str) -> None:
        """
        Add module to resolution stack to track active resolutions.
        
        Args:
            module_id: ID of the module being resolved
        """
        if module_id not in self.module_resolution_stack:
            self.module_resolution_stack.append(module_id)
            logger.debug(f"Added module {module_id} to resolution stack")
    
    def remove_module_from_resolution_stack(self, module_id: str) -> None:
        """
        Remove module from resolution stack when resolution completes.
        
        Args:
            module_id: ID of the module that finished resolving
        """
        if module_id in self.module_resolution_stack:
            self.module_resolution_stack.remove(module_id)
            logger.debug(f"Removed module {module_id} from resolution stack")
    
    def get_reflection_audit_trail(self) -> List[Dict[str, Any]]:
        """
        Get reflection audit trail for debugging and self-awareness.
        
        Returns:
            List of reflection chain entries
        """
        return self.reflection_chain.copy()