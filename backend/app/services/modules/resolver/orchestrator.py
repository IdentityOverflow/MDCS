"""
Main orchestrator facade for the staged module resolver.

This is the primary interface that replaces the monolithic StagedModuleResolver class
with a clean composition-based architecture using focused components.
"""

import logging
from typing import Optional, Dict, Any, AsyncIterator
from sqlalchemy.orm import Session

from .result_models import (
    StagedTemplateResolutionResult,
    CompleteResolutionResult,
    validate_module_name
)
from .session_manager import ResolverSessionManager  
from .state_tracker import ResolverStateTracker
from .pipeline_executor import PipelineExecutor
from .streaming_handler import StreamingPipelineHandler

from ..template_parser import TemplateParser

logger = logging.getLogger(__name__)


class StagedModuleResolver:
    """
    Main orchestrator facade for the staged module resolver.
    
    Replaces the monolithic 679-line resolver with a clean composition-based
    architecture using focused components:
    
    - ResolverSessionManager: Session tracking and cancellation
    - ResolverStateTracker: SystemPromptState tracking  
    - PipelineExecutor: Core 5-stage execution logic
    - StreamingPipelineHandler: Streaming execution management
    
    This facade provides the same interface as the original StagedModuleResolver
    while delegating responsibilities to specialized components.
    """
    
    def __init__(self, db_session: Optional[Session] = None, session_manager=None):
        """
        Initialize the staged module resolver orchestrator.
        
        Args:
            db_session: Optional database session. If not provided, will get one from connection pool.
            session_manager: Optional session manager for cancellation support.
        """
        self.db_session = db_session
        
        # Initialize components with composition
        self.session_manager = ResolverSessionManager(session_manager)
        self.state_tracker = ResolverStateTracker()
        self.pipeline_executor = PipelineExecutor(db_session, self.session_manager)
        self.streaming_handler = StreamingPipelineHandler(self.pipeline_executor, self.session_manager)
    
    # Session Management Methods
    def set_session_id(self, session_id: str) -> None:
        """
        Set the current session ID for this resolver instance.
        
        Args:
            session_id: Session ID to associate with operations
        """
        self.session_manager.set_session_id(session_id)
    
    # State Tracking Methods  
    def enable_state_tracking(self) -> None:
        """Enable SystemPromptState tracking for AI plugins."""
        self.state_tracker.enable_state_tracking()
    
    def disable_state_tracking(self) -> None:
        """Disable SystemPromptState tracking."""
        self.state_tracker.disable_state_tracking()
    
    def get_current_state(self) -> Optional[Any]:
        """Get current SystemPromptState if tracking is enabled."""
        return self.state_tracker.get_current_state()
    
    def get_debug_summary(self) -> Optional[Dict[str, Any]]:
        """Get debug summary if state tracking is enabled."""
        return self.state_tracker.get_debug_summary()
    
    def get_performance_summary(self) -> Optional[Dict[str, Any]]:
        """Get performance summary if state tracking is enabled."""
        return self.state_tracker.get_performance_summary()
    
    # Core Pipeline Methods
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
        
        Delegates to PipelineExecutor for the actual execution logic.
        """
        return await self.pipeline_executor.resolve_template_stages_1_and_2(
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
        
        Delegates to PipelineExecutor for the actual execution logic.
        """
        return await self.pipeline_executor.execute_complete_pipeline(
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
    ) -> list:
        """
        Execute Stage 4 and Stage 5 post-response processing.
        
        Delegates to PipelineExecutor for the actual execution logic.
        """
        return await self.pipeline_executor.execute_post_response_stages(
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
        
        Delegates to StreamingPipelineHandler for the actual streaming logic.
        """
        async for result in self.streaming_handler.execute_streaming_pipeline(
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
        ):
            yield result
    
    # Backward Compatibility Methods
    def _parse_module_references(self, template: str) -> list:
        """Parse module references from template for backward compatibility."""
        return TemplateParser.parse_module_references(template)
    
    @staticmethod
    def validate_module_name(name: str) -> bool:
        """Validate module name format for backward compatibility."""
        return validate_module_name(name)