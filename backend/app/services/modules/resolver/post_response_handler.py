"""
Post-response processing handler for stages 4 and 5.

Handles POST_RESPONSE module execution after the main AI response has been generated.
"""

import logging
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session

from ....database.connection import get_db
from ..stages import Stage4Executor, Stage5Executor
from ..stages.base_stage import ModuleResolutionWarning

from .result_models import PostResponseExecutionResult
from .session_manager import ResolverSessionManager
from .execution_utils import ExecutionTimer, StageErrorHandler

logger = logging.getLogger(__name__)


class PostResponseHandler:
    """
    Handles post-response processing for stages 4 and 5.
    
    Stage 4: POST_RESPONSE Non-AI modules
    Stage 5: POST_RESPONSE AI-powered modules
    """
    
    def __init__(self, db_session: Optional[Session] = None, session_manager: Optional[ResolverSessionManager] = None):
        """
        Initialize post-response handler.
        
        Args:
            db_session: Optional database session
            session_manager: Optional session manager for cancellation support
        """
        self.db_session = db_session
        self.session_manager = session_manager
        
        # Initialize stage executors
        self.stage4 = Stage4Executor(db_session)
        self.stage5 = Stage5Executor(db_session)
        
        # Initialize utilities
        self.timer = ExecutionTimer()
        self.error_handler = StageErrorHandler()
    
    async def execute_post_response_stages(
        self,
        template: str,
        ai_response: str,
        session_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        persona_id: Optional[str] = None,
        db_session: Optional[Session] = None,
        trigger_context: Optional[Dict[str, Any]] = None,
        current_provider: Optional[str] = None,
        current_provider_settings: Optional[Dict[str, Any]] = None,
        current_chat_controls: Optional[Dict[str, Any]] = None,
        response_metadata: Optional[Dict[str, Any]] = None
    ) -> List[PostResponseExecutionResult]:
        """
        Execute Stage 4 and Stage 5 post-response processing.
        
        Args:
            template: Original template (for module discovery)
            ai_response: AI response from Stage 3
            session_id: Optional session ID for cancellation support
            conversation_id: Optional conversation ID
            persona_id: Optional persona ID  
            db_session: Optional database session
            trigger_context: Optional trigger context
            current_provider: AI provider for Stage 5
            current_provider_settings: Provider settings
            current_chat_controls: Chat controls
            response_metadata: Metadata from AI response
            
        Returns:
            List of PostResponseExecutionResult for each executed module
        """
        logger.debug("Starting post-response processing: Stages 4 and 5")
        
        # Check for cancellation before starting
        if self.session_manager:
            self.session_manager.check_cancellation(session_id)
        
        # Initialize tracking variables
        db = db_session or next(get_db()) if self.db_session is None else self.db_session
        warnings: List[ModuleResolutionWarning] = []
        resolved_modules: List[str] = []
        results: List[PostResponseExecutionResult] = []
        
        # Stage 4: POST_RESPONSE Non-AI modules
        stage4_results = await self._execute_stage4(
            template=template,
            warnings=warnings,
            resolved_modules=resolved_modules,
            conversation_id=conversation_id,
            persona_id=persona_id,
            db_session=db,
            trigger_context=trigger_context,
            current_provider=current_provider,
            current_provider_settings=current_provider_settings,
            current_chat_controls=current_chat_controls,
            ai_response=ai_response,
            response_metadata=response_metadata,
            session_id=session_id
        )
        results.extend(stage4_results)
        
        # Check for cancellation between Stage 4 and Stage 5
        if self.session_manager:
            self.session_manager.check_cancellation(session_id)
        
        # Stage 5: POST_RESPONSE AI-powered modules
        stage5_results = await self._execute_stage5(
            template=template,
            warnings=warnings,
            resolved_modules=resolved_modules,
            conversation_id=conversation_id,
            persona_id=persona_id,
            db_session=db,
            trigger_context=trigger_context,
            current_provider=current_provider,
            current_provider_settings=current_provider_settings,
            current_chat_controls=current_chat_controls,
            ai_response=ai_response,
            response_metadata=response_metadata,
            session_id=session_id
        )
        results.extend(stage5_results)
        
        return results
    
    async def _execute_stage4(
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
        ai_response: str,
        response_metadata: Optional[Dict[str, Any]],
        session_id: Optional[str]
    ) -> List[PostResponseExecutionResult]:
        """Execute Stage 4 with error handling and timing."""
        
        results = []
        
        with self.timer.time_stage(4) as stage_timer:
            try:
                self.stage4.execute_stage(
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
                    ai_response=ai_response,
                    response_metadata=response_metadata
                )
                elapsed_time = stage_timer.elapsed or 0.0
                logger.debug(f"Stage 4 completed in {elapsed_time:.3f}s")
                
                # TODO: Convert stage execution results to PostResponseExecutionResult objects
                # For now, create placeholder results for each resolved module
                for module_name in resolved_modules:
                    if module_name not in [r.module_name for r in results]:  # Avoid duplicates
                        results.append(PostResponseExecutionResult(
                            module_name=module_name,
                            stage=4,
                            variables={},
                            execution_metadata={"timing": elapsed_time},
                            success=True
                        ))
                
            except Exception as e:
                self.error_handler.handle_stage_error(4, e, warnings)
                # Create error result
                results.append(PostResponseExecutionResult(
                    module_name="stage4_execution",
                    stage=4,
                    variables={},
                    execution_metadata={"error": str(e)},
                    success=False,
                    error_message=str(e)
                ))
        
        return results
    
    async def _execute_stage5(
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
        ai_response: str,
        response_metadata: Optional[Dict[str, Any]],
        session_id: Optional[str]
    ) -> List[PostResponseExecutionResult]:
        """Execute Stage 5 with error handling and timing."""
        
        results = []
        
        with self.timer.time_stage(5) as stage_timer:
            try:
                self.stage5.execute_stage(
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
                    ai_response=ai_response,
                    response_metadata=response_metadata
                )
                elapsed_time = stage_timer.elapsed or 0.0
                logger.debug(f"Stage 5 completed in {elapsed_time:.3f}s")
                
                # TODO: Convert stage execution results to PostResponseExecutionResult objects
                # For now, create placeholder results for each resolved module
                for module_name in resolved_modules:
                    if module_name not in [r.module_name for r in results]:  # Avoid duplicates
                        results.append(PostResponseExecutionResult(
                            module_name=module_name,
                            stage=5,
                            variables={},
                            execution_metadata={"timing": elapsed_time},
                            success=True
                        ))
                
            except Exception as e:
                self.error_handler.handle_stage_error(5, e, warnings)
                # Create error result
                results.append(PostResponseExecutionResult(
                    module_name="stage5_execution",
                    stage=5,
                    variables={},
                    execution_metadata={"error": str(e)},
                    success=False,
                    error_message=str(e)
                ))
        
        return results