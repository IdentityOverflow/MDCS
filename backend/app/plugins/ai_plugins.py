"""
AI generation plugin functions for advanced modules.

Provides clean AI generation capabilities with flexible signature support
and automatic integration with current chat session provider/model settings.
"""

import asyncio
import concurrent.futures
import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.core.script_plugins import plugin_registry
from app.services.ai_providers import ChatRequest, ProviderType
from app.services.providers.ollama import OllamaService
from app.services.providers.openai import OpenAIService

logger = logging.getLogger(__name__)


def _get_state_aware_system_prompt(script_context) -> Optional[str]:
    """
    Get state-aware system prompt for AI reflection based on SystemPromptState.
    
    Args:
        script_context: Script execution context with potential state access
        
    Returns:
        State-aware system prompt or None if state is not available
    """
    try:
        # Check if context has state-aware methods (loose coupling check)
        if not hasattr(script_context, 'get_system_prompt_state') or not hasattr(script_context, 'get_current_execution_stage'):
            return None
        
        # Get SystemPromptState
        prompt_state = script_context.get_system_prompt_state()
        if not prompt_state:
            return None
        
        # Get current execution stage
        current_stage = script_context.get_current_execution_stage()
        if not current_stage:
            return None
        
        # Get stage-appropriate system prompt
        stage_prompt = prompt_state.get_prompt_for_stage(current_stage)
        
        # Ensure we return a valid string (not Mock or None)
        if isinstance(stage_prompt, str) and stage_prompt.strip():
            return stage_prompt
        else:
            return None
        
    except Exception as e:
        # Any exception in state access should fall back gracefully
        logger.debug(f"Could not get state-aware system prompt: {e}")
        return None


def _run_async_ai_call(provider: str, chat_request: ChatRequest) -> str:
    """
    Run an async AI call using a simple synchronous HTTP approach.
    
    This bypasses all the async/threading complexity by making direct HTTP calls.
    
    Args:
        provider: Provider type ("ollama" or "openai")
        chat_request: The chat request to process
        
    Returns:
        AI response content
    """
    try:
        if provider == "ollama":
            return _sync_ollama_call(chat_request)
        else:
            return _sync_openai_call(chat_request)
    except Exception as e:
        logger.error(f"Error in sync AI call: {e}")
        return f"Error processing with AI: {str(e)}"


def _sync_ollama_call(chat_request: ChatRequest) -> str:
    """Make a synchronous HTTP call to Ollama."""
    import requests
    import json
    
    # Extract settings
    settings = chat_request.provider_settings
    host = settings.get("host", "http://localhost:11434")
    model = settings.get("model", "tinydolphin")
    
    # Build request
    messages = []
    if chat_request.system_prompt:
        messages.append({"role": "system", "content": chat_request.system_prompt})
    messages.append({"role": "user", "content": chat_request.message})
    
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": chat_request.chat_controls.get("temperature", 0.1),
            "num_predict": chat_request.chat_controls.get("max_tokens", 1000)
        }
    }
    
    # Make request
    url = f"{host.rstrip('/')}/api/chat"
    response = requests.post(url, json=payload, timeout=30)
    response.raise_for_status()
    
    result = response.json()
    return result.get("message", {}).get("content", "")


def _sync_openai_call(chat_request: ChatRequest) -> str:
    """Make a synchronous HTTP call to OpenAI."""
    import requests
    import json
    
    # Extract settings
    settings = chat_request.provider_settings
    api_key = settings.get("api_key", "")
    model = settings.get("model", "liquid/lfm2-1.2b")
    base_url = settings.get("base_url", "http://127.0.0.1:1234/v1")
    
    # Build request
    messages = []
    if chat_request.system_prompt:
        messages.append({"role": "system", "content": chat_request.system_prompt})
    messages.append({"role": "user", "content": chat_request.message})
    
    payload = {
        "model": model,
        "messages": messages,
        "temperature": chat_request.chat_controls.get("temperature", 0.1),
        "max_tokens": chat_request.chat_controls.get("max_tokens", 1000)
    }
    
    # Make request
    headers = {"Authorization": f"Bearer {api_key}"}
    url = f"{base_url.rstrip('/')}/chat/completions"
    response = requests.post(url, json=payload, headers=headers, timeout=30)
    response.raise_for_status()
    
    result = response.json()
    return result.get("choices", [{}])[0].get("message", {}).get("content", "")


async def _async_ai_call(provider: str, chat_request: ChatRequest) -> str:
    """
    Internal async method to make the actual AI call.
    
    Args:
        provider: Provider type ("ollama" or "openai")
        chat_request: The chat request to process
        
    Returns:
        AI response content
    """
    try:
        # Initialize appropriate service
        if provider == "ollama":
            service = OllamaService()
        else:
            service = OpenAIService()
            
        # Validate provider settings
        if not service.validate_settings(chat_request.provider_settings):
            raise ValueError(f"Invalid provider settings for {provider}")
        
        # Send request and get response
        response = await service.send_message(chat_request)
        
        logger.info(f"AI processing completed: {len(response.content)} characters generated")
        return response.content
        
    except Exception as e:
        logger.error(f"Error in async AI call: {e}")
        raise


