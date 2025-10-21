"""
Stage 1 Executor: Simple modules + IMMEDIATE Non-AI + Previous POST_RESPONSE results.

Handles the first stage of template resolution which includes:
- Simple text-based modules
- IMMEDIATE modules that don't require AI inference  
- Previous POST_RESPONSE module results from conversation state
"""

import logging
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session

from ....models import Module
from ....database.connection import get_db
from ..template_parser import TemplateParser
from .base_stage import BaseStageExecutor, ModuleResolutionWarning

logger = logging.getLogger(__name__)


class Stage1Executor(BaseStageExecutor):
    """
    Executes Stage 1 of the module resolution pipeline.
    
    Stage 1 processes:
    - Simple text modules (no AI inference required)
    - IMMEDIATE context modules that don't need AI
    - Previous POST_RESPONSE results stored in conversation state
    
    This prepares the template with basic content before AI-dependent modules.
    """
    
    STAGE_NUMBER = 1
    STAGE_NAME = "Simple + IMMEDIATE Non-AI + Previous POST_RESPONSE"

    async def execute_stage_async(
        self,
        template: str,
        warnings: List[ModuleResolutionWarning],
        resolved_modules: List[str],
        conversation_id: Optional[str] = None,
        persona_id: Optional[str] = None,
        db_session: Optional[Session] = None,
        trigger_context: Optional[Dict[str, Any]] = None,
        current_provider: Optional[str] = None,
        current_provider_settings: Optional[Dict[str, Any]] = None,
        current_chat_controls: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        cancellation_token: Optional[Any] = None
    ) -> str:
        """
        Execute Stage 1 module resolution asynchronously with cancellation support.

        Stage 1 typically doesn't have AI calls but needs async for cancellation checks.

        Args:
            template: Template string with module references
            warnings: List to collect resolution warnings
            resolved_modules: List to track successfully resolved modules
            conversation_id: Optional conversation context
            persona_id: Optional persona context
            db_session: Optional database session
            trigger_context: Optional trigger context for advanced modules
            current_provider: Current chat provider for context
            current_provider_settings: Provider settings for context
            current_chat_controls: Chat controls for context
            session_id: Optional session ID
            cancellation_token: Optional cancellation token for immediate cancellation

        Returns:
            Template with Stage 1 modules resolved
        """
        logger.debug("Executing Stage 1 asynchronously: Simple + IMMEDIATE Non-AI + Previous POST_RESPONSE")

        # Check cancellation at start
        if cancellation_token:
            cancellation_token.check_cancelled()

        # Get database session
        db = db_session or next(get_db()) if self.db_session is None else self.db_session

        # Get modules for Stage 1
        stage1_modules = self._get_modules_for_stage(db, persona_id)

        if not stage1_modules:
            logger.debug("No Stage 1 modules found")
            # Still need to check for POST_RESPONSE resolution
            return self._resolve_previous_post_response_results(
                template, conversation_id, db, resolved_modules, warnings
            )

        logger.debug(f"Found {len(stage1_modules)} modules for Stage 1: {[m.name for m in stage1_modules]}")

        # First, resolve any POST_RESPONSE module references
        current_template = self._resolve_previous_post_response_results(
            template, conversation_id, db, resolved_modules, warnings
        )
        logger.debug(f"After POST_RESPONSE resolution, resolved_modules: {resolved_modules}")

        # Check cancellation before module resolution
        if cancellation_token:
            cancellation_token.check_cancelled()

        # Then resolve regular Stage 1 modules asynchronously
        return await self._resolve_modules_async(
            template=current_template,
            modules=stage1_modules,
            warnings=warnings,
            resolved_modules=resolved_modules,
            conversation_id=conversation_id,
            persona_id=persona_id,
            db_session=db,
            trigger_context=trigger_context,
            current_provider=current_provider,
            current_provider_settings=current_provider_settings,
            current_chat_controls=current_chat_controls,
            session_id=session_id,
            cancellation_token=cancellation_token
        )

    async def _resolve_modules_async(
        self,
        template: str,
        modules: List[Module],
        warnings: List[ModuleResolutionWarning],
        resolved_modules: List[str],
        conversation_id: Optional[str],
        persona_id: Optional[str],
        db_session: Session,
        trigger_context: Optional[Dict[str, Any]],
        current_provider: Optional[str],
        current_provider_settings: Optional[Dict[str, Any]],
        current_chat_controls: Optional[Dict[str, Any]],
        session_id: Optional[str],
        cancellation_token: Optional[Any]
    ) -> str:
        """
        Resolve Stage 1 modules asynchronously with cancellation checks.

        Args:
            template: Template to resolve
            modules: List of modules to process
            (other args same as execute_stage_async)

        Returns:
            Resolved template string
        """
        resolved_template = template

        for module in modules:
            # Check cancellation before each module
            if cancellation_token:
                cancellation_token.check_cancelled()

            # Find module reference in template
            module_ref = f"@{module.name}"
            if module_ref not in resolved_template:
                continue

            logger.debug(f"Resolving Stage 1 module: {module.name}")

            try:
                # Process module (Stage 1 modules are typically simple/non-AI)
                module_content = await self._process_module_async(
                    module=module,
                    conversation_id=conversation_id,
                    persona_id=persona_id,
                    db_session=db_session,
                    trigger_context=trigger_context,
                    warnings=warnings,
                    current_provider=current_provider,
                    current_provider_settings=current_provider_settings,
                    current_chat_controls=current_chat_controls,
                    session_id=session_id,
                    cancellation_token=cancellation_token
                )

                # Replace module reference
                resolved_template = resolved_template.replace(module_ref, module_content)

                # Track resolved module
                if module.name not in resolved_modules:
                    resolved_modules.append(module.name)

            except Exception as e:
                logger.error(f"Error processing Stage 1 module '{module.name}': {e}")
                warnings.append(ModuleResolutionWarning(
                    module_name=module.name,
                    warning_type="execution_error",
                    message=f"Stage 1 module execution failed: {str(e)}",
                    stage=self.STAGE_NUMBER
                ))

        return resolved_template

    async def _process_module_async(
        self,
        module: Module,
        conversation_id: Optional[str] = None,
        persona_id: Optional[str] = None,
        db_session: Optional[Session] = None,
        trigger_context: Optional[Dict[str, Any]] = None,
        warnings: Optional[List[ModuleResolutionWarning]] = None,
        current_provider: Optional[str] = None,
        current_provider_settings: Optional[Dict[str, Any]] = None,
        current_chat_controls: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        cancellation_token: Optional[Any] = None
    ) -> str:
        """
        Process a Stage 1 module asynchronously.

        Stage 1 modules are typically simple or non-AI advanced modules.

        Args:
            module: Module to process
            (other args for context)

        Returns:
            Resolved module content as string
        """
        from ....models import ModuleType
        from ..execution import SimpleExecutor, ScriptExecutor

        # Check cancellation before processing
        if cancellation_token:
            cancellation_token.check_cancelled()

        try:
            if module.type == ModuleType.SIMPLE:
                # Simple text module (synchronous)
                executor = SimpleExecutor()
                return executor.execute(module, {})

            elif module.type == ModuleType.ADVANCED:
                # Advanced script module - use async executor
                executor = ScriptExecutor()

                context = {
                    'conversation_id': conversation_id,
                    'persona_id': persona_id,
                    'db_session': db_session,
                    'trigger_context': trigger_context or {},
                    'current_provider': current_provider,
                    'current_provider_settings': current_provider_settings or {},
                    'current_chat_controls': current_chat_controls or {},
                    'stage': self.STAGE_NUMBER,
                    'stage_name': self.STAGE_NAME,
                    'session_id': session_id,
                    'cancellation_token': cancellation_token
                }

                # Execute asynchronously
                return await executor.execute_async(module, context)

            else:
                logger.warning(f"Unknown module type: {module.type}")
                return f"[Unknown module type: {module.type}]"

        except Exception as e:
            logger.error(f"Error executing Stage 1 module '{module.name}': {e}")
            if warnings is not None:
                warnings.append(ModuleResolutionWarning(
                    module_name=module.name,
                    warning_type="execution_error",
                    message=f"Stage 1 module execution failed: {str(e)}",
                    stage=self.STAGE_NUMBER
                ))
            return f"[Error in Stage 1 module {module.name}: {str(e)}]"

    def execute_stage(
        self,
        template: str,
        warnings: List[ModuleResolutionWarning], 
        resolved_modules: List[str],
        conversation_id: Optional[str] = None,
        persona_id: Optional[str] = None,
        db_session: Optional[Session] = None,
        trigger_context: Optional[Dict[str, Any]] = None,
        current_provider: Optional[str] = None,
        current_provider_settings: Optional[Dict[str, Any]] = None,
        current_chat_controls: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> str:
        """
        Execute Stage 1 module resolution.
        
        Args:
            template: Template string with module references
            warnings: List to collect resolution warnings
            resolved_modules: List to track successfully resolved modules
            conversation_id: Optional conversation context
            persona_id: Optional persona context
            db_session: Optional database session
            trigger_context: Optional trigger context for advanced modules
            current_provider: Current chat provider for context
            current_provider_settings: Provider settings for context
            current_chat_controls: Chat controls for context
            
        Returns:
            Template with Stage 1 modules resolved
        """
        logger.debug("Executing Stage 1: Simple + IMMEDIATE Non-AI + Previous POST_RESPONSE")
        
        # Get database session
        db = db_session or next(get_db()) if self.db_session is None else self.db_session
        
        # Get modules for Stage 1
        stage1_modules = self._get_modules_for_stage(db, persona_id)
        
        if not stage1_modules:
            logger.debug("No Stage 1 modules found")
            return template
        
        logger.debug(f"Found {len(stage1_modules)} modules for Stage 1: {[m.name for m in stage1_modules]}")
        
        # First, resolve any POST_RESPONSE module references (both with and without conversation state)
        current_template = self._resolve_previous_post_response_results(
            template, conversation_id, db, resolved_modules, warnings
        )
        logger.debug(f"After POST_RESPONSE resolution, resolved_modules: {resolved_modules}")
        
        # Then resolve regular Stage 1 modules in the updated template
        return self._resolve_modules_in_template(
            template=current_template,
            modules=stage1_modules,
            warnings=warnings,
            resolved_modules=resolved_modules,
            conversation_id=conversation_id,
            persona_id=persona_id,
            db_session=db,
            trigger_context=trigger_context,
            current_provider=current_provider,
            current_provider_settings=current_provider_settings,
            current_chat_controls=current_chat_controls,
            session_id=session_id
        )
    
    def _get_modules_for_stage(self, db_session: Session, persona_id: Optional[str]) -> List[Module]:
        """
        Get modules that should execute in Stage 1.
        
        Args:
            db_session: Database session
            persona_id: Optional persona ID to filter modules
            
        Returns:
            List of modules for Stage 1
        """
        try:
            # Get modules using the Model method for stage-based filtering
            modules_query = Module.get_modules_for_stage(db_session, self.STAGE_NUMBER, persona_id)
            return modules_query.all()
        except Exception as e:
            logger.error(f"Error getting modules for Stage 1: {e}")
            return []
    
    def _should_execute_module(self, module: Module) -> bool:
        """
        Determine if a module should execute in Stage 1.
        
        Stage 1 criteria:
        - Simple modules (no AI required)
        - IMMEDIATE modules that don't require AI inference
        - Modules with ExecutionContext.IMMEDIATE and requires_ai_inference=False
        
        Args:
            module: Module to check
            
        Returns:
            True if module should execute in Stage 1
        """
        from ....models import ExecutionContext, ModuleType
        
        # Simple modules always execute in Stage 1
        if module.type == ModuleType.SIMPLE:
            return True
        
        # Advanced modules with IMMEDIATE context but no AI requirement
        if (module.type == ModuleType.ADVANCED and 
            module.execution_context == ExecutionContext.IMMEDIATE and
            not module.requires_ai_inference):
            return True
        
        # Previous POST_RESPONSE results are handled in _resolve_previous_post_response_results
        # This method only determines if a module should execute in Stage 1
        
        return False
    
    def _resolve_previous_post_response_results(
        self,
        template: str,
        conversation_id: Optional[str],
        db_session: Session,
        resolved_modules: List[str],
        warnings: List[ModuleResolutionWarning]
    ) -> str:
        """
        Resolve module references that have previous POST_RESPONSE results stored.
        
        This checks ConversationState for modules that executed in previous
        POST_RESPONSE stages and replaces their @module_name references with
        the stored variable outputs.
        
        Args:
            template: Template string with @module_name references
            conversation_id: Conversation ID to look up state
            db_session: Database session
            resolved_modules: List to append resolved module names to
            warnings: List to append warnings to
            
        Returns:
            Template with previous POST_RESPONSE results resolved
        """
        if not conversation_id:
            return template
            
        try:
            from ....models.conversation_state import ConversationState
            from ....models import Module, ExecutionContext
            from ..template_parser import TemplateParser
            
            # Get all module references in the template
            module_references = TemplateParser.parse_module_references(template)
            if not module_references:
                return template
                
            # Get all conversation states for this conversation
            conversation_states = ConversationState.get_for_conversation(db_session, conversation_id).all()
            logger.debug(f"Found {len(conversation_states)} conversation states for conversation {conversation_id}")
            
            current_template = template
            
            # Handle modules that have no conversation state (first message case)
            # These should resolve to empty string entirely, but only if they are POST_RESPONSE modules
            if not conversation_states:
                # Check each module reference to see if it's a POST_RESPONSE module
                for module_ref in module_references:
                    # Check if this is a POST_RESPONSE module
                    module = db_session.query(Module).filter(Module.name == module_ref).first()
                    if module and module.execution_context == ExecutionContext.POST_RESPONSE:
                        # This is a POST_RESPONSE module with no conversation state - resolve to empty string
                        module_pattern = f"@{module_ref}"
                        if module_pattern in current_template:
                            current_template = current_template.replace(module_pattern, "")
                            resolved_modules.append(module_ref)
                            logger.debug(f"Resolved POST_RESPONSE module '{module_ref}' to empty string (no conversation state)")
                    else:
                        logger.debug(f"Skipping non-POST_RESPONSE module '{module_ref}' for normal Stage 1 processing")
                return current_template
            
            # Track which modules have conversation state
            modules_with_state = {state.module.name for state in conversation_states if state.module}
            logger.debug(f"Modules with conversation state: {modules_with_state}")
            logger.debug(f"All module references in template: {module_references}")
            
            for state in conversation_states:
                module = state.module
                if not module or module.name not in module_references:
                    continue
                    
                # Get the output from the stored variables
                variables = state.variables or {}
                logger.debug(f"Module '{module.name}' has stored variables: {variables}")
                
                # For modules with ${variable} syntax, we need to resolve the template
                if module.content and '${' in module.content:
                    try:
                        logger.debug(f"Resolving template '{module.content}' with variables: {variables}")
                        resolved_content = self._resolve_template_variables(module.content, variables)
                        logger.debug(f"Resolved POST_RESPONSE module '{module.name}' to: {resolved_content}")
                    except Exception as e:
                        logger.warning(f"Failed to resolve variables for module '{module.name}': {e}")
                        resolved_content = module.content  # Fallback to original content
                else:
                    # Simple content or no variable substitution needed
                    resolved_content = module.content or ""
                    logger.debug(f"Module '{module.name}' has no template variables, using content: {resolved_content}")
                
                # Replace @module_name with resolved content
                module_pattern = f"@{module.name}"
                if module_pattern in current_template:
                    current_template = current_template.replace(module_pattern, resolved_content)
                    resolved_modules.append(module.name)
                    logger.debug(f"Resolved previous POST_RESPONSE result for module '{module.name}'")
            
            # Handle POST_RESPONSE modules that are referenced but don't have conversation state
            # These should resolve to empty string
            for module_ref in module_references:
                if module_ref not in modules_with_state:
                    # Check if this is a POST_RESPONSE module
                    module = db_session.query(Module).filter(Module.name == module_ref).first()
                    if module and module.execution_context == ExecutionContext.POST_RESPONSE:
                        # This is a POST_RESPONSE module without stored state - resolve to empty string
                        module_pattern = f"@{module_ref}"
                        if module_pattern in current_template:
                            current_template = current_template.replace(module_pattern, "")
                            resolved_modules.append(module_ref)
                            logger.debug(f"Resolved POST_RESPONSE module '{module_ref}' to empty string (no stored state)")
                    else:
                        logger.debug(f"Skipping non-POST_RESPONSE module '{module_ref}' (no stored state) for normal Stage 1 processing")
            
            return current_template
            
        except Exception as e:
            logger.error(f"Error resolving previous POST_RESPONSE results: {e}")
            warnings.append(ModuleResolutionWarning(
                module_name="post_response_resolution",
                warning_type="previous_results_error", 
                message=f"Failed to resolve previous POST_RESPONSE results: {str(e)}",
                stage=1
            ))
            return template
    
    def _resolve_template_variables(self, template: str, variables: Dict[str, Any]) -> str:
        """
        Resolve ${variable} references in a template using provided variables.
        
        Args:
            template: Template string with ${variable} syntax
            variables: Dictionary of variable name -> value mappings
            
        Returns:
            Resolved template string
        """
        import re
        
        def replace_variable(match):
            var_name = match.group(1)
            return str(variables.get(var_name, f"${{{var_name}}}"))  # Keep unresolved if not found
        
        # Replace all ${variable} patterns
        return re.sub(r'\$\{([^}]+)\}', replace_variable, template)