"""
Ollama-specific request and response models.
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel


class OllamaOptions(BaseModel):
    """Ollama-specific generation options."""
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    num_predict: Optional[int] = None  # Ollama's equivalent to max_tokens
    repeat_penalty: Optional[float] = None
    seed: Optional[int] = None
    stop: Optional[List[str]] = None
    tfs_z: Optional[float] = None
    num_thread: Optional[int] = None
    num_ctx: Optional[int] = None
    num_batch: Optional[int] = None
    num_gqa: Optional[int] = None
    num_gpu: Optional[int] = None
    main_gpu: Optional[int] = None
    low_vram: Optional[bool] = None
    f16_kv: Optional[bool] = None
    logits_all: Optional[bool] = None
    vocab_only: Optional[bool] = None
    use_mmap: Optional[bool] = None
    use_mlock: Optional[bool] = None
    embedding_only: Optional[bool] = None
    rope_frequency_base: Optional[float] = None
    rope_frequency_scale: Optional[float] = None
    num_keep: Optional[int] = None
    typical_p: Optional[float] = None
    presence_penalty: Optional[float] = None
    frequency_penalty: Optional[float] = None
    mirostat: Optional[int] = None
    mirostat_tau: Optional[float] = None
    mirostat_eta: Optional[float] = None
    penalize_newline: Optional[bool] = None
    numa: Optional[bool] = None


class OllamaRequest(BaseModel):
    """Ollama API request structure."""
    model: str
    messages: List[Dict[str, str]]
    stream: bool = False
    format: Optional[str] = None
    options: Optional[Dict[str, Any]] = None
    keep_alive: Optional[str] = None
    think: Optional[bool] = None  # Ollama thinking mode


class OllamaResponse(BaseModel):
    """Ollama API non-streaming response structure."""
    model: str
    created_at: str
    message: Dict[str, str]
    done: bool
    total_duration: Optional[int] = None
    load_duration: Optional[int] = None
    prompt_eval_count: Optional[int] = None
    prompt_eval_duration: Optional[int] = None
    eval_count: Optional[int] = None
    eval_duration: Optional[int] = None


class OllamaStreamChunk(BaseModel):
    """Ollama API streaming response chunk."""
    model: str
    created_at: str
    message: Optional[Dict[str, str]] = None
    done: bool
    total_duration: Optional[int] = None
    load_duration: Optional[int] = None
    prompt_eval_count: Optional[int] = None
    prompt_eval_duration: Optional[int] = None
    eval_count: Optional[int] = None
    eval_duration: Optional[int] = None


class OllamaModelInfo(BaseModel):
    """Ollama model information structure."""
    name: str
    size: Optional[int] = None
    digest: Optional[str] = None
    modified_at: Optional[str] = None
    
    
class OllamaModelsResponse(BaseModel):
    """Ollama models list response structure."""
    models: List[OllamaModelInfo]