@plugin_registry.register("generate")
def generate(*args, _script_context=None, **kwargs) -> str:
    """
    Generate AI responses with flexible signature support.
    
    Supported signatures:
        ctx.generate('Instructions')
        ctx.generate('Instructions', 'input_text')
        ctx.generate('provider_name', 'model_id', 'instructions')
        ctx.generate('provider_name', 'model_id', 'instructions', 'input_text')
    
    The function automatically uses the current chat session's provider and model
    if not explicitly specified, allowing easy AI generation within advanced modules.
    
    Args:
        *args: Variable arguments matching one of the supported signatures
        _script_context: Script execution context (auto-injected)
        **kwargs: Keyword arguments for fine-tuning (temperature, max_tokens, etc.)
        
    Returns:
        AI-generated response text
        
    Examples:
        # Use current session provider/model with simple instruction
        response = ctx.generate("Summarize the key points")
        
        # Use current session provider/model with instruction and input
        summary = ctx.generate("Summarize this text", long_text)
        
        # Use specific provider/model with instruction
        quick_response = ctx.generate("ollama", "llama3.2:3b", "Generate a short response")
        
        # Use specific provider/model with instruction and input
        analysis = ctx.generate("openai", "gpt-4", "Analyze this conversation", chat_history)
        
        # With additional parameters
        creative_response = ctx.generate("Write a creative story", temperature=0.8, max_tokens=500)
    """
    try:
        # Parse arguments based on signature
        if len(args) == 0:
            logger.error("generate() called with no arguments")
            return "Error: No instructions provided"
        
        elif len(args) == 1:
            # ctx.generate('Instructions')
            instructions = args[0]
            input_text = None
            provider = None
            model = None
            
        elif len(args) == 2:
            # ctx.generate('Instructions', 'input_text')
            instructions = args[0]
            input_text = args[1]
            provider = None
            model = None
            
        elif len(args) == 3:
            # ctx.generate('provider_name', 'model_id', 'instructions')
            provider = args[0]
            model = args[1] 
            instructions = args[2]
            input_text = None
            
        elif len(args) == 4:
            # ctx.generate('provider_name', 'model_id', 'instructions', 'input_text')
            provider = args[0]
            model = args[1]
            instructions = args[2]
            input_text = args[3]
            
        else:
            logger.error(f"generate() called with invalid number of arguments: {len(args)}")
            return "Error: Invalid number of arguments"
        
        # Validate required parameters
        if not instructions or not instructions.strip():
            logger.error("generate() called with empty instructions")
            return "Error: Instructions cannot be empty"
        
        # Get current session context or use defaults
        if not provider and _script_context and hasattr(_script_context, 'current_provider'):
            provider = _script_context.current_provider or "ollama"
        else:
            provider = provider or "ollama"
        
        # Normalize provider
        provider = provider.lower()
        if provider not in ["ollama", "openai"]:
            logger.error(f"Unsupported provider: {provider}")
            return f"Error: Unsupported provider '{provider}'"
        
        provider_type = ProviderType.OLLAMA if provider == "ollama" else ProviderType.OPENAI
        
        # Get provider settings from current session context
        if _script_context and hasattr(_script_context, 'current_provider_settings'):
            provider_settings = _script_context.current_provider_settings.copy()
        else:
            provider_settings = {}
        
        # Override model if explicitly provided
        if model and provider_settings:
            provider_settings["model"] = model
        
        # If no provider settings available, we can't make AI calls
        if not provider_settings:
            return "Error: No provider settings available from current chat session"
        
        # Get chat controls from session or use defaults
        if _script_context and hasattr(_script_context, 'current_chat_controls'):
            chat_controls = _script_context.current_chat_controls.copy()
        else:
            chat_controls = {}
        
        # Apply keyword arguments to chat controls
        chat_controls.update(kwargs)
        
        # Set defaults for missing chat controls
        chat_controls.setdefault("temperature", 0.1)  # Lower for consistency
        chat_controls.setdefault("max_tokens", 1000)
        chat_controls.setdefault("stream", False)  # Always non-streaming for scripts
        
        # Build the generation prompt
        if input_text and input_text.strip():
            user_message = f"""{instructions}

Input:
{input_text}"""
        else:
            user_message = instructions
        
        # Get state-aware system prompt if available, otherwise use empty prompt
        generation_system_prompt = _get_state_aware_system_prompt(_script_context) or ""
        
        # Create chat request
        chat_request = ChatRequest(
            message=user_message,
            provider_type=provider_type,
            provider_settings=provider_settings,
            chat_controls=chat_controls,
            system_prompt=generation_system_prompt  # Use state-aware prompt if available
        )
        
        logger.debug(f"AI generation: {provider} - {instructions[:30]}...")
        
        # Use synchronous wrapper to call AI provider
        result = _run_async_ai_call(provider, chat_request)
        
        return result
        
    except Exception as e:
        logger.error(f"Error in generate(): {e}")
        return f"Error generating response: {str(e)}"


