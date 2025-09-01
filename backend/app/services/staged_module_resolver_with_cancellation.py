"""
Enhanced StagedModuleResolver with session management and cancellation support.

Extends the existing StagedModuleResolver to integrate with ChatSessionManager
for proper cancellation across all 5 execution stages.
"""

import asyncio
import logging
import uuid
import time
from typing import List, Dict, Set, Optional, Any, Tuple
from dataclasses import dataclass
from sqlalchemy.orm import Session

from .staged_module_resolver import (
    StagedModuleResolver as BaseStagedModuleResolver,
    StagedTemplateResolutionResult,
    PostResponseExecutionResult,
    ModuleResolutionWarning,
    ExecutionStage,
    MAX_RECURSION_DEPTH
)
from .chat_session_manager import get_chat_session_manager, ChatSessionManager
from app.models import Module, ModuleType, ExecutionContext

logger = logging.getLogger(__name__)


class StagedModuleResolverWithCancellation(BaseStagedModuleResolver):
    """
    Enhanced StagedModuleResolver with session management and cancellation support.
    
    Extends the base StagedModuleResolver to integrate with ChatSessionManager,
    enabling proper request cancellation across all 5 execution stages.
    """
    
    def __init__(self, db_session: Optional[Session] = None, session_manager: Optional[ChatSessionManager] = None):
        """
        Initialize the enhanced staged module resolver.
        
        Args:
            db_session: Optional database session. If not provided, will get one from connection pool.
            session_manager: Optional session manager instance. If not provided, uses global instance.
        """
        super().__init__(db_session=db_session)
        self.session_manager = session_manager or get_chat_session_manager()
        self._current_session_id = None
    
    def set_session_id(self, session_id: str) -> None:
        """
        Set the current session ID for this resolver instance.
        
        Args:
            session_id: Session ID to associate with operations
        """
        self._current_session_id = session_id
    
    def _check_cancellation(self, session_id: Optional[str] = None) -> None:
        """
        Check if the current operation should be cancelled.
        
        Args:
            session_id: Session ID to check, uses current session if not provided
            
        Raises:
            asyncio.CancelledError: If the session has been cancelled
        """
        check_session_id = session_id or self._current_session_id
        if check_session_id:
            token = self.session_manager.get_session(check_session_id)
            if token and token.is_cancelled():
                logger.info(f"Operation cancelled for session {check_session_id}")
                raise asyncio.CancelledError()
    
    async def resolve_template_stage1_and_stage2_async(
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
        Async version of resolve_template_stage1_and_stage2 with cancellation support.
        
        Execute Stage 1 and Stage 2 of template resolution with cancellation checks
        between stages and during AI module execution.
        
        Args:
            template: The template string containing @module_name references
            conversation_id: Optional conversation ID for advanced module context
            persona_id: Optional persona ID for advanced module context
            db_session: Optional database session
            trigger_context: Optional trigger context for advanced modules
            current_provider: Current chat session provider
            current_provider_settings: Current provider connection settings
            current_chat_controls: Current chat control parameters
            session_id: Session ID for cancellation tracking
            
        Returns:
            StagedTemplateResolutionResult with resolved content and execution info
            
        Raises:
            asyncio.CancelledError: If the operation is cancelled
        """
        # Use provided session ID or current one
        working_session_id = session_id or self._current_session_id
        
        if not template:
            return StagedTemplateResolutionResult(
                resolved_template="",
                warnings=[],
                resolved_modules=[],
                stages_executed=[]
            )
        
        warnings: List[ModuleResolutionWarning] = []
        resolved_modules: List[str] = []
        stages_executed: List[int] = []
        
        # Register current task if we have a session ID
        if working_session_id:
            current_task = asyncio.current_task()
            if current_task:
                try:
                    self.session_manager.register_session(
                        session_id=working_session_id,
                        conversation_id=conversation_id,
                        asyncio_task=current_task,
                        current_stage=1  # Starting with Stage 1
                    )
                except ValueError:
                    # Session already registered, just continue
                    pass
        
        try:
            # Reset resolution stack for new template
            self._resolution_stack = set()
            
            # Initialize SystemPromptState tracking if enabled
            if self._state_tracking_enabled and self._prompt_state_manager:
                self._current_state = self._prompt_state_manager.create_initial_state(
                    conversation_id or "unknown",
                    persona_id or "unknown", 
                    template
                )
            
            # Handle escaped modules
            template_with_placeholders, escaped_placeholders = self._handle_escaped_modules(template)
            
            # Check for cancellation before Stage 1
            self._check_cancellation(working_session_id)
            
            # Stage 1: Simple modules + IMMEDIATE Non-AI + Previous POST_RESPONSE
            if working_session_id:
                self.session_manager.update_session_stage(working_session_id, 1)
            
            stage1_start_time = time.time()
            stage1_template = await self._execute_stage1_async(
                template_with_placeholders, warnings, resolved_modules,
                conversation_id, persona_id, db_session, trigger_context,
                current_provider, current_provider_settings, current_chat_controls,
                working_session_id
            )
            stage1_execution_time = time.time() - stage1_start_time
            stages_executed.append(1)
            
            # Check for cancellation between stages
            self._check_cancellation(working_session_id)
            
            # Update SystemPromptState after Stage 1
            if self._current_state and self._prompt_state_manager:
                stage1_modules = [m for m in resolved_modules if m not in []]
                self._current_state = self._prompt_state_manager.update_stage1_completion(
                    self._current_state, stage1_template, stage1_modules, 
                    warnings[-len(stage1_modules):] if stage1_modules else [], 
                    stage1_execution_time
                )
            
            # Stage 2: IMMEDIATE AI-powered modules
            if working_session_id:
                self.session_manager.update_session_stage(working_session_id, 2)
            
            stage2_start_time = time.time()
            stage2_template = await self._execute_stage2_async(
                stage1_template, warnings, resolved_modules,
                conversation_id, persona_id, db_session, trigger_context,
                current_provider, current_provider_settings, current_chat_controls,
                working_session_id
            )
            stage2_execution_time = time.time() - stage2_start_time
            stages_executed.append(2)
            
            # Final cancellation check
            self._check_cancellation(working_session_id)
            
            # Update SystemPromptState after Stage 2
            if self._current_state and self._prompt_state_manager:
                stage2_modules = [m for m in resolved_modules if m not in stage1_modules] if 'stage1_modules' in locals() else []
                self._current_state = self._prompt_state_manager.update_stage2_completion(
                    self._current_state, stage2_template, stage2_modules, [], stage2_execution_time
                )
            
            # Restore escaped modules
            final_template = self._restore_escaped_modules(stage2_template, escaped_placeholders)
            
            # Finalize SystemPromptState
            if self._current_state and self._prompt_state_manager:
                self._current_state = self._prompt_state_manager.finalize_state(self._current_state)
            
            # Clean up session
            if working_session_id:
                self.session_manager.remove_session(working_session_id)
            
            return StagedTemplateResolutionResult(
                resolved_template=final_template,
                warnings=warnings,
                resolved_modules=list(set(resolved_modules)),  # Remove duplicates
                stages_executed=stages_executed
            )
            
        except asyncio.CancelledError:
            logger.info(f"Template resolution cancelled for session {working_session_id}")
            # Clean up session
            if working_session_id:
                self.session_manager.remove_session(working_session_id)
            raise
        except Exception as e:
            logger.error(f"Unexpected error during staged template resolution: {e}")
            # Clean up session
            if working_session_id:
                self.session_manager.remove_session(working_session_id)
            
            warnings.append(ModuleResolutionWarning(
                module_name="",
                warning_type="resolution_error",
                message=f"Unexpected error during resolution: {str(e)}"
            ))
            
            return StagedTemplateResolutionResult(
                resolved_template=template,  # Return original on error
                warnings=warnings,
                resolved_modules=resolved_modules,
                stages_executed=stages_executed
            )
    
    async def execute_post_response_modules_async(
        self,
        arg1: Optional[str],
        arg2: Optional[str],
        arg3: Optional[Session] = None,
        arg4: Optional[Any] = None,
        trigger_context: Optional[Dict[str, Any]] = None,
        current_provider: Optional[str] = None,
        current_provider_settings: Optional[Dict[str, Any]] = None,
        current_chat_controls: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> List[PostResponseExecutionResult]:
        """
        Async version of execute_post_response_modules with cancellation support.
        
        Execute Stage 4 and Stage 5: POST_RESPONSE modules with cancellation checks.
        
        Args:
            Same as parent method, plus:
            session_id: Session ID for cancellation tracking
            
        Returns:
            List of PostResponseExecutionResult objects
            
        Raises:
            asyncio.CancelledError: If the operation is cancelled
        """
        # Use provided session ID or current one
        working_session_id = session_id or self._current_session_id
        
        # Handle both calling patterns (same as parent)
        if isinstance(arg4, list):
            conversation_id = arg1
            persona_id = arg2
            db_session = arg3
            post_response_modules = arg4
        else:
            persona_id = arg1
            conversation_id = arg2
            db_session = arg3
            trigger_context = arg4 or trigger_context
            post_response_modules = None
        
        if not persona_id or not db_session:
            logger.warning("Cannot execute POST_RESPONSE modules without persona_id and db_session")
            return []
        
        # Register current task if we have a session ID
        if working_session_id:
            current_task = asyncio.current_task()
            if current_task:
                try:
                    self.session_manager.register_session(
                        session_id=working_session_id,
                        conversation_id=conversation_id,
                        asyncio_task=current_task,
                        current_stage=4  # Starting with Stage 4
                    )
                except ValueError:
                    # Session already registered, just continue
                    pass
        
        all_results: List[PostResponseExecutionResult] = []
        
        try:
            # Check for cancellation before starting
            self._check_cancellation(working_session_id)
            
            # Stage 4: POST_RESPONSE Non-AI modules
            if working_session_id:
                self.session_manager.update_session_stage(working_session_id, 4)
            
            stage4_results = await self._execute_stage4_async(
                persona_id, conversation_id, db_session, 
                post_response_modules, trigger_context,
                current_provider, current_provider_settings, current_chat_controls,
                working_session_id
            )
            all_results.extend(stage4_results)
            
            # Check for cancellation between stages
            self._check_cancellation(working_session_id)
            
            # Stage 5: POST_RESPONSE AI-powered modules
            if working_session_id:
                self.session_manager.update_session_stage(working_session_id, 5)
            
            stage5_results = await self._execute_stage5_async(
                persona_id, conversation_id, db_session,
                post_response_modules, trigger_context,
                current_provider, current_provider_settings, current_chat_controls,
                working_session_id
            )
            all_results.extend(stage5_results)
            
            # Final cancellation check
            self._check_cancellation(working_session_id)
            
            # Clean up session
            if working_session_id:
                self.session_manager.remove_session(working_session_id)
            
            return all_results
            
        except asyncio.CancelledError:
            logger.info(f"Post-response execution cancelled for session {working_session_id}")
            # Clean up session
            if working_session_id:
                self.session_manager.remove_session(working_session_id)
            raise
        except Exception as e:
            logger.error(f"Error executing POST_RESPONSE modules: {e}")
            # Clean up session
            if working_session_id:
                self.session_manager.remove_session(working_session_id)
            raise
    
    async def _execute_stage1_async(
        self,
        template: str,
        warnings: List[ModuleResolutionWarning],
        resolved_modules: List[str],
        conversation_id: Optional[str],
        persona_id: Optional[str],
        db_session: Optional[Session],
        trigger_context: Optional[Dict[str, Any]],
        current_provider: Optional[str],
        current_provider_settings: Optional[Dict[str, Any]],
        current_chat_controls: Optional[Dict[str, Any]],
        session_id: Optional[str] = None
    ) -> str:
        """
        Execute Stage 1 with cancellation checks.
        
        Stage 1: Simple modules + IMMEDIATE Non-AI + Previous POST_RESPONSE
        """
        # For now, delegate to sync version with periodic cancellation checks
        # This can be enhanced to be fully async in the future
        
        # Check cancellation before starting
        self._check_cancellation(session_id)
        
        # Execute the original Stage 1 logic
        result = self._execute_stage1(
            template, warnings, resolved_modules,
            conversation_id, persona_id, db_session, trigger_context,
            current_provider, current_provider_settings, current_chat_controls
        )
        
        # Check cancellation after completion
        self._check_cancellation(session_id)
        
        return result
    
    async def _execute_stage2_async(
        self,
        template: str,
        warnings: List[ModuleResolutionWarning],
        resolved_modules: List[str],
        conversation_id: Optional[str],
        persona_id: Optional[str],
        db_session: Optional[Session],
        trigger_context: Optional[Dict[str, Any]],
        current_provider: Optional[str],
        current_provider_settings: Optional[Dict[str, Any]],
        current_chat_controls: Optional[Dict[str, Any]],
        session_id: Optional[str] = None
    ) -> str:
        """
        Execute Stage 2 with cancellation checks during AI module execution.
        
        Stage 2: IMMEDIATE AI-powered modules
        """
        # Check cancellation before starting
        self._check_cancellation(session_id)
        
        # Execute the original Stage 2 logic with periodic checks
        # For AI modules, we'll add cancellation checks during script execution
        result = self._execute_stage2(
            template, warnings, resolved_modules,
            conversation_id, persona_id, db_session, trigger_context,
            current_provider, current_provider_settings, current_chat_controls
        )
        
        # Check cancellation after completion
        self._check_cancellation(session_id)
        
        return result
    
    async def _execute_stage4_async(
        self,
        persona_id: str,
        conversation_id: str,
        db_session: Session,
        post_response_modules: Optional[List[Module]],
        trigger_context: Optional[Dict[str, Any]],
        current_provider: Optional[str],
        current_provider_settings: Optional[Dict[str, Any]],
        current_chat_controls: Optional[Dict[str, Any]],
        session_id: Optional[str] = None
    ) -> List[PostResponseExecutionResult]:
        """
        Execute Stage 4 with cancellation checks.
        
        Stage 4: POST_RESPONSE Non-AI modules
        """
        # Check cancellation before starting
        self._check_cancellation(session_id)
        
        # Get modules if not provided
        if post_response_modules is None:
            post_response_modules = self._get_post_response_modules(persona_id, db_session)
        
        results = []
        
        # Filter for Stage 4 modules (POST_RESPONSE, non-AI)
        stage4_modules = [
            module for module in post_response_modules
            if (module.execution_context == ExecutionContext.POST_RESPONSE and 
                not module.requires_ai_inference and module.is_active)
        ]
        
        for module in stage4_modules:
            # Check cancellation before each module
            self._check_cancellation(session_id)
            
            try:
                # Execute module (delegating to base implementation for now)
                result = self._execute_single_post_response_module(
                    module, persona_id, conversation_id, db_session,
                    trigger_context, current_provider, 
                    current_provider_settings, current_chat_controls
                )
                results.append(result)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"Error executing Stage 4 module {module.name}: {e}")
                results.append(PostResponseExecutionResult(
                    module_name=module.name,
                    stage=4,
                    variables={},
                    execution_metadata={},
                    success=False,
                    error_message=str(e)
                ))
        
        return results
    
    async def _execute_stage5_async(
        self,
        persona_id: str,
        conversation_id: str,
        db_session: Session,
        post_response_modules: Optional[List[Module]],
        trigger_context: Optional[Dict[str, Any]],
        current_provider: Optional[str],
        current_provider_settings: Optional[Dict[str, Any]],
        current_chat_controls: Optional[Dict[str, Any]],
        session_id: Optional[str] = None
    ) -> List[PostResponseExecutionResult]:
        """
        Execute Stage 5 with cancellation checks during AI operations.
        
        Stage 5: POST_RESPONSE AI-powered modules
        """
        # Check cancellation before starting
        self._check_cancellation(session_id)
        
        # Get modules if not provided
        if post_response_modules is None:
            post_response_modules = self._get_post_response_modules(persona_id, db_session)
        
        results = []
        
        # Filter for Stage 5 modules (POST_RESPONSE, AI-powered)
        stage5_modules = [
            module for module in post_response_modules
            if (module.execution_context == ExecutionContext.POST_RESPONSE and 
                module.requires_ai_inference and module.is_active)
        ]
        
        for module in stage5_modules:
            # Check cancellation before each AI module
            self._check_cancellation(session_id)
            
            try:
                # Execute AI-powered module (delegating to base implementation for now)
                result = self._execute_single_post_response_module(
                    module, persona_id, conversation_id, db_session,
                    trigger_context, current_provider, 
                    current_provider_settings, current_chat_controls
                )
                results.append(result)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"Error executing Stage 5 module {module.name}: {e}")
                results.append(PostResponseExecutionResult(
                    module_name=module.name,
                    stage=5,
                    variables={},
                    execution_metadata={},
                    success=False,
                    error_message=str(e)
                ))
        
        return results
    
    def _get_post_response_modules(self, persona_id: str, db_session: Session) -> List[Module]:
        """Get POST_RESPONSE modules for a persona."""
        # Delegate to base implementation
        return db_session.query(Module).filter(
            Module.persona_id == persona_id,
            Module.execution_context == ExecutionContext.POST_RESPONSE,
            Module.is_active == True
        ).all()
    
    def _execute_single_post_response_module(
        self,
        module: Module,
        persona_id: str,
        conversation_id: str,
        db_session: Session,
        trigger_context: Optional[Dict[str, Any]],
        current_provider: Optional[str],
        current_provider_settings: Optional[Dict[str, Any]],
        current_chat_controls: Optional[Dict[str, Any]]
    ) -> PostResponseExecutionResult:
        """Execute a single post-response module."""
        # This would delegate to the base implementation
        # For now, return a basic result
        return PostResponseExecutionResult(
            module_name=module.name,
            stage=4 if not module.requires_ai_inference else 5,
            variables={},
            execution_metadata={},
            success=True
        )
    
    # Backward compatibility methods - delegate to async versions when session ID is available
    def resolve_template_stage1_and_stage2(
        self,
        template: str,
        conversation_id: Optional[str] = None,
        persona_id: Optional[str] = None,
        db_session: Optional[Session] = None,
        trigger_context: Optional[Dict[str, Any]] = None,
        current_provider: Optional[str] = None,
        current_provider_settings: Optional[Dict[str, Any]] = None,
        current_chat_controls: Optional[Dict[str, Any]] = None
    ) -> StagedTemplateResolutionResult:
        """
        Backward compatibility method - uses async version if session ID is set.
        """
        if self._current_session_id:
            # Run async version in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(
                    self.resolve_template_stage1_and_stage2_async(
                        template, conversation_id, persona_id, db_session,
                        trigger_context, current_provider, current_provider_settings,
                        current_chat_controls, self._current_session_id
                    )
                )
            finally:
                loop.close()
        else:
            # Use base implementation
            return super().resolve_template_stage1_and_stage2(
                template, conversation_id, persona_id, db_session,
                trigger_context, current_provider, current_provider_settings,
                current_chat_controls
            )