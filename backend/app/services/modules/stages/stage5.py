"""
Stage 5 Executor: POST_RESPONSE AI-powered modules.

Handles modules that execute after the main AI response and require AI inference.
These modules typically analyze the response, provide AI-powered insights, or generate
additional AI content based on the conversation outcome.
"""

import logging
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session

from ....models import Module
from ....database.connection import get_db
from .base_stage import BaseStageExecutor, ModuleResolutionWarning

logger = logging.getLogger(__name__)


class Stage5Executor(BaseStageExecutor):
    """
    Executes Stage 5 of the module resolution pipeline.
    
    Stage 5 processes POST_RESPONSE modules that require AI inference.
    These modules typically:
    - Analyze AI response quality using AI
    - Generate AI-powered insights about the conversation
    - Provide AI feedback or suggestions
    - Perform AI-based response enhancement
    
    This is the final stage of the resolution pipeline and runs after
    all other processing is complete.
    """
    
    STAGE_NUMBER = 5
    STAGE_NAME = "POST_RESPONSE AI-powered modules"

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
        ai_response: Optional[str] = None,
        response_metadata: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        cancellation_token: Optional[Any] = None
    ) -> str:
        """
        Execute Stage 5 AI-powered post-response module resolution asynchronously.

        This async version enables immediate cancellation detection during
        module execution, especially for modules using ctx.generate() or ctx.reflect().

        Args:
            template: Template string with module references
            warnings: List to collect resolution warnings
            resolved_modules: List to track successfully resolved modules
            conversation_id: Optional conversation context
            persona_id: Optional persona context
            db_session: Optional database session
            trigger_context: Optional trigger context for advanced modules
            current_provider: Current chat provider for AI inference
            current_provider_settings: Provider settings for AI calls
            current_chat_controls: Chat controls for AI parameters
            ai_response: The AI response from Stage 3 for analysis
            response_metadata: Metadata about the AI response
            session_id: Optional session ID
            cancellation_token: Cancellation token for immediate cancellation

        Returns:
            Template with Stage 5 modules resolved
        """
        logger.debug("Executing Stage 5 asynchronously: POST_RESPONSE AI-powered modules")

        # Check cancellation at start
        if cancellation_token:
            cancellation_token.check_cancelled()

        # Get database session
        db = db_session or next(get_db()) if self.db_session is None else self.db_session

        # Get modules for Stage 5
        stage5_modules = self._get_modules_for_stage(db, persona_id)

        if not stage5_modules:
            logger.debug("No Stage 5 modules found")
            return template

        logger.debug(f"Found {len(stage5_modules)} modules for Stage 5")

        # Add response context for post-response AI modules
        enhanced_trigger_context = (trigger_context or {}).copy()
        enhanced_trigger_context.update({
            'ai_response': ai_response,
            'response_metadata': response_metadata or {},
            'stage': self.STAGE_NUMBER,
            'stage_name': self.STAGE_NAME
        })

        # Check cancellation before module resolution
        if cancellation_token:
            cancellation_token.check_cancelled()

        # Resolve modules asynchronously
        return await self._resolve_modules_async(
            template=template,
            modules=stage5_modules,
            warnings=warnings,
            resolved_modules=resolved_modules,
            conversation_id=conversation_id,
            persona_id=persona_id,
            db_session=db,
            trigger_context=enhanced_trigger_context,
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
        Resolve modules asynchronously with frequent cancellation checks.

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

            # POST_RESPONSE modules execute based on ExecutionContext timing, not template references
            # They may or may not be referenced in the template with @module_name
            # If referenced, we replace it; if not, we just execute them for side effects
            module_ref = f"@{module.name}"
            module_in_template = module_ref in resolved_template

            logger.debug(f"Resolving Stage 5 module: {module.name} (in_template={module_in_template})")

            try:
                # Process module asynchronously
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

                # Replace module reference if it was in the template
                # Otherwise the module just executed for side effects (e.g., logging, state changes)
                if module_in_template:
                    resolved_template = resolved_template.replace(module_ref, module_content)
                    logger.debug(f"Replaced {module_ref} in template")
                else:
                    logger.debug(f"Module {module.name} executed for side effects (not in template)")

                # Track resolved module
                if module.name not in resolved_modules:
                    resolved_modules.append(module.name)

            except Exception as e:
                logger.error(f"Error processing Stage 5 module '{module.name}': {e}")
                warnings.append(ModuleResolutionWarning(
                    module_name=module.name,
                    warning_type="execution_error",
                    message=f"Stage 5 module execution failed: {str(e)}",
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
        Process a Stage 5 module asynchronously with AI inference support.

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
                # Simple text module (shouldn't be in Stage 5, but handle gracefully)
                executor = SimpleExecutor()
                return executor.execute(module, {})

            elif module.type == ModuleType.ADVANCED:
                # Advanced script module - use async executor
                executor = ScriptExecutor()

                context = {
                    'module_name': module.name,
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
            logger.error(f"Error executing Stage 5 module '{module.name}': {e}")
            if warnings is not None:
                warnings.append(ModuleResolutionWarning(
                    module_name=module.name,
                    warning_type="execution_error",
                    message=f"Stage 5 module execution failed: {str(e)}",
                    stage=self.STAGE_NUMBER
                ))
            return f"[Error in Stage 5 module {module.name}: {str(e)}]"

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
        ai_response: Optional[str] = None,
        response_metadata: Optional[Dict[str, Any]] = None,
        cancellation_token: Optional[Any] = None
    ) -> str:
        """
        Execute Stage 5 AI-powered post-response module resolution.
        
        Args:
            template: Template string with module references
            warnings: List to collect resolution warnings
            resolved_modules: List to track successfully resolved modules
            conversation_id: Optional conversation context
            persona_id: Optional persona context
            db_session: Optional database session
            trigger_context: Optional trigger context for advanced modules
            current_provider: Current chat provider for AI inference
            current_provider_settings: Provider settings for AI calls
            current_chat_controls: Chat controls for AI parameters
            ai_response: The AI response from Stage 3 for analysis
            response_metadata: Metadata about the AI response
            
        Returns:
            Template with Stage 5 modules resolved
        """
        logger.debug("Executing Stage 5: POST_RESPONSE AI-powered modules")
        
        # Get database session
        db = db_session or next(get_db()) if self.db_session is None else self.db_session
        
        # Get modules for Stage 5
        stage5_modules = self._get_modules_for_stage(db, persona_id)
        
        if not stage5_modules:
            logger.debug("No Stage 5 modules found")
            return template
        
        logger.debug(f"Found {len(stage5_modules)} modules for Stage 5")
        
        # Add response context for post-response AI modules
        enhanced_trigger_context = (trigger_context or {}).copy()
        enhanced_trigger_context.update({
            'ai_response': ai_response,
            'response_metadata': response_metadata or {},
            'stage': self.STAGE_NUMBER,
            'stage_name': self.STAGE_NAME
        })
        
        # Resolve modules in template
        return self._resolve_modules_in_template(
            template=template,
            modules=stage5_modules,
            warnings=warnings,
            resolved_modules=resolved_modules,
            conversation_id=conversation_id,
            persona_id=persona_id,
            db_session=db,
            trigger_context=enhanced_trigger_context,
            current_provider=current_provider,
            current_provider_settings=current_provider_settings,
            current_chat_controls=current_chat_controls,
            cancellation_token=cancellation_token
        )
    
    def _get_modules_for_stage(self, db_session: Session, persona_id: Optional[str]) -> List[Module]:
        """
        Get modules that should execute in Stage 5.
        
        Args:
            db_session: Database session
            persona_id: Optional persona ID to filter modules
            
        Returns:
            List of modules for Stage 5
        """
        try:
            # Get modules using the Model method for stage-based filtering
            modules_query = Module.get_modules_for_stage(db_session, self.STAGE_NUMBER, persona_id)
            return modules_query.all()
        except Exception as e:
            logger.error(f"Error getting modules for Stage 5: {e}")
            return []
    
    def _should_execute_module(self, module: Module) -> bool:
        """
        Determine if a module should execute in Stage 5.
        
        Stage 5 criteria:
        - Advanced modules with POST_RESPONSE context that require AI inference
        - Modules with ExecutionContext.POST_RESPONSE and requires_ai_inference=True
        
        Args:
            module: Module to check
            
        Returns:
            True if module should execute in Stage 5
        """
        from ....models import ExecutionContext, ModuleType
        
        # Advanced modules with POST_RESPONSE context that require AI
        if (module.type == ModuleType.ADVANCED and 
            module.execution_context == ExecutionContext.POST_RESPONSE and
            module.requires_ai_inference):
            return True
        
        return False
    
    def _process_module(
        self,
        module: Module,
        conversation_id: Optional[str] = None,
        persona_id: Optional[str] = None,
        db_session: Optional[Session] = None,
        trigger_context: Optional[Dict[str, Any]] = None,
        warnings: Optional[List[ModuleResolutionWarning]] = None,
        current_provider: Optional[str] = None,
        current_provider_settings: Optional[Dict[str, Any]] = None,
        current_chat_controls: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Process a Stage 5 module with AI inference support.
        
        Stage 5 modules have full access to the AI response and can make additional AI calls.
        
        Args:
            module: Module to process
            conversation_id: Optional conversation context
            persona_id: Optional persona context
            db_session: Optional database session
            trigger_context: Optional trigger context (includes ai_response)
            warnings: Optional warnings list
            current_provider: Current provider for AI inference
            current_provider_settings: Provider settings for AI calls
            current_chat_controls: Chat controls for AI parameters
            
        Returns:
            Resolved module content as string
        """
        from ....models import ModuleType
        from ..execution import SimpleExecutor, ScriptExecutor, AIExecutor
        
        try:
            if module.type == ModuleType.SIMPLE:
                # Simple text module (shouldn't be in Stage 5, but handle gracefully)
                executor = SimpleExecutor()
                return executor.execute(module, {})
            
            elif module.type == ModuleType.ADVANCED:
                # Advanced script module with AI support
                if module.requires_ai_inference:
                    # Use AI-enabled executor
                    executor = AIExecutor(current_provider, current_provider_settings)
                else:
                    # Use standard script executor
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
                    'ai_response': trigger_context.get('ai_response') if trigger_context else None,
                    'response_metadata': trigger_context.get('response_metadata', {}) if trigger_context else {},
                    'cancellation_token': cancellation_token
                }
                return executor.execute(module, context)
            
            else:
                logger.warning(f"Unknown module type: {module.type}")
                return f"[Unknown module type: {module.type}]"
                
        except Exception as e:
            logger.error(f"Error executing Stage 5 module '{module.name}': {e}")
            if warnings is not None:
                warnings.append(ModuleResolutionWarning(
                    module_name=module.name,
                    warning_type="execution_error",
                    message=f"Stage 5 module execution failed: {str(e)}",
                    stage=self.STAGE_NUMBER
                ))
            return f"[Error in Stage 5 module {module.name}: {str(e)}]"