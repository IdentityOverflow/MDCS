"""
Unified Staged Module Resolver orchestrating the complete 5-stage execution pipeline.

This replaces the monolithic staged_module_resolver_base.py with a clean composition-based
architecture that orchestrates all 5 stages using focused stage executors.
"""

import logging
import time
from typing import List, Dict, Set, Optional, Any, Tuple, AsyncIterator
from dataclasses import dataclass
from enum import Enum
from sqlalchemy.orm import Session

from ...models import Module, ModuleType, ExecutionContext, ConversationState
from ...database.connection import get_db
from ...core.script_engine import ScriptEngine
from ...core.script_context import ScriptExecutionContext
from ...core.trigger_matcher import TriggerMatcher
from ...services.system_prompt_state import SystemPromptState, PromptStateManager

from .template_parser import TemplateParser
from .stages import Stage1Executor, Stage2Executor, Stage3Executor, Stage4Executor, Stage5Executor
from .stages.base_stage import ModuleResolutionWarning

logger = logging.getLogger(__name__)


@dataclass
class StagedTemplateResolutionResult:
    """Result of staged template resolution with content and warnings."""
    resolved_template: str
    warnings: List[ModuleResolutionWarning]
    resolved_modules: List[str]  # List of successfully resolved module names
    stages_executed: List[int]  # List of stages that were executed


@dataclass
class PostResponseExecutionResult:
    """Result of POST_RESPONSE module execution."""
    module_name: str
    stage: int  # 4 or 5
    variables: Dict[str, Any]
    execution_metadata: Dict[str, Any]
    success: bool
    error_message: Optional[str] = None


@dataclass
class CompleteResolutionResult:
    """Result of complete 5-stage resolution including AI response."""
    template_resolution: StagedTemplateResolutionResult
    ai_response: Optional[str]
    ai_response_metadata: Dict[str, Any]
    post_response_results: List[PostResponseExecutionResult]
    total_execution_time: float
    stage_timings: Dict[int, float]


class ExecutionStage(Enum):
    """Enumeration of template resolution stages."""
    STAGE1 = 1  # Simple + IMMEDIATE Non-AI + Previous POST_RESPONSE
    STAGE2 = 2  # IMMEDIATE AI-powered
    STAGE4 = 4  # POST_RESPONSE Non-AI
    STAGE5 = 5  # POST_RESPONSE AI-powered


