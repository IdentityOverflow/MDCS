"""
Module Resolution Service for the Cognitive Engine.

Handles parsing @module_name references in templates and resolving them
to their actual content with proper error handling and circular dependency detection.
"""

import re
import logging
from typing import List, Dict, Set, Optional, Any
from dataclasses import dataclass
from sqlalchemy.orm import Session

from app.models import Module, ModuleType, ExecutionTiming
from app.database.connection import get_db
from app.core.script_engine import ScriptEngine
from app.core.script_context import ScriptExecutionContext
from app.core.trigger_matcher import TriggerMatcher

logger = logging.getLogger(__name__)

# Configuration constants
MAX_RECURSION_DEPTH = 10
MODULE_NAME_PATTERN = r'(?<!\\)@([a-z][a-z0-9_]{0,49})'  # Negative lookbehind to exclude escaped @
ESCAPED_MODULE_PATTERN = r'\\@([a-z][a-z0-9_]{0,49})'  # Pattern for escaped modules
VARIABLE_PATTERN = r'\$\{([a-zA-Z_][a-zA-Z0-9_]*)\}'  # Pattern for ${variable_name}
MODULE_NAME_MAX_LENGTH = 50


@dataclass
class ModuleResolutionWarning:
    """Warning information for module resolution issues."""
    module_name: str
    warning_type: str  # 'module_not_found', 'circular_dependency', 'max_depth_exceeded'
    message: str


@dataclass
class TemplateResolutionResult:
    """Result of template resolution with content and warnings."""
    resolved_template: str
    warnings: List[ModuleResolutionWarning]
    resolved_modules: List[str]  # List of successfully resolved module names


