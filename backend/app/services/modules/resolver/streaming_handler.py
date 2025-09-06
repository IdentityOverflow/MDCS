"""
Streaming pipeline handler for the staged module resolver.

Manages streaming execution of the complete 5-stage pipeline.
"""

import logging
from typing import Optional, Dict, Any, AsyncIterator

from sqlalchemy.orm import Session

from .result_models import StagedTemplateResolutionResult, PostResponseExecutionResult
from .session_manager import ResolverSessionManager
from .pipeline_executor import PipelineExecutor

logger = logging.getLogger(__name__)


class StreamingPipelineHandler:
    """
    Streaming pipeline handler for the staged module resolver.
    
    Manages streaming execution with cancellation support across all stages.
    """
    
    def __init__(self, pipeline_executor: PipelineExecutor, session_manager: ResolverSessionManager):
        """
        Initialize streaming handler.
        
        Args:
            pipeline_executor: Core pipeline executor
            session_manager: Session manager for cancellation support
        """
        self.pipeline_executor = pipeline_executor
        self.session_manager = session_manager
    
    async def execute_streaming_pipeline(
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
    ) -> AsyncIterator[Any]:
        """
        Execute the complete pipeline with streaming Stage 3 response.
        
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
            
        Yields:
            Various result types including template resolution, streaming chunks, and post-response results
        """
        logger.debug("Starting streaming 5-stage resolution pipeline")
        
        # Set session ID if provided
        if session_id:
            self.session_manager.set_session_id(session_id)
        
        # Check for cancellation before starting pipeline
        self.session_manager.check_cancellation(session_id)
        
        # Stage 1 & 2: Template Resolution
        template_result = await self.pipeline_executor.resolve_template_stages_1_and_2(
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
        
        yield template_result
        
        # Check for cancellation before Stage 3
        self.session_manager.check_cancellation(session_id)
        
        # Stage 3: Streaming AI Response Generation
        accumulated_response = ""
        async for chunk in self.pipeline_executor.execute_stage3_streaming(
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
            accumulated_response += chunk.content if hasattr(chunk, 'content') else str(chunk)
            yield chunk
        
        # Stages 4 & 5: Post-Response Processing (after streaming completes)
        if accumulated_response:
            post_response_results = await self.pipeline_executor.execute_post_response_stages(
                template=template,
                ai_response=accumulated_response,
                session_id=session_id,
                conversation_id=conversation_id,
                persona_id=persona_id,
                db_session=db_session,
                trigger_context=trigger_context,
                current_provider=current_provider,
                current_provider_settings=current_provider_settings,
                current_chat_controls=current_chat_controls,
                response_metadata={}
            )
            
            yield post_response_results