@plugin_registry.register("reflect")
def reflect(instructions: str, _script_context=None, **kwargs) -> str:
    """
    Self-reflective AI processing using the current state-aware system prompt.
    
    This function enables AI personas to reflect on their own thoughts and actions,
    using the fully resolved system prompt from the current execution stage.
    Includes comprehensive safety mechanisms to prevent infinite loops.
    
    Safety features:
    - Maximum reflection depth limiting (3 levels)
    - Direct module recursion prevention  
    - Execution context restrictions (no nested IMMEDIATE)
    - Audit trail for debugging and self-awareness
    
    Args:
        instructions: Reflection instructions from the script (mandatory)
        _script_context: Script execution context (auto-injected)
        **kwargs: Chat control overrides (temperature, max_tokens, etc.)
        
    Returns:
        AI-generated reflection response or error message if reflection is blocked
        
    Examples:
        # Self-assessment using current system prompt
        quality = ctx.reflect("Rate my last response quality 1-10 and suggest improvements")
        
        # Adaptive behavior analysis
        tone = ctx.reflect("What communication style would work best for this user?")
        
        # Creative reflection with custom parameters
        creative_idea = ctx.reflect("Generate a creative solution approach", temperature=0.8, max_tokens=300)
    """
    try:
        # Safety check - verify script context is available
        if not _script_context:
            logger.error("reflect() called without script context - safety mechanisms unavailable")
            return "Error: Reflection requires script context for safety mechanisms"
        
        # Validate instructions
        if not instructions or not isinstance(instructions, str) or not instructions.strip():
            logger.error("reflect() called with invalid instructions")
            return "Error: Reflection instructions must be a non-empty string"
        
        # CRITICAL SAFETY CHECK: Verify reflection is allowed
        current_module_id = getattr(_script_context, 'current_module_id', 'unknown_module')
        current_timing = getattr(_script_context, 'current_timing', "POST_RESPONSE")
        
        if not _script_context.can_reflect(current_module_id, current_timing):
            blocked_msg = f"Reflection blocked for safety: current depth {_script_context.reflection_depth}, module stack: {_script_context.module_resolution_stack}"
            return blocked_msg
        
        # Enter reflection mode for tracking
        _script_context.enter_reflection(current_module_id, instructions[:100])  # Truncated for logging
        
        try:
            # Get provider settings from current session context
            if not hasattr(_script_context, 'current_provider') or not hasattr(_script_context, 'current_provider_settings'):
                return "Error: No provider settings available from current chat session for reflection"
            
            provider = _script_context.current_provider or "ollama"
            provider_settings = _script_context.current_provider_settings or {}
            
            if not provider_settings:
                return "Error: No provider settings available from current chat session for reflection"
            
            # Normalize provider
            provider = provider.lower()
            if provider not in ["ollama", "openai"]:
                logger.error(f"Unsupported provider for reflection: {provider}")
                return f"Error: Unsupported provider '{provider}' for reflection"
            
            provider_type = ProviderType.OLLAMA if provider == "ollama" else ProviderType.OPENAI
            
            # Get chat controls from session and apply overrides
            chat_controls = {}
            if hasattr(_script_context, 'current_chat_controls') and _script_context.current_chat_controls:
                chat_controls = _script_context.current_chat_controls.copy()
            
            # Set reasonable defaults for reflection
            chat_controls.setdefault("temperature", 0.3)  # Moderate temperature for balanced reflection
            chat_controls.setdefault("max_tokens", 200)   # Reasonable default for reflections
            chat_controls.setdefault("stream", False)     # Always non-streaming for scripts
            
            # Apply keyword arguments to override defaults
            chat_controls.update(kwargs)
            
            # Get state-aware system prompt or use current context
            system_prompt = _get_state_aware_system_prompt(_script_context)
            
            # If no state-aware prompt available, reflection should fail gracefully
            # This maintains the principle that reflect() uses the actual system prompt state
            if not system_prompt:
                logger.warning("No state-aware system prompt available for reflection")
                return "Error: No system prompt state available for reflection"
            
            # Create chat request with state-aware system prompt
            chat_request = ChatRequest(
                message=instructions,  # Use instructions directly as the user message
                provider_type=provider_type,
                provider_settings=provider_settings,
                chat_controls=chat_controls,
                system_prompt=system_prompt
            )
            
            # Use synchronous wrapper to call AI provider
            result = _run_async_ai_call(provider, chat_request)
            
            return result
            
        finally:
            # Always exit reflection mode to maintain proper depth tracking
            _script_context.exit_reflection()
            
    except Exception as e:
        logger.error(f"Error in reflect(): {e}")
        return f"Error during reflection: {str(e)}"