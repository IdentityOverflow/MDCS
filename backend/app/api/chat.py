"""
FastAPI endpoints for chat functionality.
"""

import time
import logging
from typing import Dict, Any, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import StreamingResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session

from .chat_models import (
    ChatSendRequest,
    ChatSendResponse, 
    StreamingChatResponse,
    ChatError,
    ChatProvider
)
from ..services.ai_providers import ProviderFactory, ProviderType
from ..services.exceptions import (
    ProviderConnectionError,
    ProviderAuthenticationError,
    UnsupportedProviderError
)
from ..services.module_resolver import ModuleResolver
from ..database.connection import get_db
from ..models import Persona

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


def get_provider_settings_from_request(request: ChatSendRequest) -> Optional[Dict[str, Any]]:
    """
    Get provider settings from the request.
    
    The frontend now passes provider settings directly in the request,
    so we extract them from there instead of loading from backend storage.
    """
    return request.provider_settings


async def resolve_system_prompt(request: ChatSendRequest, db: Session) -> str:
    """
    Resolve system prompt from persona template with module resolution.
    
    Args:
        request: Chat request containing optional persona_id
        db: Database session
        
    Returns:
        Resolved system prompt (empty string if no persona)
        
    Raises:
        HTTPException: If persona is not found or inactive
    """
    if not request.persona_id:
        return ""
    
    try:
        # Convert persona_id to UUID and fetch persona
        persona_uuid = UUID(request.persona_id)
        persona = db.query(Persona).filter(
            Persona.id == persona_uuid,
            Persona.is_active == True
        ).first()
        
        if not persona:
            raise HTTPException(
                status_code=404,
                detail=f"Persona with ID {request.persona_id} not found or inactive"
            )
        
        # If persona has no template, return empty string
        if not persona.template:
            return ""
        
        # Build trigger context from user message for advanced modules
        trigger_context = {"last_user_message": request.message}
        
        # Use conversation_id from request if provided, otherwise fallback to None
        # When None, advanced modules that need conversation context will return empty/default values
        conversation_id = request.conversation_id
        
        # Extract current session context from request for advanced modules
        current_provider = request.provider.value if request.provider else None
        current_provider_settings = request.provider_settings
        current_chat_controls = request.chat_controls
        
        # Resolve template using ModuleResolver with full context including session info
        resolver = ModuleResolver(db_session=db)
        result = resolver.resolve_template(
            persona.template,
            conversation_id=conversation_id,
            persona_id=request.persona_id,
            db_session=db,
            trigger_context=trigger_context,
            current_provider=current_provider,
            current_provider_settings=current_provider_settings,
            current_chat_controls=current_chat_controls
        )
        
        # Log warnings for debugging
        if result.warnings:
            logger.warning(f"Template resolution warnings for persona {persona.id}: {len(result.warnings)} warnings")
            for warning in result.warnings:
                logger.warning(f"  {warning.warning_type}: {warning.message}")
        
        return result.resolved_template
        
    except ValueError:
        # Invalid UUID format
        raise HTTPException(
            status_code=400,
            detail=f"Invalid persona ID format: {request.persona_id}"
        )
    except HTTPException:
        # Re-raise HTTPException (e.g., persona not found) without modification
        raise
    except Exception as e:
        logger.error(f"Error resolving system prompt for persona {request.persona_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to resolve system prompt: {str(e)}"
        )


