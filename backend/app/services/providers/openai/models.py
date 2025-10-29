"""
OpenAI-specific request and response models.
"""

from typing import Dict, Any, Optional, List, Union
from pydantic import BaseModel


class OpenAIResponseFormat(BaseModel):
    """OpenAI response format specification for JSON mode."""
    type: str = "json_object"


class OpenAIMessage(BaseModel):
    """OpenAI message structure."""
    role: str
    content: str
    reasoning: Optional[str] = None  # For o1 models


class OpenAIRequest(BaseModel):
    """OpenAI API request structure."""
    model: str
    messages: List[OpenAIMessage]
    stream: bool = False
    max_tokens: Optional[int] = None
    max_completion_tokens: Optional[int] = None  # For reasoning models
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    n: Optional[int] = None
    stop: Optional[Union[str, List[str]]] = None
    presence_penalty: Optional[float] = None
    frequency_penalty: Optional[float] = None
    logit_bias: Optional[Dict[str, float]] = None
    user: Optional[str] = None
    response_format: Optional[OpenAIResponseFormat] = None
    seed: Optional[int] = None
    reasoning_effort: Optional[str] = None  # "low", "medium", "high" for reasoning models
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None
    tools: Optional[List[Dict[str, Any]]] = None


class OpenAIUsage(BaseModel):
    """OpenAI token usage information."""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    completion_tokens_details: Optional[Dict[str, Any]] = None
    prompt_tokens_details: Optional[Dict[str, Any]] = None


class OpenAIChoice(BaseModel):
    """OpenAI response choice."""
    index: int
    message: OpenAIMessage
    finish_reason: Optional[str] = None
    reasoning: Optional[str] = None  # Alternative location for reasoning content


class OpenAIResponse(BaseModel):
    """OpenAI API non-streaming response structure."""
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[OpenAIChoice]
    usage: Optional[OpenAIUsage] = None
    system_fingerprint: Optional[str] = None


class OpenAIDelta(BaseModel):
    """OpenAI streaming response delta."""
    role: Optional[str] = None
    content: Optional[str] = None
    reasoning: Optional[str] = None


class OpenAIStreamChoice(BaseModel):
    """OpenAI streaming response choice."""
    index: int
    delta: Optional[OpenAIDelta] = None
    message: Optional[OpenAIMessage] = None  # Some APIs send 'message' in final chunk
    finish_reason: Optional[str] = None


class OpenAIStreamChunk(BaseModel):
    """OpenAI API streaming response chunk."""
    id: str
    object: str = "chat.completion.chunk"
    created: int
    model: str
    choices: List[OpenAIStreamChoice]
    usage: Optional[OpenAIUsage] = None
    system_fingerprint: Optional[str] = None


class OpenAIModelPermission(BaseModel):
    """OpenAI model permission information."""
    id: str
    object: str = "model_permission"
    created: int
    allow_create_engine: bool
    allow_sampling: bool
    allow_logprobs: bool
    allow_search_indices: bool
    allow_view: bool
    allow_fine_tuning: bool
    organization: str
    group: Optional[str] = None
    is_blocking: bool = False


class OpenAIModelInfo(BaseModel):
    """OpenAI model information structure."""
    id: str
    object: str = "model"
    created: Optional[int] = 0  # Optional for local APIs like LMStudio
    owned_by: str
    permission: Optional[List[OpenAIModelPermission]] = None
    root: Optional[str] = None
    parent: Optional[str] = None


class OpenAIModelsResponse(BaseModel):
    """OpenAI models list response structure."""
    object: str = "list"
    data: List[OpenAIModelInfo]


class OpenAIErrorDetail(BaseModel):
    """OpenAI API error detail."""
    message: str
    type: str
    param: Optional[str] = None
    code: Optional[str] = None


class OpenAIErrorResponse(BaseModel):
    """OpenAI API error response."""
    error: OpenAIErrorDetail