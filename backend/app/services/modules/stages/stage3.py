"""
Stage 3 Executor: Main AI Response Generation.

Handles the core AI response generation using the template resolved from
Stages 1 and 2. This is where the primary AI inference happens.
"""

import logging
from typing import List, Dict, Optional, Any, AsyncIterator
from sqlalchemy.orm import Session

from ....models import Module
from ....services.ai_providers import ChatRequest, ChatResponse, StreamingChatResponse, ProviderType, ProviderFactory
from .base_stage import BaseStageExecutor, ModuleResolutionWarning

logger = logging.getLogger(__name__)


class AIResponse:
    """Container for AI response with metadata."""
    
    def __init__(self, content: str, model: str, provider_type: str, metadata: Dict[str, Any] = None, thinking: str = None):
        self.content = content
        self.model = model
        self.provider_type = provider_type
        self.metadata = metadata or {}
        self.thinking = thinking


class Stage3Executor(BaseStageExecutor):
    """
    Executes Stage 3 of the module resolution pipeline - Main AI Response Generation.
    
    Stage 3 takes the template resolved from Stages 1 and 2 and generates
    the main AI response. This is the core AI inference stage that produces
    the primary response content.
    
    Unlike other stages, Stage 3 doesn't resolve modules - it generates
    the AI response that will be processed by Stages 4 and 5.
    """
    
    STAGE_NUMBER = 3
    STAGE_NAME = "Main AI Response Generation"
    
    async def execute_stage_async(
        self,
        resolved_template: str,
        user_message: str,
        warnings: List[ModuleResolutionWarning],
        resolved_modules: List[str],
        conversation_id: Optional[str] = None,
        persona_id: Optional[str] = None,
        db_session: Optional[Session] = None,
        trigger_context: Optional[Dict[str, Any]] = None,
        current_provider: Optional[str] = None,
        current_provider_settings: Optional[Dict[str, Any]] = None,
        current_chat_controls: Optional[Dict[str, Any]] = None
    ) -> AIResponse:
        """
        Execute Stage 3 AI response generation.
        
        Args:
            resolved_template: System prompt template resolved from Stages 1+2
            user_message: User's message to respond to
            warnings: List to collect resolution warnings
            resolved_modules: List to track successfully resolved modules
            conversation_id: Optional conversation context
            persona_id: Optional persona context
            db_session: Optional database session
            trigger_context: Optional trigger context
            current_provider: AI provider to use ("ollama" or "openai")
            current_provider_settings: Provider connection settings
            current_chat_controls: Chat control parameters
            
        Returns:
            AIResponse with generated content and metadata
        """
        logger.debug("Executing Stage 3: Main AI Response Generation")
        
        if not current_provider or not current_provider_settings:
            raise ValueError("Stage 3 requires AI provider and settings")
        
        try:
            # Create provider instance
            provider_type = ProviderType.OLLAMA if current_provider == "ollama" else ProviderType.OPENAI
            provider = ProviderFactory.create_provider(provider_type)
            
            # Build chat request
            chat_request = ChatRequest(
                message=user_message,
                provider_type=provider_type,
                provider_settings=current_provider_settings,
                chat_controls=current_chat_controls or {},
                system_prompt=resolved_template
            )
            
            # Generate AI response
            response = await provider.send_message(chat_request)
            
            # Create AI response container
            ai_response = AIResponse(
                content=response.content,
                model=response.model,
                provider_type=response.provider_type.value,
                metadata=response.metadata,
                thinking=response.thinking
            )
            
            logger.debug(f"Stage 3 completed: Generated {len(ai_response.content)} character response")
            return ai_response
            
        except Exception as e:
            logger.error(f"Stage 3 AI generation failed: {e}")
            warnings.append(ModuleResolutionWarning(
                module_name="stage3_ai_generation",
                warning_type="ai_generation_error",
                message=f"AI response generation failed: {str(e)}",
                stage=self.STAGE_NUMBER
            ))
            # Return empty response on failure
            return AIResponse(
                content=f"[AI Response Generation Error: {str(e)}]",
                model="unknown",
                provider_type=current_provider or "unknown",
                metadata={"error": str(e)}
            )
    
    async def execute_stage_streaming(
        self,
        resolved_template: str,
        user_message: str,
        warnings: List[ModuleResolutionWarning],
        resolved_modules: List[str],
        conversation_id: Optional[str] = None,
        persona_id: Optional[str] = None,
        db_session: Optional[Session] = None,
        trigger_context: Optional[Dict[str, Any]] = None,
        current_provider: Optional[str] = None,
        current_provider_settings: Optional[Dict[str, Any]] = None,
        current_chat_controls: Optional[Dict[str, Any]] = None
    ) -> AsyncIterator[StreamingChatResponse]:
        """
        Execute Stage 3 with streaming AI response generation.
        
        Args:
            resolved_template: System prompt template resolved from Stages 1+2
            user_message: User's message to respond to
            warnings: List to collect resolution warnings
            resolved_modules: List to track successfully resolved modules
            conversation_id: Optional conversation context
            persona_id: Optional persona context
            db_session: Optional database session
            trigger_context: Optional trigger context
            current_provider: AI provider to use ("ollama" or "openai")
            current_provider_settings: Provider connection settings
            current_chat_controls: Chat control parameters
            
        Yields:
            StreamingChatResponse chunks from AI provider
        """
        logger.debug("Executing Stage 3: Streaming AI Response Generation")
        
        if not current_provider or not current_provider_settings:
            error_msg = "Stage 3 requires AI provider and settings"
            logger.error(error_msg)
            warnings.append(ModuleResolutionWarning(
                module_name="stage3_ai_generation",
                warning_type="configuration_error",
                message=error_msg,
                stage=self.STAGE_NUMBER
            ))
            return
        
        try:
            # Create provider instance
            provider_type = ProviderType.OLLAMA if current_provider == "ollama" else ProviderType.OPENAI
            provider = ProviderFactory.create_provider(provider_type)
            
            # Build chat request
            chat_request = ChatRequest(
                message=user_message,
                provider_type=provider_type,
                provider_settings=current_provider_settings,
                chat_controls=current_chat_controls or {},
                system_prompt=resolved_template
            )
            
            # Stream AI response
            chunk_count = 0
            async for chunk in provider.send_message_stream(chat_request):
                chunk_count += 1
                yield chunk
            
            logger.debug(f"Stage 3 streaming completed: {chunk_count} chunks generated")
            
        except Exception as e:
            logger.error(f"Stage 3 streaming AI generation failed: {e}")
            warnings.append(ModuleResolutionWarning(
                module_name="stage3_ai_generation",
                warning_type="ai_generation_error",
                message=f"Streaming AI response generation failed: {str(e)}",
                stage=self.STAGE_NUMBER
            ))
            # Note: In streaming mode, we can't return an error response chunk
            # The caller will need to handle the exception
    
    def execute_stage(
        self,
        template: str,
        warnings: List[ModuleResolutionWarning],
        resolved_modules: List[str],
        **kwargs
    ) -> str:
        """
        Synchronous execute_stage method (required by BaseStageExecutor).
        
        For Stage 3, this is not typically used since AI generation is async.
        This method raises NotImplementedError to indicate async execution should be used.
        """
        raise NotImplementedError(
            "Stage 3 requires async execution. Use execute_stage_async() or execute_stage_streaming() instead."
        )
    
    def _get_modules_for_stage(self, db_session: Session, persona_id: Optional[str]) -> List[Module]:
        """
        Stage 3 doesn't use database modules - it generates AI responses.
        
        Returns:
            Empty list (Stage 3 doesn't resolve modules)
        """
        return []
    
    def _should_execute_module(self, module: Module) -> bool:
        """
        Stage 3 doesn't execute modules - it generates AI responses.
        
        Returns:
            False (Stage 3 doesn't process modules)
        """
        return False
    
    @staticmethod
    def validate_requirements(
        current_provider: Optional[str],
        current_provider_settings: Optional[Dict[str, Any]]
    ) -> bool:
        """
        Validate that Stage 3 has the required AI provider configuration.
        
        Args:
            current_provider: AI provider name
            current_provider_settings: Provider settings
            
        Returns:
            True if Stage 3 can execute with given configuration
        """
        if not current_provider:
            return False
        
        if not current_provider_settings:
            return False
        
        if current_provider not in ["ollama", "openai"]:
            return False
        
        return True