class ModuleResolver:
    """
    Service for resolving @module_name references in templates.
    
    Handles recursive resolution, circular dependency detection,
    and provides comprehensive error reporting.
    """
    
    def __init__(self, db_session: Optional[Session] = None):
        """
        Initialize the module resolver.
        
        Args:
            db_session: Optional database session. If not provided, will get one from connection pool.
        """
        self.db_session = db_session
        self._resolution_stack: Set[str] = set()  # Track modules being resolved to detect cycles
    
    def resolve_template(
        self, 
        template: str,
        conversation_id: Optional[str] = None,
        persona_id: Optional[str] = None,
        db_session: Optional[Session] = None,
        trigger_context: Optional[Dict[str, Any]] = None,
        current_provider: Optional[str] = None,
        current_provider_settings: Optional[Dict[str, Any]] = None,
        current_chat_controls: Optional[Dict[str, Any]] = None
    ) -> TemplateResolutionResult:
        """
        Resolve all @module_name references in a template, with support for advanced modules.
        
        Args:
            template: The template string containing @module_name references
            conversation_id: Optional conversation ID for advanced module context
            persona_id: Optional persona ID for advanced module context
            db_session: Optional database session for advanced module context
            trigger_context: Optional trigger context for advanced modules
            current_provider: Current chat session provider ("ollama" or "openai")
            current_provider_settings: Current provider connection settings  
            current_chat_controls: Current chat control parameters
            
        Returns:
            TemplateResolutionResult with resolved content and any warnings
        """
        if not template:
            return TemplateResolutionResult(
                resolved_template="",
                warnings=[],
                resolved_modules=[]
            )
        
        warnings: List[ModuleResolutionWarning] = []
        resolved_modules: List[str] = []
        
        # Reset resolution stack for new template
        self._resolution_stack = set()
        
        try:
            # First, handle escaped modules by temporarily replacing them
            escaped_placeholders = {}
            escaped_counter = 0
            
            def escape_replacement(match):
                nonlocal escaped_counter
                placeholder = f"__ESCAPED_MODULE_{escaped_counter}__"
                escaped_placeholders[placeholder] = f"@{match.group(1)}"
                escaped_counter += 1
                return placeholder
            
            # Replace escaped modules with placeholders
            template_with_placeholders = re.sub(ESCAPED_MODULE_PATTERN, escape_replacement, template)
            
            # Resolve normal modules
            resolved_content = self._resolve_recursive(
                template_with_placeholders, 
                warnings, 
                resolved_modules, 
                depth=0,
                conversation_id=conversation_id,
                persona_id=persona_id,
                db_session=db_session or self.db_session,
                trigger_context=trigger_context or {},
                current_provider=current_provider,
                current_provider_settings=current_provider_settings,
                current_chat_controls=current_chat_controls
            )
            
            # Restore escaped modules (remove backslash)
            for placeholder, original in escaped_placeholders.items():
                resolved_content = resolved_content.replace(placeholder, original)
            
            return TemplateResolutionResult(
                resolved_template=resolved_content,
                warnings=warnings,
                resolved_modules=list(set(resolved_modules))  # Remove duplicates
            )
            
        except Exception as e:
            logger.error(f"Unexpected error during template resolution: {e}")
            warnings.append(ModuleResolutionWarning(
                module_name="",
                warning_type="resolution_error",
                message=f"Unexpected error during resolution: {str(e)}"
            ))
            
            return TemplateResolutionResult(
                resolved_template=template,  # Return original on error
                warnings=warnings,
                resolved_modules=resolved_modules
            )
    
    def _resolve_recursive(
        self, 
        template: str, 
        warnings: List[ModuleResolutionWarning], 
        resolved_modules: List[str], 
        depth: int,
        conversation_id: Optional[str] = None,
        persona_id: Optional[str] = None,
        db_session: Optional[Session] = None,
        trigger_context: Optional[Dict[str, Any]] = None,
        current_provider: Optional[str] = None,
        current_provider_settings: Optional[Dict[str, Any]] = None,
        current_chat_controls: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Recursively resolve module references in template with advanced module support.
        
        Args:
            template: Template to resolve
            warnings: List to collect warnings
            resolved_modules: List to collect successfully resolved module names
            depth: Current recursion depth
            conversation_id: Conversation ID for advanced module context
            persona_id: Persona ID for advanced module context
            db_session: Database session for advanced module context
            trigger_context: Trigger context for advanced modules
            current_provider: Current chat session provider ("ollama" or "openai")
            current_provider_settings: Current provider connection settings
            current_chat_controls: Current chat control parameters
            
        Returns:
            Template with module references resolved
        """
        # Check maximum recursion depth
        if depth > MAX_RECURSION_DEPTH:
            warnings.append(ModuleResolutionWarning(
                module_name="",
                warning_type="max_depth_exceeded",
                message=f"Maximum recursion depth ({MAX_RECURSION_DEPTH}) exceeded"
            ))
            return template
        
        # Parse module references in current template
        module_names = self._parse_module_references(template)
        
        if not module_names:
            return template  # No modules to resolve
        
        # Get modules from database
        modules = self._get_modules_by_names(module_names)
        modules_by_name = {module.name: module for module in modules}
        
        # Track missing modules
        found_module_names = set(modules_by_name.keys())
        missing_modules = set(module_names) - found_module_names
        
        for missing_module in missing_modules:
            warnings.append(ModuleResolutionWarning(
                module_name=missing_module,
                warning_type="module_not_found",
                message=f"Module '{missing_module}' not found"
            ))
        
        # Resolve each module reference
        resolved_template = template
        
        for module_name in module_names:
            module_ref = f"@{module_name}"
            
            if module_name in missing_modules:
                # Keep missing module as-is (don't replace with empty string)
                continue
            
            # Check for circular dependency
            if module_name in self._resolution_stack:
                warnings.append(ModuleResolutionWarning(
                    module_name=module_name,
                    warning_type="circular_dependency",
                    message=f"Circular dependency detected with module '{module_name}'"
                ))
                # Keep circular dependency module as-is (don't replace with empty string)
                continue
            
            # Add to resolution stack
            self._resolution_stack.add(module_name)
            
            try:
                module = modules_by_name[module_name]
                module_content = module.content or ""  # Handle None content
                
                # Handle advanced modules with script execution
                if module.type == ModuleType.ADVANCED:
                    module_content = self._process_advanced_module(
                        module, 
                        module_content,
                        conversation_id,
                        persona_id,
                        db_session,
                        trigger_context,
                        warnings,
                        current_provider,
                        current_provider_settings,
                        current_chat_controls
                    )
                
                # Recursively resolve the module content
                resolved_content = self._resolve_recursive(
                    module_content, 
                    warnings, 
                    resolved_modules, 
                    depth + 1,
                    conversation_id=conversation_id,
                    persona_id=persona_id,
                    db_session=db_session,
                    trigger_context=trigger_context,
                    current_provider=current_provider,
                    current_provider_settings=current_provider_settings,
                    current_chat_controls=current_chat_controls
                )
                
                # Replace module reference with resolved content
                resolved_template = resolved_template.replace(module_ref, resolved_content)
                
                # Track successfully resolved module
                if module_name not in resolved_modules:
                    resolved_modules.append(module_name)
                
            finally:
                # Remove from resolution stack
                self._resolution_stack.discard(module_name)
        
        return resolved_template
    
    def _parse_module_references(self, template: str) -> List[str]:
        """
        Parse @module_name references from template.
        
        Args:
            template: Template string to parse
            
        Returns:
            List of unique module names found (without @ prefix)
        """
        if not template:
            return []
        
        # Find all @module_name patterns
        matches = re.findall(MODULE_NAME_PATTERN, template)
        
        # Return unique module names
        return list(set(matches))
    
    def _get_modules_by_names(self, module_names: List[str]) -> List[Module]:
        """
        Retrieve modules from database by their names.
        
        Args:
            module_names: List of module names to retrieve
            
        Returns:
            List of Module objects found in database
        """
        if not module_names:
            return []
        
        # Get database session
        db = self.db_session
        if db is None:
            db = next(get_db())
        
        try:
            # Query modules by name (only active modules)
            modules = db.query(Module).filter(
                Module.name.in_(module_names),
                Module.is_active == True
            ).all()
            
            return modules
            
        except Exception as e:
            logger.error(f"Database error retrieving modules: {e}")
            return []
    
    def _process_advanced_module(
        self,
        module: Module,
        module_content: str,
        conversation_id: Optional[str],
        persona_id: Optional[str],
        db_session: Optional[Session],
        trigger_context: Optional[Dict[str, Any]],
        warnings: List[ModuleResolutionWarning],
        current_provider: Optional[str] = None,
        current_provider_settings: Optional[Dict[str, Any]] = None,
        current_chat_controls: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Process advanced module with script execution and ${variable} resolution.
        
        Args:
            module: The advanced module to process
            module_content: The module's content template
            conversation_id: Conversation ID for script context
            persona_id: Persona ID for script context  
            db_session: Database session for script context
            trigger_context: Trigger context for script execution
            warnings: List to collect warnings
            current_provider: Current chat session provider ("ollama" or "openai")
            current_provider_settings: Current provider connection settings
            current_chat_controls: Current chat control parameters
            
        Returns:
            Module content with ${variable} references resolved
        """
        try:
            # Check trigger pattern if specified
            if module.trigger_pattern:
                should_execute = TriggerMatcher.should_execute(
                    module.trigger_pattern, 
                    trigger_context or {}
                )
                if not should_execute:
                    logger.debug(f"Advanced module '{module.name}' trigger not matched")
                    return module_content  # Return content with unresolved variables
            
            # Skip script execution if no script is provided
            if not module.script or not module.script.strip():
                logger.debug(f"Advanced module '{module.name}' has no script")
                # For AFTER timing, still resolve variables with previous state or empty
                if module.timing == ExecutionTiming.AFTER:
                    return self._resolve_variables_with_previous_state(
                        module_content, module, conversation_id
                    )
                return module_content
            
            # Create execution context - allow some scripts to run without full context
            # We need at least a db_session to run any script
            if not db_session:
                logger.warning(f"Advanced module '{module.name}' missing database session")
                warnings.append(ModuleResolutionWarning(
                    module_name=module.name,
                    warning_type="missing_context", 
                    message=f"Advanced module '{module.name}' requires database session"
                ))
                return module_content
            
            # Create context with whatever we have - scripts will handle missing context gracefully
            context = ScriptExecutionContext(
                conversation_id=conversation_id,  # May be None
                persona_id=persona_id,  # May be None
                db_session=db_session,
                trigger_data=trigger_context or {},
                current_provider=current_provider,
                current_provider_settings=current_provider_settings,
                current_chat_controls=current_chat_controls
            )
            
            # Set current module information for reflection safety
            context.current_module_id = module.name
            context.current_timing = module.timing
            
            # Sync module resolution stack for reflection safety
            context.module_resolution_stack = list(self._resolution_stack)
            
            # Handle AFTER timing differently - use previous state during template resolution
            if module.timing == ExecutionTiming.AFTER:
                resolved_content = self._resolve_variables_with_previous_state(
                    module_content, module, conversation_id
                )
                logger.debug(f"Advanced module '{module.name}' with AFTER timing - using previous state")
                return resolved_content
            else:
                # BEFORE and CUSTOM timing - execute immediately
                script_engine = ScriptEngine()
                result = script_engine.execute_script(
                    module.script,
                    {"ctx": context}
                )
                
                if not result.success:
                    logger.error(f"Script execution failed for module '{module.name}': {result.error_message}")
                    warnings.append(ModuleResolutionWarning(
                        module_name=module.name,
                        warning_type="script_execution_failed",
                        message=f"Script execution failed: {result.error_message}"
                    ))
                    return module_content  # Return content with unresolved variables
                
                # Resolve ${variable} references in module content
                resolved_content = self._resolve_variables(module_content, result.outputs)
            
            logger.debug(f"Advanced module '{module.name}' processed successfully")
            return resolved_content
            
        except Exception as e:
            logger.error(f"Unexpected error processing advanced module '{module.name}': {e}")
            warnings.append(ModuleResolutionWarning(
                module_name=module.name,
                warning_type="processing_error",
                message=f"Unexpected error: {str(e)}"
            ))
            return module_content
    
    def _resolve_variables_with_previous_state(
        self, 
        content: str, 
        module: Module, 
        conversation_id: Optional[str]
    ) -> str:
        """
        Resolve ${variable} references using previous execution state for AFTER timing modules.
        
        Args:
            content: Content with ${variable} references
            module: The module being processed
            conversation_id: ID of the conversation for state lookup
            
        Returns:
            Content with variables resolved using previous state or empty strings
        """
        previous_outputs = {}
        if (module.extra_data and 
            isinstance(module.extra_data, dict) and 
            conversation_id and
            'conversation_states' in module.extra_data):
            
            conversation_states = module.extra_data.get('conversation_states', {})
            if conversation_id in conversation_states:
                previous_outputs = conversation_states[conversation_id]

        return self._resolve_variables(content, previous_outputs)
    
    def _resolve_variables(self, content: str, script_outputs: Dict[str, Any]) -> str:
        """
        Resolve ${variable} references in content using script outputs.
        
        Args:
            content: Content with ${variable} references
            script_outputs: Dictionary of variable names and values from script
            
        Returns:
            Content with variables resolved
        """
        # Always process variables, even if script_outputs is empty
        # This ensures unresolved variables become empty strings
        
        resolved_content = content
        
        # Find all ${variable} patterns
        variable_matches = re.findall(VARIABLE_PATTERN, content)
        
        for var_name in variable_matches:
            variable_ref = f"${{{var_name}}}"
            if var_name in script_outputs:
                variable_value = str(script_outputs[var_name])
                resolved_content = resolved_content.replace(variable_ref, variable_value)
                logger.debug(f"Resolved variable {variable_ref} -> {variable_value}")
            else:
                # Replace unresolved variables with empty strings
                resolved_content = resolved_content.replace(variable_ref, "")
                logger.debug(f"Resolved unresolved variable {variable_ref} -> (empty string)")
        
        return resolved_content
    
    def execute_after_timing_modules(
        self,
        persona_id: Optional[str],
        conversation_id: Optional[str],
        db_session: Optional[Session] = None,
        trigger_context: Optional[Dict[str, Any]] = None,
        current_provider: Optional[str] = None,
        current_provider_settings: Optional[Dict[str, Any]] = None,
        current_chat_controls: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute all AFTER timing modules for a persona and store their results.
        
        This should be called after the AI response is generated to update
        the stored state for AFTER timing modules.
        
        Args:
            persona_id: ID of the persona to get modules for
            conversation_id: ID of the conversation for context
            db_session: Database session
            trigger_context: Trigger context for script execution
            current_provider: Current provider for AI generation
            current_provider_settings: Current provider settings
            current_chat_controls: Current chat controls
            
        Returns:
            A list of dictionaries, where each dictionary contains the execution
            results (outputs) of a single module.
        """
        if not persona_id or not db_session:
            logger.warning("Cannot execute AFTER timing modules without persona_id and db_session")
            return []
        
        all_results: List[Dict[str, Any]] = []
        
        try:
            # Get all AFTER timing modules for this persona
            from app.models import Persona
            persona = db_session.query(Persona).filter(
                Persona.id == persona_id,
                Persona.is_active == True
            ).first()
            
            if not persona or not persona.template:
                return []
            
            # Find all module references in the persona template
            module_names = self._parse_module_references(persona.template)
            if not module_names:
                return []
            
            # Get modules from database
            modules = self._get_modules_by_names(module_names)
            after_modules = [m for m in modules if m.type == ModuleType.ADVANCED and m.timing == ExecutionTiming.AFTER]
            
            if not after_modules:
                return []
            
            logger.info(f"Executing {len(after_modules)} AFTER timing modules for persona {persona_id}")
            
            # Execute each AFTER module and store results
            for module in after_modules:
                try:
                    execution_result = self._execute_and_store_after_module(
                        module, conversation_id, persona_id, db_session, trigger_context,
                        current_provider, current_provider_settings, current_chat_controls
                    )
                    if execution_result:
                        all_results.append({
                            "module_name": module.name,
                            "outputs": execution_result
                        })
                except Exception as e:
                    logger.error(f"Error executing AFTER module '{module.name}': {e}")
                    continue
            
            return all_results
                    
        except Exception as e:
            logger.error(f"Error in execute_after_timing_modules: {e}")
            return []
    
    def _execute_and_store_after_module(
        self,
        module: Module,
        conversation_id: Optional[str],
        persona_id: Optional[str],
        db_session: Session,
        trigger_context: Optional[Dict[str, Any]],
        current_provider: Optional[str],
        current_provider_settings: Optional[Dict[str, Any]],
        current_chat_controls: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Execute a single AFTER timing module, store its results, and return them.
        
        Returns:
            A dictionary containing the script outputs, or None if execution fails or yields no output.
        """
        try:
            # Check trigger pattern if specified
            if module.trigger_pattern:
                should_execute = TriggerMatcher.should_execute(
                    module.trigger_pattern, 
                    trigger_context or {}
                )
                if not should_execute:
                    logger.debug(f"AFTER module '{module.name}' trigger not matched")
                    return None
            
            # Skip if no script
            if not module.script or not module.script.strip():
                return None
            
            # Create execution context
            context = ScriptExecutionContext(
                conversation_id=conversation_id,
                persona_id=persona_id,
                db_session=db_session,
                trigger_data=trigger_context or {},
                current_provider=current_provider,
                current_provider_settings=current_provider_settings,
                current_chat_controls=current_chat_controls
            )
            
            # Execute script
            script_engine = ScriptEngine()
            result = script_engine.execute_script(
                module.script,
                {"ctx": context}
            )
            
            logger.debug(f"AFTER module '{module.name}' executed - Success: {result.success}, Outputs: {len(result.outputs) if result.outputs else 0} variables")
            
            if result.success:
                if result.outputs:
                    # Store the results in module's extra_data
                    if not module.extra_data:
                        module.extra_data = {}
                    if 'conversation_states' not in module.extra_data:
                        module.extra_data['conversation_states'] = {}
                    
                    # Store outputs for this conversation
                    if conversation_id:
                        module.extra_data['conversation_states'][conversation_id] = result.outputs
                        
                        # Force SQLAlchemy to detect JSON field changes
                        from sqlalchemy.orm.attributes import flag_modified
                        flag_modified(module, 'extra_data')
                        
                        # Commit the changes to database
                        db_session.add(module)
                        db_session.flush()
                        db_session.commit()
                        db_session.refresh(module)
                        
                        logger.debug(f"Stored AFTER module '{module.name}' results for conversation {conversation_id}")
                    
                    return result.outputs
                else:
                    logger.warning(f"AFTER module '{module.name}' produced no outputs")
                    return None
            else:
                logger.error(f"AFTER module '{module.name}' execution failed: {getattr(result, 'error_message', 'Unknown error')}")
                return None
                
        except Exception as e:
            logger.error(f"Error executing and storing AFTER module '{module.name}': {e}")
            return None
    
    @staticmethod
    def validate_module_name(name: str) -> bool:
        """
        Validate that a module name follows the required format.
        
        Rules:
        - Only lowercase letters, numbers, and underscores
        - Must start with a letter
        - Max length 50 characters
        
        Args:
            name: Module name to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not name:
            return False
        
        if len(name) > MODULE_NAME_MAX_LENGTH:
            return False
        
        # Check pattern: starts with letter, contains only a-z, 0-9, _
        pattern = r'^[a-z][a-z0-9_]*$'
        return bool(re.match(pattern, name))


# Convenience function for standalone usage
def resolve_template(template: str, db_session: Optional[Session] = None) -> TemplateResolutionResult:
    """
    Convenience function to resolve a template.
    
    If db_session is not provided, a new session will be obtained and closed.
    """
    local_db_session = None
    try:
        if db_session is None:
            local_db_session = next(get_db())
            resolver = ModuleResolver(local_db_session)
        else:
            resolver = ModuleResolver(db_session)
        
        return resolver.resolve_template(template)
    finally:
        if local_db_session:
            local_db_session.close()