@router.post("/send", response_model=ChatSendResponse)
async def send_chat_message(request: ChatSendRequest, db: Session = Depends(get_db)) -> ChatSendResponse:
    """
    Send a chat message and get a complete response.
    
    Args:
        request: Chat request with message, provider, and controls
        
    Returns:
        Chat response with content and metadata
        
    Raises:
        HTTPException: For various error conditions
    """
    start_time = time.time()
    
    # Get provider settings from request - check outside try block so HTTPException propagates
    provider_settings = get_provider_settings_from_request(request)
    if not provider_settings:
        error = ChatError(
            error_type="configuration_error",
            message=f"{request.provider.value} provider settings not found or incomplete"
        )
        raise HTTPException(status_code=400, detail=error.model_dump())
    
    try:
        # Resolve system prompt from persona (if provided)
        resolved_system_prompt = await resolve_system_prompt(request, db)
        
        # Debug logging
        if request.persona_id:
            logger.info(f"Chat request with persona_id: {request.persona_id}")
            logger.info(f"Resolved system prompt: '{resolved_system_prompt[:100]}...' ({len(resolved_system_prompt)} chars)")
        else:
            logger.info("Chat request without persona_id")
        
        # Create provider instance - convert ChatProvider to ProviderType
        provider_type = ProviderType.OLLAMA if request.provider == ChatProvider.OLLAMA else ProviderType.OPENAI
        provider = ProviderFactory.create_provider(provider_type)
        
        # Convert to provider request with resolved system prompt
        provider_request = request.to_provider_request(system_prompt=resolved_system_prompt)
        
        # Capture request timestamp for debug data
        request_timestamp = time.time()
        
        # Send message to provider
        provider_response = await provider.send_message(provider_request)
        
        # Capture response timestamp for debug data
        response_timestamp = time.time()
        response_time = response_timestamp - start_time
        
        # Create debug data for the request/response - use actual API format
        from .chat_models import DebugData
        
        debug_data = DebugData(
            provider_request=provider_response.metadata.get("debug_api_request", {}),
            provider_response=provider_response.metadata.get("debug_api_response", {}),
            request_timestamp=request_timestamp,
            response_timestamp=response_timestamp
        )
        
        # Convert to API response with resolved system prompt and debug data
        response = ChatSendResponse.from_provider_response(
            provider_response=provider_response,
            response_time=response_time,
            resolved_system_prompt=resolved_system_prompt,
            debug_data=debug_data
        )
        
        # Execute AFTER timing modules asynchronously (don't block response)
        if request.persona_id:
            import asyncio
            
            async def run_after_modules():
                """Run AFTER timing modules in background without blocking response."""
                try:
                    # Extract session context for AFTER modules
                    current_provider = request.provider.value if request.provider else None
                    current_provider_settings = request.provider_settings
                    current_chat_controls = request.chat_controls
                    
                    resolver = ModuleResolver(db_session=db)
                    trigger_context = {"last_ai_message": provider_response.content}
                    
                    resolver.execute_after_timing_modules(
                        persona_id=request.persona_id,
                        conversation_id=request.conversation_id,
                        db_session=db,
                        trigger_context=trigger_context,
                        current_provider=current_provider,
                        current_provider_settings=current_provider_settings,
                        current_chat_controls=current_chat_controls
                    )
                except Exception as e:
                    # Don't fail the response if AFTER modules fail
                    logger.error(f"Error executing AFTER timing modules: {e}")
            
            # Schedule AFTER modules to run in background without waiting
            asyncio.create_task(run_after_modules())
        
        return response
        
    except HTTPException:
        # Re-raise HTTPException (from persona resolution) without modification
        raise
        
    except ProviderAuthenticationError as e:
        logger.error(f"Authentication error: {e}")
        error = ChatError.from_exception(e)
        raise HTTPException(status_code=401, detail=error.model_dump())
        
    except ProviderConnectionError as e:
        logger.error(f"Connection error: {e}")
        error = ChatError.from_exception(e)
        raise HTTPException(status_code=500, detail=error.model_dump())
        
    except UnsupportedProviderError as e:
        logger.error(f"Unsupported provider error: {e}")
        error = ChatError.from_exception(e)
        raise HTTPException(status_code=400, detail=error.model_dump())
        
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        error = ChatError.from_validation_error(e)
        raise HTTPException(status_code=422, detail=error.model_dump())
        
    except Exception as e:
        logger.error(f"Unexpected error in chat send: {e}")
        error = ChatError(
            error_type="internal_error",
            message=f"An unexpected error occurred: {str(e)}"
        )
        raise HTTPException(status_code=500, detail=error.model_dump())


