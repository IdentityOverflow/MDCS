"""
AI-powered module executor for modules requiring AI inference.

Extends script execution with AI provider access for modules that
need to make AI calls during execution (like ctx.reflect()).
"""

import logging
from typing import Dict, Any, Optional

from ....models import Module, ModuleType
from ....core.script_engine import ScriptEngine
from ....core.script_context import ScriptExecutionContext
from .script_executor import ScriptExecutor

logger = logging.getLogger(__name__)


class AIExecutor(ScriptExecutor):
    """
    Executes advanced Python script modules with AI inference support.
    
    Extends ScriptExecutor to provide AI provider access for modules
    that need to make AI calls (reflection, analysis, etc.) during execution.
    """
    
    def __init__(self, current_provider: Optional[str] = None, provider_settings: Optional[Dict[str, Any]] = None):
        """
        Initialize the AI-enabled script executor.
        
        Args:
            current_provider: Current AI provider ("ollama" or "openai")
            provider_settings: Provider connection settings
        """
        super().__init__()
        self.current_provider = current_provider
        self.provider_settings = provider_settings or {}
    
    def execute(self, module: Module, context: Dict[str, Any]) -> str:
        """
        Execute an advanced Python script module with AI support.
        
        Args:
            module: Module to execute (must be ModuleType.ADVANCED with requires_ai_inference=True)
            context: Execution context containing conversation info, AI settings, etc.
            
        Returns:
            Module execution result as string
            
        Raises:
            ValueError: If module is not an advanced module requiring AI
        """
        if module.type != ModuleType.ADVANCED:
            raise ValueError(f"AIExecutor can only execute ADVANCED modules, got {module.type}")
        
        if not module.requires_ai_inference:
            logger.warning(f"Module '{module.name}' doesn't require AI inference, consider using ScriptExecutor instead")
        
        logger.debug(f"Executing AI-powered module: {module.name}")
        
        # Get script content
        script_content = module.content or ""
        if not script_content.strip():
            logger.warning(f"AI module '{module.name}' has empty content")
            return ""
        
        # Build enhanced execution context with AI support
        script_context = self._build_ai_script_context(module, context)
        
        try:
            # Execute script using ScriptEngine with AI support
            execution_result = self.script_engine.execute_script(
                script_content=script_content,
                context=script_context
            )
            
            # Extract output from execution result
            if execution_result.success and execution_result.outputs:
                # Join all outputs (scripts can produce multiple outputs)
                result = "\n".join(str(output) for output in execution_result.outputs)
                logger.debug(f"AI module '{module.name}' executed successfully, {len(result)} characters output")
                return result
            
            elif execution_result.success:
                # Script executed but produced no output
                logger.debug(f"AI module '{module.name}' executed successfully but produced no output")
                return ""
            
            else:
                # Script execution failed
                error_msg = execution_result.error or "Unknown execution error"
                logger.error(f"AI module '{module.name}' execution failed: {error_msg}")
                return f"[Error in AI module {module.name}: {error_msg}]"
                
        except Exception as e:
            logger.error(f"Error executing AI module '{module.name}': {e}")
            return f"[Error in AI module {module.name}: {str(e)}]"
    
    def _build_ai_script_context(self, module: Module, context: Dict[str, Any]) -> ScriptExecutionContext:
        """
        Build enhanced ScriptExecutionContext with AI provider support.
        
        Args:
            module: Module being executed
            context: Execution context from stage executor
            
        Returns:
            ScriptExecutionContext with AI capabilities enabled
        """
        # Start with base script context
        script_context = super()._build_script_context(module, context)
        
        # Ensure AI provider information is available
        provider = context.get('current_provider') or self.current_provider
        provider_settings = context.get('current_provider_settings') or self.provider_settings
        chat_controls = context.get('current_chat_controls', {})
        
        # Update context with AI provider info
        if provider:
            script_context.set_current_provider(provider, provider_settings)
            script_context.set_variable('current_provider', provider)
            script_context.set_variable('current_provider_settings', provider_settings)
            script_context.set_variable('current_chat_controls', chat_controls)
        
        # Add AI-specific context variables
        script_context.set_variable('ai_enabled', True)
        script_context.set_variable('requires_ai_inference', module.requires_ai_inference)
        
        # Log AI context setup
        logger.debug(f"AI context enabled for module '{module.name}' with provider: {provider}")
        
        return script_context
    
    @staticmethod
    def can_execute(module: Module) -> bool:
        """
        Check if this executor can handle the given module.
        
        Args:
            module: Module to check
            
        Returns:
            True if module can be executed by AIExecutor
        """
        return (module.type == ModuleType.ADVANCED and 
                module.requires_ai_inference)
    
    def set_ai_provider(self, provider: str, settings: Dict[str, Any]) -> None:
        """
        Update AI provider settings for this executor.
        
        Args:
            provider: Provider name ("ollama" or "openai")
            settings: Provider connection settings
        """
        self.current_provider = provider
        self.provider_settings = settings
        logger.debug(f"AI executor provider updated to: {provider}")