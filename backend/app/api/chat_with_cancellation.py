"""
Enhanced FastAPI endpoints for chat functionality with cancellation support.

Extends the original chat API to include session management, cancellation,
and consecutive message capabilities while maintaining backward compatibility.
"""

import time
import logging
import uuid
import asyncio
import json
from typing import Dict, Any, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, status, Depends, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session

from .chat_models import (
    ChatSendRequest,
    ChatSendResponse, 
    StreamingChatResponse,
    ChatError,
    ChatProvider,
    ProcessingStage
)
from ..services.ai_providers import ProviderFactory, ProviderType
from ..services.exceptions import (
    ProviderConnectionError,
    ProviderAuthenticationError,
    UnsupportedProviderError
)
from ..services.staged_module_resolver_with_cancellation import StagedModuleResolverWithCancellation
from ..services.streaming_accumulator import StreamingAccumulator, StreamingToNonStreamingConverter
from ..services.chat_session_manager import get_chat_session_manager, ChatSessionManager, SessionStatus
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


async def resolve_system_prompt_with_session(
    request: ChatSendRequest, 
    db: Session,
    session_id: Optional[str] = None
) -> str:
    """
    Resolve system prompt from persona template with module resolution and session management.
    
    Args:
        request: Chat request containing optional persona_id
        db: Database session
        session_id: Optional session ID for cancellation support
        
    Returns:
        Resolved system prompt (empty string if no persona)
        
    Raises:
        HTTPException: If persona is not found or inactive
        asyncio.CancelledError: If cancelled during resolution
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
        
        # Use conversation_id from request if provided
        conversation_id = request.conversation_id
        
        # Extract current session context from request for advanced modules
        current_provider = request.provider.value if request.provider else None
        current_provider_settings = request.provider_settings
        current_chat_controls = request.chat_controls
        
        # Use enhanced resolver with cancellation support
        resolver = StagedModuleResolverWithCancellation(db_session=db)
        resolver.enable_state_tracking()  # Enable SystemPromptState tracking
        
        if session_id:
            resolver.set_session_id(session_id)
        
        # Resolve template using async method with cancellation support
        result = await resolver.resolve_template_stage1_and_stage2_async(
            persona.template,
            conversation_id=conversation_id,
            persona_id=request.persona_id,
            db_session=db,
            trigger_context=trigger_context,
            current_provider=current_provider,
            current_provider_settings=current_provider_settings,
            current_chat_controls=current_chat_controls,
            session_id=session_id
        )
        
        # Log warnings for debugging
        if result.warnings:
            logger.warning(f"Template resolution warnings for persona {persona.id}: {len(result.warnings)} warnings")
            for warning in result.warnings:
                logger.warning(f"  {warning.warning_type}: {warning.message}")
        
        return result.resolved_template
        
    except asyncio.CancelledError:
        logger.info(f"System prompt resolution cancelled for session {session_id}")
        raise
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
async def send_chat_message_with_cancellation(
    request: ChatSendRequest, 
    response: Response,
    db: Session = Depends(get_db),
    session_manager: ChatSessionManager = Depends(get_chat_session_manager)
) -> ChatSendResponse:
    """
    Send a chat message and get a complete response with cancellation support.
    
    This endpoint now uses streaming internally with accumulation to enable
    cancellation for all request types while maintaining API compatibility.
    
    Args:
        request: Chat request with message, provider, and controls
        response: Response object for setting headers
        db: Database session
        session_manager: Chat session manager for cancellation
        
    Returns:
        Chat response with content and metadata
        
    Raises:
        HTTPException: For various error conditions
        asyncio.CancelledError: If cancelled during processing
    """
    start_time = time.time()
    
    # Generate session ID for this request
    session_id = str(uuid.uuid4())
    
    # Add session ID to response headers
    response.headers["X-Session-ID"] = session_id
    
    # Get provider settings from request
    provider_settings = get_provider_settings_from_request(request)
    if not provider_settings:
        error = ChatError(
            error_type="configuration_error",
            message=f"{request.provider.value} provider settings not found or incomplete"
        )
        raise HTTPException(status_code=400, detail=error.model_dump())
    
    try:
        # Resolve system prompt from persona with session support
        resolved_system_prompt = await resolve_system_prompt_with_session(
            request, db, session_id
        )
        
        # Create enhanced provider instance with cancellation support
        provider_type = ProviderType.OLLAMA if request.provider == ChatProvider.OLLAMA else ProviderType.OPENAI
        provider = ProviderFactory.create_provider(provider_type, with_cancellation=True)
        
        # Set session ID for provider
        if hasattr(provider, 'set_session_id'):
            provider.set_session_id(session_id)
        
        # Convert to provider request with resolved system prompt
        provider_request = request.to_provider_request(system_prompt=resolved_system_prompt)
        
        # Use streaming with accumulation for cancellation support
        converter = StreamingToNonStreamingConverter()
        
        # Get streaming response from provider
        if hasattr(provider, 'send_message_stream_with_session'):
            stream_generator = provider.send_message_stream_with_session(
                provider_request,
                session_id=session_id,
                conversation_id=request.conversation_id
            )
        else:
            # Fallback to standard streaming
            stream_generator = provider.send_message_stream(provider_request)
        
        # Convert streaming to single response with cancellation
        provider_response = await converter.convert_streaming_to_response(
            stream_generator=stream_generator,
            session_id=session_id,
            conversation_id=request.conversation_id
        )
        
        # Calculate response time
        response_time = time.time() - start_time
        
        # Create debug data (simplified for now)
        from .chat_models import DebugData
        debug_data = DebugData(
            provider_request=provider_response.metadata.get("debug_api_request", {}),
            provider_response=provider_response.metadata.get("debug_api_response", {}),
            request_timestamp=start_time,
            response_timestamp=time.time()
        )
        
        # Convert to API response
        api_response = ChatSendResponse.from_provider_response(
            provider_response=provider_response,
            response_time=response_time,
            resolved_system_prompt=resolved_system_prompt,
            debug_data=debug_data
        )
        
        # Execute POST_RESPONSE modules asynchronously (Stages 4 & 5)
        if request.persona_id:
            asyncio.create_task(execute_post_response_modules_async(
                request, db, session_id
            ))
        
        return api_response
        
    except asyncio.CancelledError:
        logger.info(f"Chat message cancelled for session {session_id}")
        # Return partial response or error as appropriate
        raise HTTPException(
            status_code=499,  # Client Closed Request
            detail={"error_type": "request_cancelled", "message": "Request was cancelled"}
        )
    except (ProviderConnectionError, ProviderAuthenticationError, UnsupportedProviderError) as e:
        error = ChatError.from_exception(e)
        raise HTTPException(status_code=400, detail=error.model_dump())
    except ValidationError as e:
        error = ChatError.from_validation_error(e)
        raise HTTPException(status_code=422, detail=error.model_dump())
    except Exception as e:
        logger.error(f"Unexpected error in chat endpoint for session {session_id}: {e}")
        error = ChatError(
            error_type="server_error",
            message=f"An unexpected error occurred: {str(e)}"
        )
        raise HTTPException(status_code=500, detail=error.model_dump())


@router.post("/stream")
async def stream_chat_message_with_cancellation(
    request: ChatSendRequest,
    db: Session = Depends(get_db),
    session_manager: ChatSessionManager = Depends(get_chat_session_manager)
) -> StreamingResponse:
    """
    Send a chat message and get a streaming response with cancellation support.
    
    Args:
        request: Chat request with message, provider, and controls
        db: Database session
        session_manager: Chat session manager for cancellation
        
    Returns:
        Streaming response with real-time content
        
    Raises:
        HTTPException: For various error conditions
    """
    # Generate session ID for this request
    session_id = str(uuid.uuid4())
    
    # Get provider settings from request
    provider_settings = get_provider_settings_from_request(request)
    if not provider_settings:
        error = ChatError(
            error_type="configuration_error",
            message=f"{request.provider.value} provider settings not found or incomplete"
        )
        raise HTTPException(status_code=400, detail=error.model_dump())
    
    async def generate_streaming_response():
        """Generate streaming response with cancellation support."""
        try:
            # Resolve system prompt with session support
            resolved_system_prompt = await resolve_system_prompt_with_session(
                request, db, session_id
            )
            
            # Create enhanced provider with cancellation
            provider_type = ProviderType.OLLAMA if request.provider == ChatProvider.OLLAMA else ProviderType.OPENAI
            provider = ProviderFactory.create_provider(provider_type, with_cancellation=True)
            
            # Set session ID for provider
            if hasattr(provider, 'set_session_id'):
                provider.set_session_id(session_id)
            
            # Convert to provider request
            provider_request = request.to_provider_request(system_prompt=resolved_system_prompt)
            
            # Stream response with session management
            if hasattr(provider, 'send_message_stream_with_session'):
                stream_generator = provider.send_message_stream_with_session(
                    provider_request,
                    session_id=session_id,
                    conversation_id=request.conversation_id
                )
            else:
                stream_generator = provider.send_message_stream(provider_request)
            
            # Convert provider chunks to API chunks and stream them
            async for provider_chunk in stream_generator:
                # Check for cancellation before each chunk
                session_manager = get_chat_session_manager()
                token = session_manager.get_session(session_id)
                if token and token.is_cancelled():
                    logger.info(f"Streaming cancelled for session {session_id}")
                    break
                
                # Convert to API format
                api_chunk = StreamingChatResponse.from_provider_chunk(
                    provider_chunk,
                    resolved_system_prompt=resolved_system_prompt if provider_chunk.done else None
                )
                
                # Send chunk as JSON line
                chunk_json = api_chunk.model_dump_json()
                yield f"{chunk_json}\n"
            
            # Send final done message
            done_chunk = StreamingChatResponse.done_event()
            yield f"{done_chunk.model_dump_json()}\n"
            
            # Execute POST_RESPONSE modules asynchronously
            if request.persona_id:
                asyncio.create_task(execute_post_response_modules_async(
                    request, db, session_id
                ))
                
        except asyncio.CancelledError:
            logger.info(f"Streaming chat cancelled for session {session_id}")
            # Send cancellation event
            cancel_event = StreamingChatResponse.create_event("cancelled", {
                "session_id": session_id,
                "message": "Request was cancelled"
            })
            yield f"{cancel_event.model_dump_json()}\n"
        except Exception as e:
            logger.error(f"Error in streaming endpoint for session {session_id}: {e}")
            # Send error event
            error_event = StreamingChatResponse.create_event("error", {
                "session_id": session_id,
                "error": str(e)
            })
            yield f"{error_event.model_dump_json()}\n"
    
    # Return streaming response with session ID in headers
    return StreamingResponse(
        generate_streaming_response(),
        media_type="text/plain",
        headers={"X-Session-ID": session_id}
    )


@router.post("/cancel/{session_id}")
async def cancel_chat_session(
    session_id: str,
    session_manager: ChatSessionManager = Depends(get_chat_session_manager)
):
    """
    Cancel an active chat session.
    
    Args:
        session_id: Session ID to cancel
        session_manager: Chat session manager
        
    Returns:
        Cancellation result
    """
    cancelled = await session_manager.cancel_session(session_id)
    
    return {
        "cancelled": cancelled,
        "session_id": session_id,
        "message": "Session cancelled successfully" if cancelled else "Session not found or already completed"
    }


@router.get("/status/{session_id}")
async def get_session_status(
    session_id: str,
    session_manager: ChatSessionManager = Depends(get_chat_session_manager)
):
    """
    Get the status of a chat session.
    
    Args:
        session_id: Session ID to check
        session_manager: Chat session manager
        
    Returns:
        Session status information
    """
    status = session_manager.get_session_status(session_id)
    
    return {
        "session_id": session_id,
        "status": status.value,
        "active": status == SessionStatus.ACTIVE
    }


@router.get("/sessions/active")
async def get_active_sessions(
    session_manager: ChatSessionManager = Depends(get_chat_session_manager)
):
    """
    Get all currently active chat sessions.
    
    Args:
        session_manager: Chat session manager
        
    Returns:
        List of active sessions
    """
    active_count = session_manager.get_active_session_count()
    
    # Get summary of active sessions (without sensitive details)
    active_sessions = []
    for session_id, token in session_manager.active_sessions.items():
        active_sessions.append({
            "session_id": session_id,
            "conversation_id": token.conversation_id,
            "current_stage": token.current_stage,
            "created_at": token.created_at.isoformat() if token.created_at else None,
            "is_cancelled": token.is_cancelled(),
            "is_active": token.is_active()
        })
    
    return {
        "active_session_count": active_count,
        "sessions": active_sessions
    }


async def execute_post_response_modules_async(
    request: ChatSendRequest,
    db: Session,
    session_id: Optional[str] = None
):
    """
    Execute POST_RESPONSE modules asynchronously (Stages 4 & 5).
    
    Args:
        request: Original chat request
        db: Database session
        session_id: Optional session ID for cancellation support
    """
    try:
        if not request.persona_id:
            return
        
        # Use enhanced resolver with cancellation
        resolver = StagedModuleResolverWithCancellation(db_session=db)
        
        if session_id:
            resolver.set_session_id(session_id)
        
        # Extract context for POST_RESPONSE modules
        trigger_context = {"last_user_message": request.message}
        current_provider = request.provider.value if request.provider else None
        current_provider_settings = request.provider_settings
        current_chat_controls = request.chat_controls
        
        # Execute POST_RESPONSE modules with cancellation support
        results = await resolver.execute_post_response_modules_async(
            request.persona_id,
            request.conversation_id,
            db,
            trigger_context=trigger_context,
            current_provider=current_provider,
            current_provider_settings=current_provider_settings,
            current_chat_controls=current_chat_controls,
            session_id=session_id
        )
        
        # Log results for debugging
        if results:
            logger.info(f"Executed {len(results)} POST_RESPONSE modules for session {session_id}")
            for result in results:
                if not result.success:
                    logger.warning(f"POST_RESPONSE module {result.module_name} failed: {result.error_message}")
                
    except asyncio.CancelledError:
        logger.info(f"POST_RESPONSE execution cancelled for session {session_id}")
        # Don't re-raise - this is background processing
    except Exception as e:
        logger.error(f"Error executing POST_RESPONSE modules for session {session_id}: {e}")
        # Don't re-raise - this is background processing