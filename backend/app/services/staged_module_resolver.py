"""
Staged Module Resolution Service for the Cognitive Engine.

Implements the 5-stage execution pipeline to replace the old BEFORE/AFTER timing system:
- Stage 1: Simple modules + IMMEDIATE Non-AI + Previous POST_RESPONSE results
- Stage 2: IMMEDIATE AI-powered modules
- Stage 3: Main AI response generation (handled by caller)
- Stage 4: POST_RESPONSE Non-AI modules
- Stage 5: POST_RESPONSE AI-powered modules

This provides clear execution order, identifiable stages, and ordered processing
to avoid race conditions.
"""

import re
import logging
from typing import List, Dict, Set, Optional, Any, Tuple
from dataclasses import dataclass
from sqlalchemy.orm import Session
from enum import Enum

from app.models import Module, ModuleType, ExecutionContext, ConversationState
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


class ExecutionStage(Enum):
    """Enumeration of template resolution stages."""
    STAGE1 = 1  # Simple + IMMEDIATE Non-AI + Previous POST_RESPONSE
    STAGE2 = 2  # IMMEDIATE AI-powered
    STAGE4 = 4  # POST_RESPONSE Non-AI
    STAGE5 = 5  # POST_RESPONSE AI-powered


@dataclass
class ModuleResolutionWarning:
    """Warning information for module resolution issues."""
    module_name: str
    warning_type: str  # 'module_not_found', 'circular_dependency', 'max_depth_exceeded'
    message: str
    stage: Optional[int] = None


@dataclass
class StagedTemplateResolutionResult:
    """Result of staged template resolution with content and warnings."""
    resolved_template: str
    warnings: List[ModuleResolutionWarning]
    resolved_modules: List[str]  # List of successfully resolved module names
    stages_executed: List[int]  # List of stages that were executed


@dataclass
class PostResponseExecutionResult:
    """Result of POST_RESPONSE module execution."""
    module_name: str
    stage: int  # 4 or 5
    variables: Dict[str, Any]
    execution_metadata: Dict[str, Any]
    success: bool
    error_message: Optional[str] = None


