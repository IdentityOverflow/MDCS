"""
Stage 4 Executor: POST_RESPONSE Non-AI modules.

Handles modules that execute after the main AI response and don't require AI inference.
These modules typically process the response or update state without additional AI calls.
"""

import logging
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session

from ....models import Module
from ....database.connection import get_db
from .base_stage import BaseStageExecutor, ModuleResolutionWarning

logger = logging.getLogger(__name__)


class Stage4Executor(BaseStageExecutor):
    """
    Executes Stage 4 of the module resolution pipeline.
    
    Stage 4 processes POST_RESPONSE modules that don't require AI inference.
    These modules typically:
    - Update conversation state
    - Log response metrics
    - Process response content
    - Trigger external integrations
    
    This stage runs after the main AI response (Stage 3) but before
    AI-powered post-processing (Stage 5).
    """
    
    STAGE_NUMBER = 4
    STAGE_NAME = "POST_RESPONSE Non-AI modules"
    
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
        response_metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Execute Stage 4 non-AI post-response module resolution.
        
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
            ai_response: The AI response from Stage 3 for processing
            response_metadata: Metadata about the AI response
            
        Returns:
            Template with Stage 4 modules resolved
        """
        logger.debug("Executing Stage 4: POST_RESPONSE Non-AI modules")
        
        # Get database session
        db = db_session or next(get_db()) if self.db_session is None else self.db_session
        
        # Get modules for Stage 4
        stage4_modules = self._get_modules_for_stage(db, persona_id)
        
        if not stage4_modules:
            logger.debug("No Stage 4 modules found")
            return template
        
        logger.debug(f"Found {len(stage4_modules)} modules for Stage 4")
        
        # Add response context for post-response modules
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
            modules=stage4_modules,
            warnings=warnings,
            resolved_modules=resolved_modules,
            conversation_id=conversation_id,
            persona_id=persona_id,
            db_session=db,
            trigger_context=enhanced_trigger_context,
            current_provider=current_provider,
            current_provider_settings=current_provider_settings,
            current_chat_controls=current_chat_controls
        )
    
    def _get_modules_for_stage(self, db_session: Session, persona_id: Optional[str]) -> List[Module]:
        """
        Get modules that should execute in Stage 4.
        
        Args:
            db_session: Database session
            persona_id: Optional persona ID to filter modules
            
        Returns:
            List of modules for Stage 4
        """
        try:
            # Get modules using the Model method for stage-based filtering
            modules_query = Module.get_modules_for_stage(db_session, self.STAGE_NUMBER, persona_id)
            return modules_query.all()
        except Exception as e:
            logger.error(f"Error getting modules for Stage 4: {e}")
            return []
    
    def _should_execute_module(self, module: Module) -> bool:
        """
        Determine if a module should execute in Stage 4.
        
        Stage 4 criteria:
        - Advanced modules with POST_RESPONSE context that don't require AI inference
        - Modules with ExecutionContext.POST_RESPONSE and requires_ai_inference=False
        
        Args:
            module: Module to check
            
        Returns:
            True if module should execute in Stage 4
        """
        from ....models import ExecutionContext, ModuleType
        
        # Advanced modules with POST_RESPONSE context that don't need AI
        if (module.module_type == ModuleType.ADVANCED and 
            module.execution_context == ExecutionContext.POST_RESPONSE and
            not module.requires_ai_inference):
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
        Process a Stage 4 module without AI inference.
        
        Stage 4 modules focus on post-response processing without additional AI calls.
        
        Args:
            module: Module to process
            conversation_id: Optional conversation context
            persona_id: Optional persona context
            db_session: Optional database session
            trigger_context: Optional trigger context (includes ai_response)
            warnings: Optional warnings list
            current_provider: Current provider for context
            current_provider_settings: Provider settings for context
            current_chat_controls: Chat controls for context
            
        Returns:
            Resolved module content as string
        """
        from ....models import ModuleType
        from ..execution import SimpleExecutor, ScriptExecutor
        
        try:
            if module.module_type == ModuleType.SIMPLE:
                # Simple text module
                executor = SimpleExecutor()
                return executor.execute(module, {})
            
            elif module.module_type == ModuleType.ADVANCED:
                # Advanced script module without AI
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
                    'response_metadata': trigger_context.get('response_metadata', {}) if trigger_context else {}
                }
                return executor.execute(module, context)
            
            else:
                logger.warning(f"Unknown module type: {module.module_type}")
                return f"[Unknown module type: {module.module_type}]"
                
        except Exception as e:
            logger.error(f"Error executing Stage 4 module '{module.name}': {e}")
            if warnings is not None:
                warnings.append(ModuleResolutionWarning(
                    module_name=module.name,
                    warning_type="execution_error",
                    message=f"Stage 4 module execution failed: {str(e)}",
                    stage=self.STAGE_NUMBER
                ))
            return f"[Error in Stage 4 module {module.name}: {str(e)}]"