"""
Simple module executor for text-based modules.

Handles basic text substitution and simple module resolution without
script execution or AI inference.
"""

import logging
from typing import Dict, Any

from ....models import Module, ModuleType

logger = logging.getLogger(__name__)


class SimpleExecutor:
    """
    Executes simple text-based modules.
    
    Simple modules contain static text content that is directly substituted
    into templates without any processing or dynamic generation.
    """
    
    def execute(self, module: Module, context: Dict[str, Any]) -> str:
        """
        Execute a simple text module.
        
        Args:
            module: Module to execute (must be ModuleType.SIMPLE)
            context: Execution context (not used for simple modules)
            
        Returns:
            Module content as string
            
        Raises:
            ValueError: If module is not a simple module
        """
        if module.module_type != ModuleType.SIMPLE:
            raise ValueError(f"SimpleExecutor can only execute SIMPLE modules, got {module.module_type}")
        
        logger.debug(f"Executing simple module: {module.name}")
        
        # Simple modules just return their content directly
        content = module.content or ""
        
        # Log execution for debugging
        logger.debug(f"Simple module '{module.name}' returned {len(content)} characters")
        
        return content
    
    @staticmethod
    def can_execute(module: Module) -> bool:
        """
        Check if this executor can handle the given module.
        
        Args:
            module: Module to check
            
        Returns:
            True if module can be executed by SimpleExecutor
        """
        return module.module_type == ModuleType.SIMPLE