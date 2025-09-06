"""
Refactored pipeline executor using focused component composition.

This replaces the 430-line monolithic pipeline executor with clean delegation
to specialized components for different pipeline responsibilities.
"""

import logging
from typing import List, Optional, Dict, Any, AsyncIterator
from sqlalchemy.orm import Session

from .result_models import (
    StagedTemplateResolutionResult, 
    PostResponseExecutionResult,
    CompleteResolutionResult
)
from .session_manager import ResolverSessionManager
from .template_resolver import TemplateResolver
from .post_response_handler import PostResponseHandler
from .stage_coordinator import StageCoordinator

logger = logging.getLogger(__name__)


class PipelineExecutor:
    """
    Refactored pipeline executor using focused component composition.
    
    Delegates responsibilities to specialized components:
    - TemplateResolver: Handles stages 1 & 2 template resolution
    - PostResponseHandler: Handles stages 4 & 5 post-response processing
    - StageCoordinator: Orchestrates complete pipeline execution
    """
    
    def __init__(self, db_session: Optional[Session] = None, session_manager: Optional[ResolverSessionManager] = None):
        """
        Initialize the pipeline executor with focused components.
        
        Args:
            db_session: Optional database session
            session_manager: Optional session manager for cancellation support
        """
        self.db_session = db_session
        self.session_manager = session_manager
        
        # Initialize focused components
        self.template_resolver = TemplateResolver(db_session, session_manager)
        self.post_response_handler = PostResponseHandler(db_session, session_manager)
        self.stage_coordinator = StageCoordinator(db_session, session_manager)
    
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
        
        Delegates to TemplateResolver for the actual logic.
        """
        return await self.template_resolver.resolve_template_stages_1_and_2(
            template=template,
            conversation_id=conversation_id,
            persona_id=persona_id,
            db_session=db_session,
            trigger_context=trigger_context,
            current_provider=current_provider,
            current_provider_settings=current_provider_settings,
            current_chat_controls=current_chat_controls,
            session_id=session_id
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
        
        Delegates to StageCoordinator for the actual logic.
        """
        async for chunk in self.stage_coordinator.execute_stage3_streaming(
            template_result=template_result,
            user_message=user_message,
            conversation_id=conversation_id,
            persona_id=persona_id,
            db_session=db_session,
            trigger_context=trigger_context,
            current_provider=current_provider,
            current_provider_settings=current_provider_settings,
            current_chat_controls=current_chat_controls
        ):
            yield chunk
    
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
        
        Delegates to PostResponseHandler for the actual logic.
        """
        return await self.post_response_handler.execute_post_response_stages(
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
            response_metadata=response_metadata
        )
    
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
        
        Delegates to StageCoordinator for the actual orchestration logic.
        """
        return await self.stage_coordinator.execute_complete_pipeline(
            template=template,
            user_message=user_message,
            session_id=session_id,
            conversation_id=conversation_id,
            persona_id=persona_id,
            db_session=db_session,
            trigger_context=trigger_context,
            current_provider=current_provider,
            current_provider_settings=current_provider_settings,
            current_chat_controls=current_chat_controls
        )