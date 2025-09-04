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
        current_chat_controls: Optional[Dict[str, Any]] = None
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
        
        logger.debug(f"Found {len(stage1_modules)} modules for Stage 1")
        
        # Resolve modules in template
        return self._resolve_modules_in_template(
            template=template,
            modules=stage1_modules,
            warnings=warnings,
            resolved_modules=resolved_modules,
            conversation_id=conversation_id,
            persona_id=persona_id,
            db_session=db,
            trigger_context=trigger_context,
            current_provider=current_provider,
            current_provider_settings=current_provider_settings,
            current_chat_controls=current_chat_controls
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
        
        # TODO: Add logic for previous POST_RESPONSE results from conversation state
        # This would check ConversationState for stored POST_RESPONSE results
        
        return False