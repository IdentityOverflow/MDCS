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
                
                # Convert stage execution results to PostResponseExecutionResult objects
                # Get the actual execution results from the stage executor
                execution_results = self._extract_execution_results_from_stage4(
                    template=template,
                    resolved_modules=resolved_modules,
                    conversation_id=conversation_id,
                    persona_id=persona_id,
                    db_session=db_session,
                    trigger_context=trigger_context,
                    current_provider=current_provider,
                    current_provider_settings=current_provider_settings,
                    current_chat_controls=current_chat_controls,
                    ai_response=ai_response,
                    response_metadata=response_metadata,
                    elapsed_time=elapsed_time
                )
                results.extend(execution_results)
                
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
                
                # Convert stage execution results to PostResponseExecutionResult objects
                # Get the actual execution results from the stage executor
                execution_results = self._extract_execution_results_from_stage5(
                    template=template,
                    resolved_modules=resolved_modules,
                    conversation_id=conversation_id,
                    persona_id=persona_id,
                    db_session=db_session,
                    trigger_context=trigger_context,
                    current_provider=current_provider,
                    current_provider_settings=current_provider_settings,
                    current_chat_controls=current_chat_controls,
                    ai_response=ai_response,
                    response_metadata=response_metadata,
                    elapsed_time=elapsed_time
                )
                results.extend(execution_results)
                
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
    
    def _extract_execution_results_from_stage4(
        self,
        template: str,
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
        elapsed_time: float
    ) -> List[PostResponseExecutionResult]:
        """
        Extract actual execution results from Stage 4 modules.
        
        This method directly executes Stage 4 modules and captures their 
        individual execution results rather than just template modifications.
        """
        from ....models import Module, ExecutionContext, ModuleType
        from ..execution import SimpleExecutor, ScriptExecutor
        
        results = []
        
        # Get Stage 4 modules
        modules_query = Module.get_modules_for_stage(db_session, 4, persona_id)
        stage4_modules = modules_query.all()
        
        if not stage4_modules:
            return results
        
        # Add response context for post-response modules
        enhanced_trigger_context = (trigger_context or {}).copy()
        enhanced_trigger_context.update({
            'ai_response': ai_response,
            'response_metadata': response_metadata or {},
            'stage': 4,
            'stage_name': "POST_RESPONSE Non-AI modules"
        })
        
        for module in stage4_modules:
            try:
                # Check if this module should execute in Stage 4
                if not self._should_execute_module_in_stage4(module):
                    continue
                
                # Execute the module and capture results
                if module.type == ModuleType.SIMPLE:
                    executor = SimpleExecutor()
                    output = executor.execute(module, {})
                    
                    # Create result for simple module
                    results.append(PostResponseExecutionResult(
                        module_name=module.name,
                        stage=4,
                        variables={"output": output},
                        execution_metadata={"timing": elapsed_time / len(stage4_modules)},
                        success=True
                    ))
                    
                elif module.type == ModuleType.ADVANCED:
                    executor = ScriptExecutor()
                    context = {
                        'conversation_id': conversation_id,
                        'persona_id': persona_id,
                        'db_session': db_session,
                        'trigger_context': enhanced_trigger_context,
                        'current_provider': current_provider,
                        'current_provider_settings': current_provider_settings or {},
                        'current_chat_controls': current_chat_controls or {},
                        'stage': 4,
                        'stage_name': "POST_RESPONSE Non-AI modules",
                        'ai_response': ai_response,
                        'response_metadata': response_metadata or {}
                    }
                    
                    # Execute module and capture detailed results including raw script variables
                    try:
                        exec_details = executor.execute_with_details(module, context)
                        results.append(PostResponseExecutionResult(
                            module_name=module.name,
                            stage=4,
                            variables=exec_details["script_variables"],  # Store raw script variables, not final output
                            execution_metadata={
                                "timing": elapsed_time / len(stage4_modules),
                                "final_output": exec_details["final_output"]  # Store final output in metadata
                            },
                            success=exec_details["success"],
                            error_message=exec_details.get("error_message")
                        ))
                    except Exception as exec_error:
                        results.append(PostResponseExecutionResult(
                            module_name=module.name,
                            stage=4,
                            variables={},
                            execution_metadata={"error": str(exec_error)},
                            success=False,
                            error_message=str(exec_error)
                        ))
                    
                # Store result in ConversationState for next cycle
                if conversation_id and results and results[-1].success:
                    self._store_result_in_conversation_state(
                        db_session=db_session,
                        conversation_id=conversation_id,
                        module=module,
                        result=results[-1],
                        stage="stage4"
                    )
                
                # Add module to resolved list
                if module.name not in resolved_modules:
                    resolved_modules.append(module.name)
                    
            except Exception as e:
                # Create error result for failed module
                results.append(PostResponseExecutionResult(
                    module_name=module.name,
                    stage=4,
                    variables={},
                    execution_metadata={"error": str(e)},
                    success=False,
                    error_message=str(e)
                ))
                logger.error(f"Error executing Stage 4 module '{module.name}': {e}")
        
        return results
    
    def _extract_execution_results_from_stage5(
        self,
        template: str,
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
        elapsed_time: float
    ) -> List[PostResponseExecutionResult]:
        """
        Extract actual execution results from Stage 5 modules.
        
        This method directly executes Stage 5 modules and captures their 
        individual execution results rather than just template modifications.
        """
        from ....models import Module, ExecutionContext, ModuleType
        from ..execution import SimpleExecutor, ScriptExecutor
        
        results = []
        
        # Get Stage 5 modules
        modules_query = Module.get_modules_for_stage(db_session, 5, persona_id)
        stage5_modules = modules_query.all()
        
        if not stage5_modules:
            return results
        
        # Add response context for post-response modules
        enhanced_trigger_context = (trigger_context or {}).copy()
        enhanced_trigger_context.update({
            'ai_response': ai_response,
            'response_metadata': response_metadata or {},
            'stage': 5,
            'stage_name': "POST_RESPONSE AI-powered modules"
        })
        
        for module in stage5_modules:
            try:
                # Check if this module should execute in Stage 5
                if not self._should_execute_module_in_stage5(module):
                    continue
                
                # Execute the module and capture results
                if module.type == ModuleType.SIMPLE:
                    executor = SimpleExecutor()
                    output = executor.execute(module, {})
                    
                    # Create result for simple module
                    results.append(PostResponseExecutionResult(
                        module_name=module.name,
                        stage=5,
                        variables={"output": output},
                        execution_metadata={"timing": elapsed_time / len(stage5_modules)},
                        success=True
                    ))
                    
                elif module.type == ModuleType.ADVANCED:
                    executor = ScriptExecutor()
                    context = {
                        'conversation_id': conversation_id,
                        'persona_id': persona_id,
                        'db_session': db_session,
                        'trigger_context': enhanced_trigger_context,
                        'current_provider': current_provider,
                        'current_provider_settings': current_provider_settings or {},
                        'current_chat_controls': current_chat_controls or {},
                        'stage': 5,
                        'stage_name': "POST_RESPONSE AI-powered modules",
                        'ai_response': ai_response,
                        'response_metadata': response_metadata or {}
                    }
                    
                    # Execute module and capture detailed results including raw script variables
                    try:
                        exec_details = executor.execute_with_details(module, context)
                        results.append(PostResponseExecutionResult(
                            module_name=module.name,
                            stage=5,
                            variables=exec_details["script_variables"],  # Store raw script variables, not final output
                            execution_metadata={
                                "timing": elapsed_time / len(stage5_modules),
                                "final_output": exec_details["final_output"]  # Store final output in metadata
                            },
                            success=exec_details["success"],
                            error_message=exec_details.get("error_message")
                        ))
                    except Exception as exec_error:
                        results.append(PostResponseExecutionResult(
                            module_name=module.name,
                            stage=5,
                            variables={},
                            execution_metadata={"error": str(exec_error)},
                            success=False,
                            error_message=str(exec_error)
                        ))
                    
                # Store result in ConversationState for next cycle
                if conversation_id and results and results[-1].success:
                    self._store_result_in_conversation_state(
                        db_session=db_session,
                        conversation_id=conversation_id,
                        module=module,
                        result=results[-1],
                        stage="stage5"
                    )
                
                # Add module to resolved list
                if module.name not in resolved_modules:
                    resolved_modules.append(module.name)
                    
            except Exception as e:
                # Create error result for failed module
                results.append(PostResponseExecutionResult(
                    module_name=module.name,
                    stage=5,
                    variables={},
                    execution_metadata={"error": str(e)},
                    success=False,
                    error_message=str(e)
                ))
                logger.error(f"Error executing Stage 5 module '{module.name}': {e}")
        
        return results
    
    def _should_execute_module_in_stage4(self, module) -> bool:
        """Check if a module should execute in Stage 4."""
        from ....models import ExecutionContext, ModuleType
        return (module.type == ModuleType.ADVANCED and 
                module.execution_context == ExecutionContext.POST_RESPONSE and
                not module.requires_ai_inference)
    
    def _should_execute_module_in_stage5(self, module) -> bool:
        """Check if a module should execute in Stage 5."""
        from ....models import ExecutionContext, ModuleType
        return (module.type == ModuleType.ADVANCED and 
                module.execution_context == ExecutionContext.POST_RESPONSE and
                module.requires_ai_inference)
    
    def _store_result_in_conversation_state(
        self,
        db_session: Session,
        conversation_id: str, 
        module,
        result: PostResponseExecutionResult,
        stage: str
    ) -> None:
        """
        Store POST_RESPONSE result in ConversationState for next cycle.
        
        Args:
            db_session: Database session
            conversation_id: Conversation ID
            module: Module that was executed  
            result: PostResponseExecutionResult from execution
            stage: "stage4" or "stage5"
        """
        try:
            from ....models.conversation_state import ConversationState
            
            ConversationState.store_execution_result(
                db_session=db_session,
                conversation_id=conversation_id,
                module_id=str(module.id),
                execution_stage=stage,
                variables=result.variables,
                execution_metadata=result.execution_metadata
            )
            
            logger.debug(f"Stored {stage} result for module '{module.name}' in conversation {conversation_id}")
            
        except Exception as e:
            logger.error(f"Failed to store {stage} result for module '{module.name}': {e}")
            # Don't raise - this is not critical for execution flow