"""
FastAPI endpoints for provider connection testing.
"""

import logging
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from ..services.providers.ollama import OllamaService
from ..services.providers.openai import OpenAIService
from ..services.exceptions import (
    ProviderConnectionError,
    ProviderAuthenticationError
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/connections", tags=["connections"])


# Request models for connection testing
class OllamaConnectionTestRequest(BaseModel):
    """Request model for testing Ollama connections."""
    host: str = Field(..., description="Ollama server host URL")
    model: str = Field(..., description="Model name to test")
    route: str = Field(default="/api/chat", description="API route path")
    timeout_ms: int = Field(default=30000, description="Timeout in milliseconds")
    
    @field_validator('host')
    def validate_host(cls, v):
        if not v or not v.strip():
            raise ValueError("Host cannot be empty")
        return v.strip()
    
    @field_validator('model')
    def validate_model(cls, v):
        if not v or not v.strip():
            raise ValueError("Model cannot be empty")
        return v.strip()


class OpenAIConnectionTestRequest(BaseModel):
    """Request model for testing OpenAI connections."""
    base_url: str = Field(..., description="OpenAI API base URL")
    api_key: str = Field(..., description="API key for authentication")
    default_model: str = Field(..., description="Default model to test")
    organization: str = Field(default="", description="Organization ID (optional)")
    project: str = Field(default="", description="Project ID (optional)")
    timeout_ms: int = Field(default=60000, description="Timeout in milliseconds")
    
    @field_validator('base_url')
    def validate_base_url(cls, v):
        if not v or not v.strip():
            raise ValueError("Base URL cannot be empty")
        return v.strip()
    
    @field_validator('api_key')
    def validate_api_key(cls, v):
        if not v or not v.strip():
            raise ValueError("API key cannot be empty")
        return v.strip()
    
    @field_validator('default_model')
    def validate_default_model(cls, v):
        if not v or not v.strip():
            raise ValueError("Default model cannot be empty")
        return v.strip()


# Response model for connection tests
class ConnectionTestResponse(BaseModel):
    """Response model for connection tests."""
    status: str = Field(..., description="Connection status (success/error)")
    message: str = Field(..., description="Human-readable status message")
    model: str = Field(default="", description="Model that was tested")
    organization: str = Field(default="", description="Organization (OpenAI only)")
    version: str = Field(default="", description="Service version (if available)")


class ConnectionTestError(BaseModel):
    """Error response model for connection tests."""
    status: str = Field(default="error", description="Error status")
    message: str = Field(..., description="Error message")
    error_type: str = Field(..., description="Type of error")


@router.post("/ollama/test", response_model=ConnectionTestResponse)
async def test_ollama_connection(request: OllamaConnectionTestRequest) -> ConnectionTestResponse:
    """
    Test connection to Ollama server.
    
    Args:
        request: Ollama connection test request
        
    Returns:
        Connection test result
        
    Raises:
        HTTPException: For connection or validation errors
    """
    try:
        # Convert request to settings dict
        settings = {
            "host": request.host,
            "model": request.model,
            "route": request.route,
            "timeout_ms": request.timeout_ms
        }
        
        # Create service instance and test connection
        ollama_service = OllamaService()
        is_connected = await ollama_service.test_connection(settings)
        
        if is_connected:
            return ConnectionTestResponse(
                status="connected",
                message="Connection successful",
                model=request.model,
                version=""
            )
        else:
            return ConnectionTestResponse(
                status="failed",
                message="Connection failed",
                model=request.model,
                version=""
            )
        
    except ProviderConnectionError as e:
        logger.error(f"Ollama connection test failed: {e}")
        error = ConnectionTestError(
            message=str(e),
            error_type="connection_error"
        )
        raise HTTPException(status_code=500, detail=error.model_dump())
        
    except Exception as e:
        logger.error(f"Unexpected error in Ollama connection test: {e}")
        error = ConnectionTestError(
            message=f"Unexpected error: {str(e)}",
            error_type="internal_error"
        )
        raise HTTPException(status_code=500, detail=error.model_dump())


# Response model for model lists
class ModelInfo(BaseModel):
    """Model information."""
    id: str = Field(..., description="Model ID")
    name: str = Field(..., description="Model display name")
    object: str = Field(default="model", description="Object type")
    created: int = Field(default=0, description="Creation timestamp")
    owned_by: str = Field(default="", description="Owner organization")


class ModelsListResponse(BaseModel):
    """Response model for model lists."""
    object: str = Field(default="list", description="Response object type")
    data: list[ModelInfo] = Field(..., description="List of available models")


# Request models for model listing
class ModelsListRequest(BaseModel):
    """Request model for listing models from providers."""
    # Ollama settings
    host: str = Field(default="http://localhost:11434", description="Provider host URL")
    
    # OpenAI settings (optional for Ollama)  
    api_key: str = Field(default="", description="API key (required for OpenAI)")
    base_url: str = Field(default="", description="Base URL (OpenAI-compatible)")
    organization: str = Field(default="", description="Organization (OpenAI)")
    project: str = Field(default="", description="Project (OpenAI)")


@router.post("/{provider}/models", response_model=ModelsListResponse)
async def list_provider_models(provider: str, request: ModelsListRequest) -> ModelsListResponse:
    """
    Get available models from a provider using the /v1/models endpoint.
    
    Args:
        provider: The provider name ("ollama" or "openai")
        
    Returns:
        List of available models in OpenAI format
        
    Raises:
        HTTPException: For connection or validation errors
    """
    if provider not in ["ollama", "openai"]:
        error = ConnectionTestError(
            message=f"Unsupported provider: {provider}",
            error_type="validation_error"
        )
        raise HTTPException(status_code=400, detail=error.model_dump())
    
    try:
        if provider == "ollama":
            # Create service instance and get models
            ollama_service = OllamaService()
            settings = {"host": request.host}
            models = await ollama_service.list_models(settings)
        else:  # openai
            # Create service instance and get models
            openai_service = OpenAIService()
            settings = {
                "base_url": request.base_url,
                "api_key": request.api_key,
                "organization": request.organization,
                "project": request.project
            }
            models = await openai_service.list_models(settings)
        
        # Convert model strings to ModelInfo objects
        model_infos = []
        for model_name in models:
            model_info = ModelInfo(
                id=model_name,
                name=model_name,
                object="model",
                created=0,
                owned_by=f"{provider}"
            )
            model_infos.append(model_info)
        
        return ModelsListResponse(data=model_infos)
        
    except ProviderConnectionError as e:
        logger.error(f"{provider.capitalize()} models list failed: {e}")
        error = ConnectionTestError(
            message=str(e),
            error_type="connection_error"
        )
        raise HTTPException(status_code=500, detail=error.model_dump())
        
    except ProviderAuthenticationError as e:
        logger.error(f"{provider.capitalize()} models authentication failed: {e}")
        error = ConnectionTestError(
            message=str(e),
            error_type="connection_error"  # Map auth errors to connection errors for consistency
        )
        raise HTTPException(status_code=500, detail=error.model_dump())
        
    except Exception as e:
        logger.error(f"Unexpected error in {provider} models list: {e}")
        error = ConnectionTestError(
            message=f"Unexpected error: {str(e)}",
            error_type="internal_error"
        )
        raise HTTPException(status_code=500, detail=error.model_dump())


@router.post("/openai/test", response_model=ConnectionTestResponse)
async def test_openai_connection(request: OpenAIConnectionTestRequest) -> ConnectionTestResponse:
    """
    Test connection to OpenAI API.
    
    Args:
        request: OpenAI connection test request
        
    Returns:
        Connection test result
        
    Raises:
        HTTPException: For connection, authentication, or validation errors
    """
    try:
        # Convert request to settings dict
        settings = {
            "base_url": request.base_url,
            "api_key": request.api_key,
            "default_model": request.default_model,
            "organization": request.organization,
            "project": request.project,
            "timeout_ms": request.timeout_ms
        }
        
        # Create service instance and test connection
        openai_service = OpenAIService()
        is_connected = await openai_service.test_connection(settings)
        
        if is_connected:
            return ConnectionTestResponse(
                status="connected",
                message="Connection successful",
                model=request.default_model,
                organization=request.organization
            )
        else:
            return ConnectionTestResponse(
                status="failed",
                message="Connection failed",
                model=request.default_model,
                organization=request.organization
            )
        
    except ProviderAuthenticationError as e:
        logger.error(f"OpenAI authentication failed: {e}")
        error = ConnectionTestError(
            message=str(e),
            error_type="authentication_error"
        )
        raise HTTPException(status_code=401, detail=error.model_dump())
        
    except ProviderConnectionError as e:
        logger.error(f"OpenAI connection test failed: {e}")
        error = ConnectionTestError(
            message=str(e),
            error_type="connection_error"
        )
        raise HTTPException(status_code=500, detail=error.model_dump())
        
    except Exception as e:
        logger.error(f"Unexpected error in OpenAI connection test: {e}")
        error = ConnectionTestError(
            message=f"Unexpected error: {str(e)}",
            error_type="internal_error"
        )
        raise HTTPException(status_code=500, detail=error.model_dump())