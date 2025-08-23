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
        
        # Get or create conversation for this persona
        # For now, we'll use a placeholder conversation_id - this should be enhanced
        # to get the actual conversation from the request or create one
        conversation_id = "temp-conversation-id"  # TODO: Get actual conversation ID
        
        # Resolve template using ModuleResolver with full context
        resolver = ModuleResolver(db_session=db)
        result = resolver.resolve_template(
            persona.template,
            conversation_id=conversation_id,
            persona_id=request.persona_id,
            db_session=db,
            trigger_context=trigger_context
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
        
        # Send message to provider
        provider_response = await provider.send_message(provider_request)
        
        # Calculate response time
        response_time = time.time() - start_time
        
        # Convert to API response with resolved system prompt for debugging
        response = ChatSendResponse.from_provider_response(
            provider_response=provider_response,
            response_time=response_time,
            resolved_system_prompt=resolved_system_prompt
        )
        
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
            
            try:
                async for provider_chunk in provider.send_message_stream(provider_request):
                    # Convert provider chunk to API chunk
                    response_time = time.time() - start_time if provider_chunk.done else None
                    api_chunk = StreamingChatResponse.from_provider_chunk(
                        provider_chunk=provider_chunk,
                        response_time=response_time
                    )
                    
                    # Format as Server-Sent Event
                    chunk_json = api_chunk.model_dump_json()
                    yield f"data: {chunk_json}\n\n"
                
                # Send final [DONE] message
                yield "data: [DONE]\n\n"
                
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