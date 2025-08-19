"""
FastAPI endpoints for chat functionality.
"""

import time
import logging
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import ValidationError

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

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


def get_provider_settings_from_request(request: ChatSendRequest) -> Optional[Dict[str, Any]]:
    """
    Get provider settings from the request.
    
    The frontend now passes provider settings directly in the request,
    so we extract them from there instead of loading from backend storage.
    """
    return request.provider_settings


@router.post("/send", response_model=ChatSendResponse)
async def send_chat_message(request: ChatSendRequest) -> ChatSendResponse:
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
        # Create provider instance - convert ChatProvider to ProviderType
        provider_type = ProviderType.OLLAMA if request.provider == ChatProvider.OLLAMA else ProviderType.OPENAI
        provider = ProviderFactory.create_provider(provider_type)
        
        # Convert to provider request (provider_settings are now included in request)
        provider_request = request.to_provider_request()
        
        # Send message to provider
        provider_response = await provider.send_message(provider_request)
        
        # Calculate response time
        response_time = time.time() - start_time
        
        # Convert to API response
        response = ChatSendResponse.from_provider_response(
            provider_response=provider_response,
            response_time=response_time
        )
        
        return response
        
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
async def stream_chat_message(request: ChatSendRequest):
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
        # Create provider instance - convert ChatProvider to ProviderType
        provider_type = ProviderType.OLLAMA if request.provider == ChatProvider.OLLAMA else ProviderType.OPENAI
        provider = ProviderFactory.create_provider(provider_type)
        
        # Convert to provider request (provider_settings are now included in request)
        provider_request = request.to_provider_request()
        
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