class StagedModuleResolver:
    """
    Unified orchestrator for the complete 5-stage module resolution pipeline.
    
    Replaces the monolithic staged_module_resolver_base.py with a clean composition-based
    architecture using focused stage executors. Handles the complete pipeline:
    
    - Stage 1: Simple + IMMEDIATE Non-AI + Previous POST_RESPONSE
    - Stage 2: IMMEDIATE AI-powered modules  
    - Stage 3: Main AI response generation
    - Stage 4: POST_RESPONSE Non-AI modules
    - Stage 5: POST_RESPONSE AI-powered modules
    """
    
    def __init__(self, db_session: Optional[Session] = None, session_manager=None):
        """
        Initialize the unified staged module resolver.
        
        Args:
            db_session: Optional database session. If not provided, will get one from connection pool.
            session_manager: Optional session manager for cancellation support.
        """
        self.db_session = db_session
        
        # Initialize stage executors with composition
        self.stage1 = Stage1Executor(db_session)
        self.stage2 = Stage2Executor(db_session)
        self.stage3 = Stage3Executor(db_session)
        self.stage4 = Stage4Executor(db_session)
        self.stage5 = Stage5Executor(db_session)
        
        # Session management and cancellation support
        from ...services.chat_session_manager import get_chat_session_manager
        self.session_manager = session_manager or get_chat_session_manager()
        self._current_session_id: Optional[str] = None
        
        # SystemPromptState tracking
        self._state_tracking_enabled: bool = False
        self._prompt_state_manager: Optional[PromptStateManager] = None
    
    def set_session_id(self, session_id: str) -> None:
        """
        Set the current session ID for this resolver instance.
        
        Args:
            session_id: Session ID to associate with operations
        """
        self._current_session_id = session_id
        logger.debug(f"Resolver session ID set to: {session_id}")
    
    def _check_cancellation(self, session_id: Optional[str] = None) -> None:
        """
        Check if the current operation should be cancelled.
        
        Args:
            session_id: Session ID to check, uses current session if not provided
            
        Raises:
            asyncio.CancelledError: If the session has been cancelled
        """
        import asyncio
        
        check_session_id = session_id or self._current_session_id
        if check_session_id and self.session_manager:
            token = self.session_manager.get_session(check_session_id)
            if token and token.is_cancelled():
                logger.info(f"Operation cancelled for session {check_session_id}")
                raise asyncio.CancelledError()
    
    def enable_state_tracking(self) -> None:
        """Enable SystemPromptState tracking for AI plugins."""
        self._state_tracking_enabled = True
        self._prompt_state_manager = PromptStateManager()
        logger.debug("SystemPromptState tracking enabled")
    
    def disable_state_tracking(self) -> None:
        """Disable SystemPromptState tracking."""
        self._state_tracking_enabled = False
        self._prompt_state_manager = None
        logger.debug("SystemPromptState tracking disabled")
    
    def get_current_state(self) -> Optional[SystemPromptState]:
        """Get current SystemPromptState if tracking is enabled."""
        return self._prompt_state_manager.get_current_state() if self._prompt_state_manager else None
    
    def get_debug_summary(self) -> Optional[Dict[str, Any]]:
        """Get debug summary if state tracking is enabled."""
        return self._prompt_state_manager.get_debug_summary() if self._prompt_state_manager else None
    
    def get_performance_summary(self) -> Optional[Dict[str, Any]]:
        """Get performance summary if state tracking is enabled."""
        return self._prompt_state_manager.get_performance_summary() if self._prompt_state_manager else None
    
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
        
        This prepares the complete template for main AI response generation (Stage 3).
        
        Args:
            template: The template string containing @module_name references
            conversation_id: Optional conversation ID for advanced module context
            persona_id: Optional persona ID for advanced module context
            db_session: Optional database session for advanced module context
            trigger_context: Optional trigger context for advanced modules
            current_provider: Current chat session provider ("ollama" or "openai")
            current_provider_settings: Current provider connection settings  
            current_chat_controls: Current chat control parameters
            
        Returns:
            StagedTemplateResolutionResult with resolved template and metadata
        """
        logger.debug("Starting template resolution: Stages 1 and 2")
        start_time = time.time()
        
        # Set session ID if provided
        if session_id:
            self.set_session_id(session_id)
        
        # Check for cancellation before starting
        self._check_cancellation(session_id)
        
        warnings: List[ModuleResolutionWarning] = []
        resolved_modules: List[str] = []
        stages_executed: List[int] = []
        stage_timings: Dict[int, float] = {}
        
        # Use provided session or get default
        db = db_session or next(get_db()) if self.db_session is None else self.db_session
        
        current_template = template
        
        # Stage 1: Simple + IMMEDIATE Non-AI + Previous POST_RESPONSE
        try:
            stage1_start = time.time()
            current_template = self.stage1.execute_stage(
                template=current_template,
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
            stage1_time = time.time() - stage1_start
            stage_timings[1] = stage1_time
            stages_executed.append(1)
            logger.debug(f"Stage 1 completed in {stage1_time:.3f}s")
        except Exception as e:
            logger.error(f"Stage 1 execution failed: {e}")
            warnings.append(ModuleResolutionWarning(
                module_name="stage1_execution",
                warning_type="stage_execution_error",
                message=f"Stage 1 execution failed: {str(e)}",
                stage=1
            ))
        
        # Check for cancellation between stages
        self._check_cancellation(session_id)
        
        # Stage 2: IMMEDIATE AI-powered modules
        try:
            stage2_start = time.time()
            current_template = self.stage2.execute_stage(
                template=current_template,
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
            stage2_time = time.time() - stage2_start
            stage_timings[2] = stage2_time
            stages_executed.append(2)
            logger.debug(f"Stage 2 completed in {stage2_time:.3f}s")
        except Exception as e:
            logger.error(f"Stage 2 execution failed: {e}")
            warnings.append(ModuleResolutionWarning(
                module_name="stage2_execution",
                warning_type="stage_execution_error",
                message=f"Stage 2 execution failed: {str(e)}",
                stage=2
            ))
        
        total_time = time.time() - start_time
        
        result = StagedTemplateResolutionResult(
            resolved_template=current_template,
            warnings=warnings,
            resolved_modules=resolved_modules,
            stages_executed=stages_executed
        )
        
        logger.debug(f"Template resolution completed in {total_time:.3f}s, {len(resolved_modules)} modules resolved")
        return result
    
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
        
        # Set session ID if provided
        if session_id:
            self.set_session_id(session_id)
        
        # Check for cancellation before starting pipeline
        self._check_cancellation(session_id)
        
        # Stage 1 & 2: Template Resolution
        template_result = await self.resolve_template_stages_1_and_2(
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
        self._check_cancellation(session_id)
        
        # Stage 3: Main AI Response Generation
        stage3_start = time.time()
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
            stage3_time = time.time() - stage3_start
            stage_timings[3] = stage3_time
            template_result.stages_executed.append(3)
            logger.debug(f"Stage 3 completed in {stage3_time:.3f}s")
        except Exception as e:
            logger.error(f"Stage 3 execution failed: {e}")
            ai_response = f"[AI Response Generation Error: {str(e)}]"
            ai_response_metadata = {"error": str(e)}
            stage_timings[3] = time.time() - stage3_start
        
        # Check for cancellation before post-response stages
        self._check_cancellation(session_id)
            
        # Stages 4 & 5: Post-Response Processing
        post_response_results = await self.execute_post_response_stages(
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
        
        # Set session ID if provided
        if session_id:
            self.set_session_id(session_id)
        
        # Check for cancellation before starting post-response stages
        self._check_cancellation(session_id)
        
        db = db_session or next(get_db()) if self.db_session is None else self.db_session
        warnings: List[ModuleResolutionWarning] = []
        resolved_modules: List[str] = []
        results: List[PostResponseExecutionResult] = []
        
        # Stage 4: POST_RESPONSE Non-AI modules
        try:
            stage4_start = time.time()
            self.stage4.execute_stage(
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
                response_metadata=response_metadata
            )
            stage4_time = time.time() - stage4_start
            logger.debug(f"Stage 4 completed in {stage4_time:.3f}s")
        except Exception as e:
            logger.error(f"Stage 4 execution failed: {e}")
        
        # Check for cancellation between Stage 4 and Stage 5
        self._check_cancellation(session_id)
        
        # Stage 5: POST_RESPONSE AI-powered modules  
        try:
            stage5_start = time.time()
            self.stage5.execute_stage(
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
                response_metadata=response_metadata
            )
            stage5_time = time.time() - stage5_start
            logger.debug(f"Stage 5 completed in {stage5_time:.3f}s")
        except Exception as e:
            logger.error(f"Stage 5 execution failed: {e}")
        
        # TODO: Convert warnings and resolved_modules into PostResponseExecutionResult objects
        # For now, return empty results as the stages handle their own execution
        
        return results
    
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
            session_id: Optional session ID for cancellation support
            
        Yields:
            Various result types including template resolution, streaming chunks, and post-response results
        """
        logger.debug("Starting streaming 5-stage resolution pipeline")
        
        # Set session ID if provided
        if session_id:
            self.set_session_id(session_id)
        
        # Check for cancellation before starting pipeline
        self._check_cancellation(session_id)
        
        # Stage 1 & 2: Template Resolution
        template_result = await self.resolve_template_stages_1_and_2(
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
        self._check_cancellation(session_id)
        
        # Stage 3: Streaming AI Response Generation
        accumulated_response = ""
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
            accumulated_response += chunk.content if hasattr(chunk, 'content') else str(chunk)
            yield chunk
        
        # Stages 4 & 5: Post-Response Processing (after streaming completes)
        if accumulated_response:
            post_response_results = await self.execute_post_response_stages(
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
    
    def _parse_module_references(self, template: str) -> List[str]:
        """Parse module references from template for backward compatibility."""
        return TemplateParser.parse_module_references(template)
    
    @staticmethod
    def validate_module_name(name: str) -> bool:
        """Validate module name format for backward compatibility."""
        import re
        # Module names should be lowercase alphanumeric with underscores, starting with a letter
        pattern = r'^[a-z][a-z0-9_]*$'
        return bool(re.match(pattern, name)) and len(name) <= 50


def resolve_template_for_response(
    template: str, 
    conversation_id: Optional[str] = None,
    persona_id: Optional[str] = None,
    db_session: Optional[Session] = None
) -> StagedTemplateResolutionResult:
    """
    Convenience function to resolve a template for main AI response (Stage 1 + Stage 2).
    
    If db_session is not provided, a new session will be obtained and closed.
    """
    local_db_session = None
    try:
        if db_session is None:
            local_db_session = next(get_db())
            db_session = local_db_session
            
        resolver = StagedModuleResolver(db_session=db_session)
        
        # Use asyncio.run to handle the async method
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're in an async context, create a new thread
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        resolver.resolve_template_stages_1_and_2(
                            template=template,
                            conversation_id=conversation_id,
                            persona_id=persona_id,
                            db_session=db_session
                        )
                    )
                    return future.result()
            else:
                # No event loop running, we can use asyncio.run directly
                return asyncio.run(
                    resolver.resolve_template_stages_1_and_2(
                        template=template,
                        conversation_id=conversation_id,
                        persona_id=persona_id,
                        db_session=db_session
                    )
                )
        except RuntimeError:
            # Fallback: create a new event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(
                    resolver.resolve_template_stages_1_and_2(
                        template=template,
                        conversation_id=conversation_id,
                        persona_id=persona_id,
                        db_session=db_session
                    )
                )
            finally:
                loop.close()
    finally:
        if local_db_session:
            local_db_session.close()


def _parse_module_references(template: str) -> List[str]:
    """Parse module references from template for backward compatibility."""
    from .template_parser import TemplateParser
    return TemplateParser.parse_module_references(template)


def validate_module_name(name: str) -> bool:
    """Validate module name format for backward compatibility."""
    import re
    # Module names should be lowercase alphanumeric with underscores, starting with a letter
    pattern = r'^[a-z][a-z0-9_]*$'
    return bool(re.match(pattern, name)) and len(name) <= 50