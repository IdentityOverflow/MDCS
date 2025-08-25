"""
Script Plugin Registry for Advanced Modules.

Provides auto-discovery decorator system for registering plugin functions
that can be used in advanced module script execution contexts.
"""

import importlib
import pkgutil
import threading
from typing import Dict, Callable, Any, Set
import logging

logger = logging.getLogger(__name__)


class ScriptPluginRegistry:
    """
    Registry for plugin functions that can be used in script execution.
    
    Provides decorator-based registration and auto-discovery of plugin modules.
    """
    
    def __init__(self):
        """Initialize the plugin registry."""
        self._functions: Dict[str, Callable] = {}
        self._loaded_plugins: Set[str] = set()
        self._loading_lock = threading.Lock()
    
    def register(self, name: str):
        """
        Decorator to register a function as a plugin.
        
        Args:
            name: Name to register the function under
            
        Returns:
            Decorator function that registers the wrapped function
            
        Example:
            @plugin_registry.register("get_current_time")
            def get_current_time():
                return datetime.now().isoformat()
        """
        def decorator(func: Callable) -> Callable:
            """Inner decorator that performs the registration."""
            self._functions[name] = func
            logger.info(f"Registered plugin function: {name}")
            return func
        
        return decorator
    
    def get_context(self) -> Dict[str, Any]:
        """
        Get all registered plugin functions for script execution.
        
        Returns:
            Dictionary copy of all registered functions
        """
        return self._functions.copy()
    
    def load_all_plugins(self):
        """
        Auto-discover and load all plugin modules from app.plugins package.
        
        Walks through all modules in the app.plugins package and imports them,
        which triggers the @register decorators to register plugin functions.
        Thread-safe implementation prevents concurrent loading issues.
        """
        with self._loading_lock:
            try:
                plugins_package = importlib.import_module("app.plugins")
                
                # Walk through all modules in plugins package
                for importer, modname, ispkg in pkgutil.walk_packages(
                    plugins_package.__path__, 
                    plugins_package.__name__ + "."
                ):
                    if modname not in self._loaded_plugins:
                        try:
                            importlib.import_module(modname)
                            self._loaded_plugins.add(modname)
                            logger.info(f"Loaded plugin module: {modname}")
                        except Exception as e:
                            logger.error(f"Failed to load plugin {modname}: {e}")
                            # Continue loading other plugins even if one fails
                            continue
                            
            except ImportError:
                # app.plugins package doesn't exist yet - this is fine during development
                logger.warning("app.plugins package not found - no plugins loaded")
    
    def clear(self):
        """
        Clear all registered functions (useful for testing).
        """
        self._functions.clear()
        self._loaded_plugins.clear()
    
    def get_registered_functions(self) -> Dict[str, str]:
        """
        Get information about registered functions.
        
        Returns:
            Dictionary mapping function names to their docstrings (for debugging)
        """
        return {
            name: func.__doc__ or "No description available"
            for name, func in self._functions.items()
        }


# Global registry instance
plugin_registry = ScriptPluginRegistry()


def get_plugin_context() -> Dict[str, Any]:
    """
    Convenience function to get the plugin context from global registry.
    
    Returns:
        Dictionary of all registered plugin functions
    """
    return plugin_registry.get_context()


def load_all_plugins():
    """
    Convenience function to load all plugins using global registry.
    """
    plugin_registry.load_all_plugins()