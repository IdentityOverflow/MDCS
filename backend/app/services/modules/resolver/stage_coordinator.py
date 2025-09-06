"""
Stage coordination logic for orchestrating the complete 5-stage pipeline.

Handles the coordination between template resolution, AI response generation,
and post-response processing stages.
"""

import logging
import time
from typing import Dict, Optional, Any, AsyncIterator
from sqlalchemy.orm import Session

from ..stages import Stage3Executor
from .result_models import (
    StagedTemplateResolutionResult,
    CompleteResolutionResult,
    PostResponseExecutionResult
)
from .template_resolver import TemplateResolver
from .post_response_handler import PostResponseHandler
from .session_manager import ResolverSessionManager
from .execution_utils import ExecutionTimer, StageErrorHandler

logger = logging.getLogger(__name__)


class StageCoordinator:
    """
    Coordinates execution across all 5 stages of the pipeline.
    
    Orchestrates template resolution (stages 1-2), AI response generation (stage 3),
    and post-response processing (stages 4-5).
    """
    
    def __init__(self, db_session: Optional[Session] = None, session_manager: Optional[ResolverSessionManager] = None):
        """
        Initialize stage coordinator.
        
        Args:
            db_session: Optional database session
            session_manager: Optional session manager for cancellation support
        """
        self.db_session = db_session
        self.session_manager = session_manager
        
        # Initialize specialized handlers
        self.template_resolver = TemplateResolver(db_session, session_manager)
        self.post_response_handler = PostResponseHandler(db_session, session_manager)
        
        # Initialize stage 3 executor directly
        self.stage3 = Stage3Executor(db_session)
        
        # Initialize utilities
        self.timer = ExecutionTimer()
        self.error_handler = StageErrorHandler()
    
    async def execute_complete_pipeline(
        self,
        template: str,
        user_message: str,
        session_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        persona_id: Optional[str] = None,
        db_session: Optional[Session] = None,
        trigger_context: Optional[Dict[str, Any]] = None,
        current_provider: Optional[str] = None,
        current_provider_settings: Optional[Dict[str, Any]] = None,
        current_chat_controls: Optional[Dict[str, Any]] = None
    ) -> CompleteResolutionResult:
        """
        Execute the complete 5-stage resolution pipeline.
        
        Args:
            template: The template string containing @module_name references
            user_message: User's message to respond to
            session_id: Optional session ID for cancellation support
            conversation_id: Optional conversation ID
            persona_id: Optional persona ID
            db_session: Optional database session
            trigger_context: Optional trigger context
            current_provider: AI provider ("ollama" or "openai")
            current_provider_settings: Provider connection settings
            current_chat_controls: Chat control parameters
            
        Returns:
            CompleteResolutionResult with all stage results and timings
        """
        logger.debug("Starting complete 5-stage resolution pipeline")
        pipeline_start = time.time()
        stage_timings: Dict[int, float] = {}
        
        # Check for cancellation before starting pipeline
        if self.session_manager:
            self.session_manager.check_cancellation(session_id)
        
        # Stage 1 & 2: Template Resolution
        template_result = await self.template_resolver.resolve_template_stages_1_and_2(
            template=template,
            session_id=session_id,
            conversation_id=conversation_id,
            persona_id=persona_id,
            db_session=db_session,
            trigger_context=trigger_context,
            current_provider=current_provider,
            current_provider_settings=current_provider_settings,
            current_chat_controls=current_chat_controls
        )
        
        # Check for cancellation before Stage 3
        if self.session_manager:
            self.session_manager.check_cancellation(session_id)
        
        # Stage 3: Main AI Response Generation
        ai_response, ai_response_metadata, stage3_time = await self._execute_stage3(
            template_result=template_result,
            user_message=user_message,
            conversation_id=conversation_id,
            persona_id=persona_id,
            db_session=db_session,
            trigger_context=trigger_context,
            current_provider=current_provider,
            current_provider_settings=current_provider_settings,
            current_chat_controls=current_chat_controls
        )
        
        if stage3_time is not None:
            stage_timings[3] = stage3_time
            template_result.stages_executed.append(3)
        
        # Check for cancellation before post-response stages
        if self.session_manager:
            self.session_manager.check_cancellation(session_id)
            
        # Stages 4 & 5: Post-Response Processing
        post_response_results = await self.post_response_handler.execute_post_response_stages(
            template=template,
            ai_response=ai_response,
            session_id=session_id,
            conversation_id=conversation_id,
            persona_id=persona_id,
            db_session=db_session,
            trigger_context=trigger_context,
            current_provider=current_provider,
            current_provider_settings=current_provider_settings,
            current_chat_controls=current_chat_controls,
            response_metadata=ai_response_metadata
        )
        
        total_time = time.time() - pipeline_start
        
        return CompleteResolutionResult(
            template_resolution=template_result,
            ai_response=ai_response,
            ai_response_metadata=ai_response_metadata,
            post_response_results=post_response_results,
            total_execution_time=total_time,
            stage_timings=stage_timings
        )
    
    async def execute_stage3_streaming(
        self,
        template_result: StagedTemplateResolutionResult,
        user_message: str,
        conversation_id: Optional[str] = None,
        persona_id: Optional[str] = None,
        db_session: Optional[Session] = None,
        trigger_context: Optional[Dict[str, Any]] = None,
        current_provider: Optional[str] = None,
        current_provider_settings: Optional[Dict[str, Any]] = None,
        current_chat_controls: Optional[Dict[str, Any]] = None
    ) -> AsyncIterator[Any]:
        """
        Execute Stage 3 with streaming response.
        
        Args:
            template_result: Result from stages 1 and 2
            user_message: User's message to respond to
            
        Yields:
            Streaming response chunks
        """
        async for chunk in self.stage3.execute_stage_streaming(
            resolved_template=template_result.resolved_template,
            user_message=user_message,
            warnings=template_result.warnings,
            resolved_modules=template_result.resolved_modules,
            conversation_id=conversation_id,
            persona_id=persona_id,
            db_session=db_session,
            trigger_context=trigger_context,
            current_provider=current_provider,
            current_provider_settings=current_provider_settings,
            current_chat_controls=current_chat_controls
        ):
            yield chunk
    
    async def _execute_stage3(
        self,
        template_result: StagedTemplateResolutionResult,
        user_message: str,
        conversation_id: Optional[str],
        persona_id: Optional[str],
        db_session: Optional[Session],
        trigger_context: Optional[Dict[str, Any]],
        current_provider: Optional[str],
        current_provider_settings: Optional[Dict[str, Any]],
        current_chat_controls: Optional[Dict[str, Any]]
    ) -> tuple[str, Dict[str, Any], Optional[float]]:
        """Execute Stage 3 with error handling and timing."""
        
        with self.timer.time_stage(3) as stage_timer:
            try:
                ai_response_obj = await self.stage3.execute_stage_async(
                    resolved_template=template_result.resolved_template,
                    user_message=user_message,
                    warnings=template_result.warnings,
                    resolved_modules=template_result.resolved_modules,
                    conversation_id=conversation_id,
                    persona_id=persona_id,
                    db_session=db_session,
                    trigger_context=trigger_context,
                    current_provider=current_provider,
                    current_provider_settings=current_provider_settings,
                    current_chat_controls=current_chat_controls
                )
                
                ai_response = ai_response_obj.content
                ai_response_metadata = {
                    "model": ai_response_obj.model,
                    "provider_type": ai_response_obj.provider_type,
                    "metadata": ai_response_obj.metadata,
                    "thinking": ai_response_obj.thinking
                }
                
                elapsed_time = stage_timer.elapsed or 0.0
                logger.debug(f"Stage 3 completed in {elapsed_time:.3f}s")
                return ai_response, ai_response_metadata, elapsed_time
                
            except Exception as e:
                logger.error(f"Stage 3 execution failed: {e}")
                ai_response = f"[AI Response Generation Error: {str(e)}]"
                ai_response_metadata = {"error": str(e)}
                elapsed_time = stage_timer.elapsed or 0.0
                return ai_response, ai_response_metadata, elapsed_time