@router.post("/stream")
async def stream_chat_message(request: ChatSendRequest, db: Session = Depends(get_db)):
    """
    Send a chat message and get a streaming response.
    
    Args:
        request: Chat request with message, provider, and controls
        
    Returns:
        StreamingResponse with Server-Sent Events
        
    Raises:
        HTTPException: For various error conditions
    """
    # Validate that streaming is enabled
    if not request.stream:
        error = ChatError(
            error_type="validation_error", 
            message="Stream must be true for streaming endpoint"
        )
        raise HTTPException(status_code=400, detail=error.model_dump())
    
    # Get provider settings from request - check outside try block so HTTPException propagates
    provider_settings = get_provider_settings_from_request(request)
    if not provider_settings:
        error = ChatError(
            error_type="configuration_error",
            message=f"{request.provider.value} provider settings not found or incomplete"
        )
        raise HTTPException(status_code=400, detail=error.model_dump())
    
    try:
        # Resolve system prompt from persona (if provided)
        resolved_system_prompt = await resolve_system_prompt(request, db)
        
        # Debug logging for streaming
        if request.persona_id:
            logger.info(f"Streaming request with persona_id: {request.persona_id}")
            logger.info(f"Resolved system prompt for streaming: '{resolved_system_prompt[:100]}...' ({len(resolved_system_prompt)} chars)")
        else:
            logger.info("Streaming request without persona_id")
        
        # Create provider instance - convert ChatProvider to ProviderType
        provider_type = ProviderType.OLLAMA if request.provider == ChatProvider.OLLAMA else ProviderType.OPENAI
        provider = ProviderFactory.create_provider(provider_type)
        
        # Convert to provider request with resolved system prompt
        provider_request = request.to_provider_request(system_prompt=resolved_system_prompt)
        
        async def generate_stream():
            """Generate Server-Sent Events stream."""
            start_time = time.time()
            request_timestamp = time.time()
            accumulated_content = ""
            accumulated_thinking = ""
            final_metadata = None
            
            try:
                async for provider_chunk in provider.send_message_stream(provider_request):
                    # Accumulate content and metadata for debug data
                    accumulated_content += provider_chunk.content
                    if provider_chunk.thinking:
                        accumulated_thinking += provider_chunk.thinking
                    if provider_chunk.done:
                        final_metadata = provider_chunk.metadata
                    
                    # Prepare debug data for final chunk - use actual API format
                    debug_data = None
                    if provider_chunk.done:
                        response_timestamp = time.time()
                        from .chat_models import DebugData
                        
                        debug_data = DebugData(
                            provider_request=provider_chunk.metadata.get("debug_api_request", {}),
                            provider_response=provider_chunk.metadata.get("debug_api_response", {}),
                            request_timestamp=request_timestamp,
                            response_timestamp=response_timestamp
                        )
                    
                    # Convert provider chunk to API chunk
                    response_time = time.time() - start_time if provider_chunk.done else None
                    api_chunk = StreamingChatResponse.from_provider_chunk(
                        provider_chunk=provider_chunk,
                        response_time=response_time,
                        resolved_system_prompt=resolved_system_prompt if provider_chunk.done else None,
                        debug_data=debug_data
                    )
                    
                    # Format as Server-Sent Event
                    chunk_json = api_chunk.model_dump_json()
                    yield f"data: {chunk_json}\n\n"
                
                # Send final [DONE] message
                yield "data: [DONE]\n\n"
                
                # Execute AFTER timing modules asynchronously (don't block streaming completion)
                if request.persona_id:
                    import asyncio
                    
                    async def run_after_modules_streaming():
                        """Run AFTER timing modules in background without blocking streaming."""
                        try:
                            # Extract session context for AFTER modules
                            current_provider = request.provider.value if request.provider else None
                            current_provider_settings = request.provider_settings
                            current_chat_controls = request.chat_controls
                            
                            resolver = ModuleResolver(db_session=db)
                            trigger_context = {"last_ai_message": accumulated_content}
                            
                            resolver.execute_after_timing_modules(
                                persona_id=request.persona_id,
                                conversation_id=request.conversation_id,
                                db_session=db,
                                trigger_context=trigger_context,
                                current_provider=current_provider,
                                current_provider_settings=current_provider_settings,
                                current_chat_controls=current_chat_controls
                            )
                        except Exception as e:
                            # Don't fail the streaming if AFTER modules fail
                            logger.error(f"Error executing AFTER timing modules in streaming: {e}")
                    
                    # Schedule AFTER modules to run in background without waiting
                    asyncio.create_task(run_after_modules_streaming())
                
            except Exception as e:
                # Send error as SSE
                error = ChatError.from_exception(e)
                error_json = error.model_dump_json()
                yield f"data: {error_json}\n\n"
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
        
    except HTTPException:
        # Re-raise HTTPException (from persona resolution) without modification
        raise
        
    except ProviderAuthenticationError as e:
        logger.error(f"Authentication error in streaming: {e}")
        error = ChatError.from_exception(e)
        raise HTTPException(status_code=401, detail=error.model_dump())
        
    except ProviderConnectionError as e:
        logger.error(f"Connection error in streaming: {e}")
        error = ChatError.from_exception(e)
        raise HTTPException(status_code=500, detail=error.model_dump())
        
    except UnsupportedProviderError as e:
        logger.error(f"Unsupported provider error in streaming: {e}")
        error = ChatError.from_exception(e)
        raise HTTPException(status_code=400, detail=error.model_dump())
        
    except ValidationError as e:
        logger.error(f"Validation error in streaming: {e}")
        error = ChatError.from_validation_error(e)
        raise HTTPException(status_code=422, detail=error.model_dump())
        
    except Exception as e:
        logger.error(f"Unexpected error in chat streaming: {e}")
        error = ChatError(
            error_type="internal_error",
            message=f"An unexpected error occurred: {str(e)}"
        )
        raise HTTPException(status_code=500, detail=error.model_dump())