class StagedModuleResolver:
    """
    Service for staged module resolution implementing the 5-stage execution pipeline.
    
    Replaces the old ModuleResolver with clear execution stages:
    - Stage 1: Template preparation with simple modules and immediate non-AI execution
    - Stage 2: Pre-response AI processing for modules requiring AI inference
    - Stage 4: Post-response processing without AI
    - Stage 5: Post-response AI analysis and reflection
    """
    
    def __init__(self, db_session: Optional[Session] = None):
        """
        Initialize the staged module resolver.
        
        Args:
            db_session: Optional database session. If not provided, will get one from connection pool.
        """
        self.db_session = db_session
        self._resolution_stack: Set[str] = set()  # Track modules being resolved to detect cycles
    
    def resolve_template_stage1_and_stage2(
        self, 
        template: str,
        conversation_id: Optional[str] = None,
        persona_id: Optional[str] = None,
        db_session: Optional[Session] = None,
        trigger_context: Optional[Dict[str, Any]] = None,
        current_provider: Optional[str] = None,
        current_provider_settings: Optional[Dict[str, Any]] = None,
        current_chat_controls: Optional[Dict[str, Any]] = None
    ) -> StagedTemplateResolutionResult:
        """
        Execute Stage 1 and Stage 2 of template resolution.
        
        Stage 1: Resolve simple modules, IMMEDIATE non-AI modules, and previous POST_RESPONSE results
        Stage 2: Resolve IMMEDIATE modules that require AI inference
        
        This prepares the complete template for main AI response generation (Stage 3).
        
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
            StagedTemplateResolutionResult with resolved content and execution info
        """
        if not template:
            return StagedTemplateResolutionResult(
                resolved_template="",
                warnings=[],
                resolved_modules=[],
                stages_executed=[]
            )
        
        warnings: List[ModuleResolutionWarning] = []
        resolved_modules: List[str] = []
        stages_executed: List[int] = []
        
        # Reset resolution stack for new template
        self._resolution_stack = set()
        
        try:
            # Handle escaped modules
            template_with_placeholders, escaped_placeholders = self._handle_escaped_modules(template)
            
            # Stage 1: Simple modules + IMMEDIATE Non-AI + Previous POST_RESPONSE
            stage1_template = self._execute_stage1(
                template_with_placeholders, warnings, resolved_modules,
                conversation_id, persona_id, db_session, trigger_context,
                current_provider, current_provider_settings, current_chat_controls
            )
            stages_executed.append(1)
            
            # Stage 2: IMMEDIATE AI-powered modules
            stage2_template = self._execute_stage2(
                stage1_template, warnings, resolved_modules,
                conversation_id, persona_id, db_session, trigger_context,
                current_provider, current_provider_settings, current_chat_controls
            )
            stages_executed.append(2)
            
            # Restore escaped modules
            final_template = self._restore_escaped_modules(stage2_template, escaped_placeholders)
            
            return StagedTemplateResolutionResult(
                resolved_template=final_template,
                warnings=warnings,
                resolved_modules=list(set(resolved_modules)),  # Remove duplicates
                stages_executed=stages_executed
            )
            
        except Exception as e:
            logger.error(f"Unexpected error during staged template resolution: {e}")
            warnings.append(ModuleResolutionWarning(
                module_name="",
                warning_type="resolution_error",
                message=f"Unexpected error during resolution: {str(e)}"
            ))
            
            return StagedTemplateResolutionResult(
                resolved_template=template,  # Return original on error
                warnings=warnings,
                resolved_modules=resolved_modules,
                stages_executed=stages_executed
            )
    
    def execute_post_response_modules(
        self,
        persona_id: Optional[str],
        conversation_id: Optional[str],
        db_session: Optional[Session] = None,
        trigger_context: Optional[Dict[str, Any]] = None,
        current_provider: Optional[str] = None,
        current_provider_settings: Optional[Dict[str, Any]] = None,
        current_chat_controls: Optional[Dict[str, Any]] = None
    ) -> List[PostResponseExecutionResult]:
        """
        Execute Stage 4 and Stage 5: POST_RESPONSE modules after AI response is generated.
        
        Stage 4: Execute POST_RESPONSE modules that don't require AI inference
        Stage 5: Execute POST_RESPONSE modules that require AI inference (reflection, etc.)
        
        Args:
            persona_id: ID of the persona to get modules for
            conversation_id: ID of the conversation for context
            db_session: Database session
            trigger_context: Trigger context for script execution
            current_provider: Current provider for AI generation
            current_provider_settings: Current provider settings
            current_chat_controls: Current chat controls
            
        Returns:
            List of PostResponseExecutionResult objects containing execution results
        """
        if not persona_id or not db_session:
            logger.warning("Cannot execute POST_RESPONSE modules without persona_id and db_session")
            return []
        
        all_results: List[PostResponseExecutionResult] = []
        
        try:
            # Get POST_RESPONSE modules for this persona
            post_response_modules = self._get_post_response_modules_for_persona(persona_id, db_session)
            
            if not post_response_modules:
                logger.debug(f"No POST_RESPONSE modules found for persona {persona_id}")
                return []
            
            logger.info(f"Executing {len(post_response_modules)} POST_RESPONSE modules for persona {persona_id}")
            
            # Stage 4: Non-AI POST_RESPONSE modules
            stage4_modules = [m for m in post_response_modules if not m.requires_ai_inference]
            for module in stage4_modules:
                result = self._execute_post_response_module(
                    module, 4, conversation_id, persona_id, db_session,
                    trigger_context, current_provider, current_provider_settings, current_chat_controls
                )
                if result:
                    all_results.append(result)
            
            # Stage 5: AI-powered POST_RESPONSE modules
            stage5_modules = [m for m in post_response_modules if m.requires_ai_inference]
            for module in stage5_modules:
                result = self._execute_post_response_module(
                    module, 5, conversation_id, persona_id, db_session,
                    trigger_context, current_provider, current_provider_settings, current_chat_controls
                )
                if result:
                    all_results.append(result)
            
            logger.info(f"Completed POST_RESPONSE execution: {len(all_results)} successful executions")
            return all_results
                    
        except Exception as e:
            logger.error(f"Error in execute_post_response_modules: {e}")
            return []
    
    def _execute_stage1(
        self,
        template: str,
        warnings: List[ModuleResolutionWarning],
        resolved_modules: List[str],
        conversation_id: Optional[str],
        persona_id: Optional[str],
        db_session: Optional[Session],
        trigger_context: Optional[Dict[str, Any]],
        current_provider: Optional[str],
        current_provider_settings: Optional[Dict[str, Any]],
        current_chat_controls: Optional[Dict[str, Any]]
    ) -> str:
        """
        Execute Stage 1: Simple modules + IMMEDIATE Non-AI + Previous POST_RESPONSE results.
        
        Returns:
            Template with Stage 1 modules resolved
        """
        logger.debug("Executing Stage 1: Simple + IMMEDIATE Non-AI + Previous POST_RESPONSE")
        
        # Get modules for Stage 1 (priority 1)
        stage1_modules = self._get_modules_for_stage(1, persona_id, db_session)
        
        return self._resolve_modules_in_template(
            template, stage1_modules, warnings, resolved_modules, 1,
            conversation_id, persona_id, db_session, trigger_context,
            current_provider, current_provider_settings, current_chat_controls
        )
    
    def _execute_stage2(
        self,
        template: str,
        warnings: List[ModuleResolutionWarning],
        resolved_modules: List[str],
        conversation_id: Optional[str],
        persona_id: Optional[str],
        db_session: Optional[Session],
        trigger_context: Optional[Dict[str, Any]],
        current_provider: Optional[str],
        current_provider_settings: Optional[Dict[str, Any]],
        current_chat_controls: Optional[Dict[str, Any]]
    ) -> str:
        """
        Execute Stage 2: IMMEDIATE AI-powered modules.
        
        Returns:
            Template with Stage 2 modules resolved
        """
        logger.debug("Executing Stage 2: IMMEDIATE AI-powered modules")
        
        # Get modules for Stage 2 (priority 2)
        stage2_modules = self._get_modules_for_stage(2, persona_id, db_session)
        
        return self._resolve_modules_in_template(
            template, stage2_modules, warnings, resolved_modules, 2,
            conversation_id, persona_id, db_session, trigger_context,
            current_provider, current_provider_settings, current_chat_controls
        )
    
    def _get_modules_for_stage(
        self,
        stage: int,
        persona_id: Optional[str],
        db_session: Optional[Session]
    ) -> List[Module]:
        """
        Get modules that should execute in the specified stage.
        
        Args:
            stage: Stage number (1, 2, 4, or 5)
            persona_id: Persona ID to filter modules
            db_session: Database session
            
        Returns:
            List of modules for the stage
        """
        if not db_session:
            db = next(get_db()) if self.db_session is None else self.db_session
        else:
            db = db_session
            
        try:
            # Get modules using the new method in Module model
            modules = Module.get_modules_for_stage(db, stage, persona_id)
            return modules.all()
        except Exception as e:
            logger.error(f"Error getting modules for stage {stage}: {e}")
            return []
    
    def _get_post_response_modules_for_persona(
        self,
        persona_id: str,
        db_session: Session
    ) -> List[Module]:
        """
        Get all POST_RESPONSE modules referenced in a persona's template.
        
        Args:
            persona_id: ID of the persona
            db_session: Database session
            
        Returns:
            List of POST_RESPONSE modules
        """
        try:
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
            
            # Get modules from database and filter for POST_RESPONSE
            modules = self._get_modules_by_names(module_names, db_session)
            return [m for m in modules if m.execution_context == ExecutionContext.POST_RESPONSE]
            
        except Exception as e:
            logger.error(f"Error getting POST_RESPONSE modules for persona {persona_id}: {e}")
            return []
    
    def _execute_post_response_module(
        self,
        module: Module,
        stage: int,
        conversation_id: Optional[str],
        persona_id: Optional[str],
        db_session: Session,
        trigger_context: Optional[Dict[str, Any]],
        current_provider: Optional[str],
        current_provider_settings: Optional[Dict[str, Any]],
        current_chat_controls: Optional[Dict[str, Any]]
    ) -> Optional[PostResponseExecutionResult]:
        """
        Execute a single POST_RESPONSE module and store its results.
        
        Returns:
            PostResponseExecutionResult or None if execution fails
        """
        try:
            # Check trigger pattern if specified
            if module.trigger_pattern:
                should_execute = TriggerMatcher.should_execute(
                    module.trigger_pattern, 
                    trigger_context or {}
                )
                if not should_execute:
                    logger.debug(f"POST_RESPONSE module '{module.name}' trigger not matched")
                    return None
            
            # Skip if no script
            if not module.script or not module.script.strip():
                logger.debug(f"POST_RESPONSE module '{module.name}' has no script")
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
            
            # Set current module information
            context.current_module_id = module.name
            context.current_timing = module.execution_context.value  # Pass the enum value
            
            # Execute script
            script_engine = ScriptEngine()
            result = script_engine.execute_script(
                module.script,
                {"ctx": context}
            )
            
            logger.debug(f"Stage {stage} module '{module.name}' executed - Success: {result.success}")
            
            if result.success and result.outputs:
                # Store the results in ConversationState table
                stage_name = f"stage{stage}"
                
                logger.info(f"POST_RESPONSE execution success for module '{module.name}': conversation_id={conversation_id}, variables={list(result.outputs.keys())}")
                
                if not conversation_id:
                    logger.error(f"Cannot store POST_RESPONSE results for module '{module.name}': missing conversation_id")
                    return PostResponseExecutionResult(
                        module_name=module.name,
                        stage=stage,
                        variables=result.outputs,
                        execution_metadata={
                            "success": False,
                            "error": "missing_conversation_id",
                            "execution_stage": stage
                        },
                        success=False,
                        error_message="Cannot store results: missing conversation_id"
                    )
                
                ConversationState.store_execution_result(
                    db_session,
                    conversation_id,
                    str(module.id),
                    stage_name,
                    result.outputs,
                    {
                        "success": True,
                        "execution_stage": stage,
                        "module_name": module.name,
                        "execution_time": result.execution_time_ms if hasattr(result, 'execution_time_ms') else None
                    }
                )
                
                logger.info(f"Successfully stored Stage {stage} module '{module.name}' results for conversation {conversation_id}")
                
                return PostResponseExecutionResult(
                    module_name=module.name,
                    stage=stage,
                    variables=result.outputs,
                    execution_metadata={
                        "success": True,
                        "execution_stage": stage
                    },
                    success=True
                )
            else:
                error_msg = getattr(result, 'error_message', 'No outputs produced') if result.success else getattr(result, 'error_message', 'Unknown error')
                logger.error(f"Stage {stage} module '{module.name}' execution failed: {error_msg}")
                
                return PostResponseExecutionResult(
                    module_name=module.name,
                    stage=stage,
                    variables={},
                    execution_metadata={
                        "success": False,
                        "execution_stage": stage
                    },
                    success=False,
                    error_message=error_msg
                )
                
        except Exception as e:
            logger.error(f"Error executing Stage {stage} module '{module.name}': {e}")
            return PostResponseExecutionResult(
                module_name=module.name,
                stage=stage,
                variables={},
                execution_metadata={
                    "success": False,
                    "execution_stage": stage
                },
                success=False,
                error_message=str(e)
            )
    
    def _resolve_modules_in_template(
        self,
        template: str,
        modules: List[Module],
        warnings: List[ModuleResolutionWarning],
        resolved_modules: List[str],
        stage: int,
        conversation_id: Optional[str],
        persona_id: Optional[str],
        db_session: Optional[Session],
        trigger_context: Optional[Dict[str, Any]],
        current_provider: Optional[str],
        current_provider_settings: Optional[Dict[str, Any]],
        current_chat_controls: Optional[Dict[str, Any]]
    ) -> str:
        """
        Resolve specific modules in a template.
        
        Returns:
            Template with specified modules resolved
        """
        if not modules:
            return template
        
        # Create lookup by module name
        modules_by_name = {module.name: module for module in modules}
        
        # Find module references in template
        module_names = self._parse_module_references(template)
        
        # Filter to only modules we have and are in this stage
        stage_module_names = [name for name in module_names if name in modules_by_name]
        
        if not stage_module_names:
            return template
        
        logger.debug(f"Stage {stage}: Resolving {len(stage_module_names)} modules: {stage_module_names}")
        
        resolved_template = template
        
        for module_name in stage_module_names:
            module_ref = f"@{module_name}"
            module = modules_by_name[module_name]
            
            # Check for circular dependency
            if module_name in self._resolution_stack:
                warnings.append(ModuleResolutionWarning(
                    module_name=module_name,
                    warning_type="circular_dependency",
                    message=f"Circular dependency detected with module '{module_name}'",
                    stage=stage
                ))
                continue
            
            # Add to resolution stack
            self._resolution_stack.add(module_name)
            
            try:
                module_content = self._process_module(
                    module, stage, conversation_id, persona_id, db_session,
                    trigger_context, warnings, current_provider,
                    current_provider_settings, current_chat_controls
                )
                
                # Replace module reference with resolved content
                resolved_template = resolved_template.replace(module_ref, module_content)
                
                # Track successfully resolved module
                if module_name not in resolved_modules:
                    resolved_modules.append(module_name)
                    
            finally:
                # Remove from resolution stack
                self._resolution_stack.discard(module_name)
        
        return resolved_template
    
    def _process_module(
        self,
        module: Module,
        stage: int,
        conversation_id: Optional[str],
        persona_id: Optional[str],
        db_session: Optional[Session],
        trigger_context: Optional[Dict[str, Any]],
        warnings: List[ModuleResolutionWarning],
        current_provider: Optional[str],
        current_provider_settings: Optional[Dict[str, Any]],
        current_chat_controls: Optional[Dict[str, Any]]
    ) -> str:
        """
        Process a module to get its resolved content.
        
        Returns:
            Resolved module content
        """
        try:
            module_content = module.content or ""
            
            # Simple modules - return content with recursive resolution
            if module.type == ModuleType.SIMPLE:
                # Check if the content has any @module_name references that need recursive resolution
                nested_modules = self._parse_module_references(module_content)
                if nested_modules:
                    # Get ALL modules for the stage (not filtered by persona) to allow recursive resolution
                    all_stage_modules = self._get_modules_for_stage(stage, None, db_session)
                    return self._resolve_modules_in_template(
                        module_content, all_stage_modules, warnings, [], stage,
                        conversation_id, persona_id, db_session, trigger_context,
                        current_provider, current_provider_settings, current_chat_controls
                    )
                else:
                    return module_content
            
            # Advanced modules - handle script execution and variable resolution
            if module.type == ModuleType.ADVANCED:
                return self._process_advanced_module(
                    module, module_content, stage, conversation_id, persona_id,
                    db_session, trigger_context, warnings, current_provider,
                    current_provider_settings, current_chat_controls
                )
            
            # Unknown module type
            logger.warning(f"Unknown module type for '{module.name}': {module.type}")
            return module_content
            
        except Exception as e:
            logger.error(f"Error processing module '{module.name}': {e}")
            warnings.append(ModuleResolutionWarning(
                module_name=module.name,
                warning_type="processing_error",
                message=f"Error processing module: {str(e)}",
                stage=stage
            ))
            return module.content or ""
    
    def _process_advanced_module(
        self,
        module: Module,
        module_content: str,
        stage: int,
        conversation_id: Optional[str],
        persona_id: Optional[str],
        db_session: Optional[Session],
        trigger_context: Optional[Dict[str, Any]],
        warnings: List[ModuleResolutionWarning],
        current_provider: Optional[str],
        current_provider_settings: Optional[Dict[str, Any]],
        current_chat_controls: Optional[Dict[str, Any]]
    ) -> str:
        """
        Process advanced module with script execution and ${variable} resolution.
        
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
            
            # For Stage 1, check if this is a POST_RESPONSE module with previous state
            if stage == 1 and module.execution_context == ExecutionContext.POST_RESPONSE:
                return self._resolve_variables_with_previous_state(
                    module_content, module, conversation_id, db_session
                )
            
            # Skip script execution if no script is provided
            if not module.script or not module.script.strip():
                logger.debug(f"Advanced module '{module.name}' has no script")
                return module_content
            
            # Create execution context
            if not db_session:
                logger.warning(f"Advanced module '{module.name}' missing database session")
                warnings.append(ModuleResolutionWarning(
                    module_name=module.name,
                    warning_type="missing_context", 
                    message=f"Advanced module '{module.name}' requires database session",
                    stage=stage
                ))
                return module_content
            
            context = ScriptExecutionContext(
                conversation_id=conversation_id,
                persona_id=persona_id,
                db_session=db_session,
                trigger_data=trigger_context or {},
                current_provider=current_provider,
                current_provider_settings=current_provider_settings,
                current_chat_controls=current_chat_controls
            )
            
            # Set current module information
            context.current_module_id = module.name
            context.current_timing = module.execution_context.value
            context.module_resolution_stack = list(self._resolution_stack)
            
            # Execute script
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
                    message=f"Script execution failed: {result.error_message}",
                    stage=stage
                ))
                return module_content
            
            # Resolve ${variable} references in module content
            resolved_content = self._resolve_variables(module_content, result.outputs)
            
            logger.debug(f"Advanced module '{module.name}' processed successfully in stage {stage}")
            return resolved_content
            
        except Exception as e:
            logger.error(f"Unexpected error processing advanced module '{module.name}': {e}")
            warnings.append(ModuleResolutionWarning(
                module_name=module.name,
                warning_type="processing_error",
                message=f"Unexpected error: {str(e)}",
                stage=stage
            ))
            return module_content
    
    def _resolve_variables_with_previous_state(
        self, 
        content: str, 
        module: Module, 
        conversation_id: Optional[str],
        db_session: Optional[Session]
    ) -> str:
        """
        Resolve ${variable} references using previous POST_RESPONSE execution state.
        
        Args:
            content: Content with ${variable} references
            module: The module being processed
            conversation_id: ID of the conversation for state lookup
            db_session: Database session for state lookup
            
        Returns:
            Content with variables resolved using previous state or empty strings
        """
        previous_outputs = {}
        
        logger.info(f"POST_RESPONSE variable resolution for module '{module.name}': conversation_id={conversation_id}, db_session={db_session is not None}")
        
        if not conversation_id:
            logger.warning(f"POST_RESPONSE module '{module.name}' has no conversation_id - cannot retrieve previous state")
            return self._resolve_variables(content, previous_outputs)
        
        if not db_session:
            logger.warning(f"POST_RESPONSE module '{module.name}' has no db_session - cannot retrieve previous state")
            return self._resolve_variables(content, previous_outputs)
        
        try:
            # Get the latest state for this module in this conversation
            logger.debug(f"Looking up previous state: conversation_id={conversation_id}, module_id={module.id}")
            latest_state = ConversationState.get_latest_for_module(
                db_session, conversation_id, str(module.id)
            )
            if latest_state and latest_state.variables:
                previous_outputs = latest_state.variables
                logger.info(f"Found previous state for module '{module.name}': {len(previous_outputs)} variables: {list(previous_outputs.keys())}")
            else:
                logger.info(f"No previous state found for module '{module.name}' in conversation {conversation_id}")
        except Exception as e:
            logger.error(f"Error retrieving previous state for module '{module.name}': {e}")
        
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
    
    def _handle_escaped_modules(self, template: str) -> Tuple[str, Dict[str, str]]:
        """Handle escaped modules by temporarily replacing them."""
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
        return template_with_placeholders, escaped_placeholders
    
    def _restore_escaped_modules(self, template: str, escaped_placeholders: Dict[str, str]) -> str:
        """Restore escaped modules by replacing placeholders."""
        restored_template = template
        for placeholder, original in escaped_placeholders.items():
            restored_template = restored_template.replace(placeholder, original)
        return restored_template
    
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
    
    def _get_modules_by_names(self, module_names: List[str], db_session: Session) -> List[Module]:
        """
        Retrieve modules from database by their names.
        
        Args:
            module_names: List of module names to retrieve
            db_session: Database session
            
        Returns:
            List of Module objects found in database
        """
        if not module_names:
            return []
        
        try:
            # Query modules by name (only active modules)
            modules = db_session.query(Module).filter(
                Module.name.in_(module_names),
                Module.is_active == True
            ).all()
            
            return modules
            
        except Exception as e:
            logger.error(f"Database error retrieving modules: {e}")
            return []
    
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
def resolve_template_for_response(
    template: str, 
    conversation_id: Optional[str] = None,
    persona_id: Optional[str] = None,
    db_session: Optional[Session] = None
) -> StagedTemplateResolutionResult:
    """
    Convenience function to resolve a template for main AI response (Stage 1 + Stage 2).
    
    If db_session is not provided, a new session will be obtained and closed.
    """
    local_db_session = None
    try:
        if db_session is None:
            local_db_session = next(get_db())
            resolver = StagedModuleResolver(local_db_session)
        else:
            resolver = StagedModuleResolver(db_session)
        
        return resolver.resolve_template_stage1_and_stage2(
            template, conversation_id, persona_id, db_session or local_db_session
        )
    finally:
        if local_db_session:
            local_db_session.close()