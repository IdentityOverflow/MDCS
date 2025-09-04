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
            current_chat_controls=current_chat_controls
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
                    'response_metadata': trigger_context.get('response_metadata', {}) if trigger_context else {}
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