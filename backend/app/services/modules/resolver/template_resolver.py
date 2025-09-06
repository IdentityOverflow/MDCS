"""
Template resolution handler for stages 1 and 2.

Handles the resolution of simple modules, IMMEDIATE non-AI modules, 
and IMMEDIATE AI-powered modules to prepare templates for main AI response.
"""

import logging
import time
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session

from ....database.connection import get_db
from ..stages import Stage1Executor, Stage2Executor
from ..stages.base_stage import ModuleResolutionWarning

from .result_models import StagedTemplateResolutionResult
from .session_manager import ResolverSessionManager
from .execution_utils import ExecutionTimer, StageErrorHandler

logger = logging.getLogger(__name__)


class TemplateResolver:
    """
    Handles template resolution for stages 1 and 2.
    
    Stage 1: Simple + IMMEDIATE Non-AI + Previous POST_RESPONSE
    Stage 2: IMMEDIATE AI-powered modules
    """
    
    def __init__(self, db_session: Optional[Session] = None, session_manager: Optional[ResolverSessionManager] = None):
        """
        Initialize template resolver.
        
        Args:
            db_session: Optional database session
            session_manager: Optional session manager for cancellation support
        """
        self.db_session = db_session
        self.session_manager = session_manager
        
        # Initialize stage executors
        self.stage1 = Stage1Executor(db_session)
        self.stage2 = Stage2Executor(db_session)
        
        # Initialize utilities
        self.timer = ExecutionTimer()
        self.error_handler = StageErrorHandler()
    
    async def resolve_template_stages_1_and_2(
        self, 
        template: str,
        conversation_id: Optional[str] = None,
        persona_id: Optional[str] = None,
        db_session: Optional[Session] = None,
        trigger_context: Optional[Dict[str, Any]] = None,
        current_provider: Optional[str] = None,
        current_provider_settings: Optional[Dict[str, Any]] = None,
        current_chat_controls: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> StagedTemplateResolutionResult:
        """
        Execute Stage 1 and Stage 2 of template resolution.
        
        Stage 1: Resolve simple modules, IMMEDIATE non-AI modules, and previous POST_RESPONSE results
        Stage 2: Resolve IMMEDIATE modules that require AI inference
        
        Args:
            template: The template string containing @module_name references
            conversation_id: Optional conversation ID for advanced module context
            persona_id: Optional persona ID for advanced module context
            db_session: Optional database session for advanced module context
            trigger_context: Optional trigger context for advanced modules
            current_provider: Current chat session provider ("ollama" or "openai")
            current_provider_settings: Current provider connection settings  
            current_chat_controls: Current chat control parameters
            session_id: Optional session ID for cancellation support
            
        Returns:
            StagedTemplateResolutionResult with resolved template and metadata
        """
        logger.debug("Starting template resolution: Stages 1 and 2")
        
        # Check for cancellation before starting
        if self.session_manager:
            self.session_manager.check_cancellation(session_id)
        
        # Initialize tracking variables
        warnings: List[ModuleResolutionWarning] = []
        resolved_modules: List[str] = []
        stages_executed: List[int] = []
        stage_timings: Dict[int, float] = {}
        
        # Use provided session or get default
        db = db_session or next(get_db()) if self.db_session is None else self.db_session
        
        current_template = template
        
        # Stage 1: Simple + IMMEDIATE Non-AI + Previous POST_RESPONSE
        current_template, stage1_timing = await self._execute_stage1(
            template=current_template,
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
        
        if stage1_timing is not None:
            stage_timings[1] = stage1_timing
            stages_executed.append(1)
        
        # Check for cancellation between stages
        if self.session_manager:
            self.session_manager.check_cancellation(session_id)
        
        # Stage 2: IMMEDIATE AI-powered modules
        current_template, stage2_timing = await self._execute_stage2(
            template=current_template,
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
        
        if stage2_timing is not None:
            stage_timings[2] = stage2_timing
            stages_executed.append(2)
        
        result = StagedTemplateResolutionResult(
            resolved_template=current_template,
            warnings=warnings,
            resolved_modules=resolved_modules,
            stages_executed=stages_executed
        )
        
        logger.debug(f"Template resolution completed, {len(resolved_modules)} modules resolved")
        return result
    
    async def _execute_stage1(
        self,
        template: str,
        warnings: List[ModuleResolutionWarning],
        resolved_modules: List[str],
        conversation_id: Optional[str],
        persona_id: Optional[str],
        db_session: Session,
        trigger_context: Optional[Dict[str, Any]],
        current_provider: Optional[str],
        current_provider_settings: Optional[Dict[str, Any]],
        current_chat_controls: Optional[Dict[str, Any]],
        session_id: Optional[str]
    ) -> tuple[str, Optional[float]]:
        """Execute Stage 1 with error handling and timing."""
        
        with self.timer.time_stage(1) as stage_timer:
            try:
                result_template = self.stage1.execute_stage(
                    template=template,
                    warnings=warnings,
                    resolved_modules=resolved_modules,
                    conversation_id=conversation_id,
                    persona_id=persona_id,
                    db_session=db_session,
                    trigger_context=trigger_context,
                    current_provider=current_provider,
                    current_provider_settings=current_provider_settings,
                    current_chat_controls=current_chat_controls,
                    session_id=session_id
                )
                elapsed_time = stage_timer.elapsed or 0.0
                logger.debug(f"Stage 1 completed in {elapsed_time:.3f}s")
                return result_template, stage_timer.elapsed
                
            except Exception as e:
                self.error_handler.handle_stage_error(1, e, warnings)
                return template, None  # Return original template on error
    
    async def _execute_stage2(
        self,
        template: str,
        warnings: List[ModuleResolutionWarning],
        resolved_modules: List[str],
        conversation_id: Optional[str],
        persona_id: Optional[str],
        db_session: Session,
        trigger_context: Optional[Dict[str, Any]],
        current_provider: Optional[str],
        current_provider_settings: Optional[Dict[str, Any]],
        current_chat_controls: Optional[Dict[str, Any]],
        session_id: Optional[str]
    ) -> tuple[str, Optional[float]]:
        """Execute Stage 2 with error handling and timing."""
        
        with self.timer.time_stage(2) as stage_timer:
            try:
                result_template = self.stage2.execute_stage(
                    template=template,
                    warnings=warnings,
                    resolved_modules=resolved_modules,
                    conversation_id=conversation_id,
                    persona_id=persona_id,
                    db_session=db_session,
                    trigger_context=trigger_context,
                    current_provider=current_provider,
                    current_provider_settings=current_provider_settings,
                    current_chat_controls=current_chat_controls,
                    session_id=session_id
                )
                elapsed_time = stage_timer.elapsed or 0.0
                logger.debug(f"Stage 2 completed in {elapsed_time:.3f}s")
                return result_template, stage_timer.elapsed
                
            except Exception as e:
                self.error_handler.handle_stage_error(2, e, warnings)
                return template, None  # Return original template on error