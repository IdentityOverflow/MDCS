"""
Script module executor for Python-based advanced modules.

Handles execution of Python scripts using the RestrictedPython sandbox
with the full plugin function ecosystem.
"""

import logging
from typing import Dict, Any, Optional

from ....models import Module, ModuleType
from ....core.script_engine import ScriptEngine
from ....core.script_context import ScriptExecutionContext

logger = logging.getLogger(__name__)


class ScriptExecutor:
    """
    Executes advanced Python script modules.
    
    Advanced modules contain Python scripts that are executed in a
    RestrictedPython sandbox with access to plugin functions and
    conversation context.
    """
    
    def __init__(self):
        """Initialize the script executor with ScriptEngine."""
        self.script_engine = ScriptEngine()
    
    def execute(self, module: Module, context: Dict[str, Any]) -> str:
        """
        Execute an advanced Python script module.
        
        Args:
            module: Module to execute (must be ModuleType.ADVANCED)
            context: Execution context containing conversation info, etc.
            
        Returns:
            Module execution result as string
            
        Raises:
            ValueError: If module is not an advanced module
        """
        if module.type != ModuleType.ADVANCED:
            raise ValueError(f"ScriptExecutor can only execute ADVANCED modules, got {module.type}")
        
        logger.debug(f"Executing advanced module: {module.name}")
        
        # Get script content from the script field (not content field)
        script_content = module.script or ""
        if not script_content.strip():
            logger.warning(f"Advanced module '{module.name}' has empty script")
            return ""
        
        # Build execution context
        script_context = self._build_script_context(module, context)
        
        try:
            # Execute script using ScriptEngine
            execution_result = self.script_engine.execute_script(
                script=script_content,
                context={'ctx': script_context}
            )
            
            if execution_result.success:
                # Script executed successfully - now resolve the module's template using script variables
                logger.debug(f"Advanced module '{module.name}' script executed successfully")
                
                # Capture script outputs as variables for template resolution
                if execution_result.outputs:
                    for var_name, var_value in execution_result.outputs.items():
                        script_context.set_variable(var_name, var_value)
                
                # Get the module's template (content field)
                template_content = module.content or ""
                
                if template_content.strip():
                    # Resolve template variables using script context variables
                    from ..template_parser import TemplateParser
                    
                    # Get variables set by the script (including captured outputs)
                    script_variables = script_context.get_all_variables()
                    
                    # Substitute variables in template
                    resolved_template = TemplateParser.substitute_variables(template_content, script_variables)
                    
                    logger.debug(f"Advanced module '{module.name}' template resolved, {len(resolved_template)} characters")
                    return resolved_template
                
                elif execution_result.outputs:
                    # No template, but script had output - return the output
                    result = "\n".join(str(output) for output in execution_result.outputs)
                    logger.debug(f"Advanced module '{module.name}' returned script output, {len(result)} characters")
                    return result
                
                else:
                    # No template and no script output
                    logger.debug(f"Advanced module '{module.name}' executed but produced no output or template")
                    return ""
            
            else:
                # Script execution failed
                error_msg = execution_result.error_message or "Unknown execution error"
                logger.error(f"Advanced module '{module.name}' execution failed: {error_msg}")
                return f"[Error in module {module.name}: {error_msg}]"
                
        except Exception as e:
            logger.error(f"Error executing advanced module '{module.name}': {e}")
            return f"[Error in module {module.name}: {str(e)}]"
    
    def _build_script_context(self, module: Module, context: Dict[str, Any]) -> ScriptExecutionContext:
        """
        Build ScriptExecutionContext for module execution.
        
        Args:
            module: Module being executed
            context: Execution context from stage executor
            
        Returns:
            ScriptExecutionContext for script execution
        """
        # Extract key context parameters
        conversation_id = context.get('conversation_id')
        persona_id = context.get('persona_id')
        db_session = context.get('db_session')
        trigger_context = context.get('trigger_context', {})
        current_provider = context.get('current_provider')
        current_provider_settings = context.get('current_provider_settings', {})
        current_chat_controls = context.get('current_chat_controls', {})
        
        # Additional stage-specific context
        stage = context.get('stage')
        stage_name = context.get('stage_name')
        ai_response = context.get('ai_response')
        response_metadata = context.get('response_metadata', {})
        
        # Create script execution context
        script_context = ScriptExecutionContext(
            conversation_id=conversation_id,
            persona_id=persona_id,
            db_session=db_session,
            trigger_data=trigger_context,
            current_provider=current_provider,
            current_provider_settings=current_provider_settings,
            current_chat_controls=current_chat_controls
        )
        
        # Add module-specific information
        script_context.set_variable('module_name', module.name)
        script_context.set_variable('module_id', str(module.id))
        
        # Add stage information if available
        if stage is not None:
            script_context.set_variable('stage', stage)
            script_context.set_variable('stage_name', stage_name)
        
        # Add AI response information for post-response stages
        if ai_response is not None:
            script_context.set_variable('ai_response', ai_response)
            script_context.set_variable('response_metadata', response_metadata)
        
        # Add any additional trigger context
        for key, value in trigger_context.items():
            if key not in ['user_message']:  # Avoid overriding already set values
                script_context.set_variable(key, value)
        
        return script_context
    
    def execute_with_details(self, module: Module, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute an advanced Python script module and return detailed results.
        
        This method returns both the final resolved template and the raw script variables,
        which is useful for POST_RESPONSE stages that need to store the variables.
        
        Args:
            module: Module to execute (must be ModuleType.ADVANCED)
            context: Execution context containing conversation info, etc.
            
        Returns:
            Dictionary containing:
            - final_output: The resolved template string
            - script_variables: Raw variables from script execution
            - success: Whether execution was successful
            - error_message: Error message if execution failed
        """
        if module.type != ModuleType.ADVANCED:
            return {
                "final_output": "",
                "script_variables": {},
                "success": False,
                "error_message": f"ScriptExecutor can only execute ADVANCED modules, got {module.type}"
            }
        
        logger.debug(f"Executing advanced module with details: {module.name}")
        
        # Get script content from the script field (not content field)
        script_content = module.script or ""
        if not script_content.strip():
            logger.warning(f"Advanced module '{module.name}' has empty script")
            return {
                "final_output": "",
                "script_variables": {},
                "success": True,
                "error_message": None
            }
        
        # Build execution context
        script_context = self._build_script_context(module, context)
        
        try:
            # Execute script using ScriptEngine
            execution_result = self.script_engine.execute_script(
                script=script_content,
                context={'ctx': script_context}
            )
            
            if execution_result.success:
                # Script executed successfully - now resolve the module's template using script variables
                logger.debug(f"Advanced module '{module.name}' script executed successfully")
                
                # Capture script outputs as variables for template resolution
                script_variables = execution_result.outputs or {}
                if script_variables:
                    for var_name, var_value in script_variables.items():
                        script_context.set_variable(var_name, var_value)
                
                # Get the module's template (content field)
                template_content = module.content or ""
                
                final_output = ""
                if template_content.strip():
                    # Resolve template variables using script context variables
                    from ..template_parser import TemplateParser
                    
                    # Get variables set by the script (including captured outputs)
                    all_script_variables = script_context.get_all_variables()
                    
                    # Substitute variables in template
                    resolved_template = TemplateParser.substitute_variables(template_content, all_script_variables)
                    final_output = resolved_template
                    logger.debug(f"Advanced module '{module.name}' template resolved, {len(final_output)} characters")
                
                elif script_variables:
                    # No template, but script had output - return the output
                    final_output = "\n".join(str(output) for output in script_variables.values())
                    logger.debug(f"Advanced module '{module.name}' returned script output, {len(final_output)} characters")
                
                return {
                    "final_output": final_output,
                    "script_variables": script_variables,
                    "success": True,
                    "error_message": None
                }
            
            else:
                # Script execution failed
                error_msg = execution_result.error_message or "Unknown execution error"
                logger.error(f"Advanced module '{module.name}' execution failed: {error_msg}")
                return {
                    "final_output": f"[Error in module {module.name}: {error_msg}]",
                    "script_variables": {},
                    "success": False,
                    "error_message": error_msg
                }
                
        except Exception as e:
            logger.error(f"Error executing advanced module '{module.name}': {e}")
            return {
                "final_output": f"[Error in module {module.name}: {str(e)}]",
                "script_variables": {},
                "success": False,
                "error_message": str(e)
            }
    
    @staticmethod
    def can_execute(module: Module) -> bool:
        """
        Check if this executor can handle the given module.
        
        Args:
            module: Module to check
            
        Returns:
            True if module can be executed by ScriptExecutor
        """
        return module.type == ModuleType.ADVANCED