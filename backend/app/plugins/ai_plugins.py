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
from app.services.ollama_service import OllamaService
from app.services.openai_service import OpenAIService

logger = logging.getLogger(__name__)


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
    model = settings.get("model", "gpt-3.5-turbo")
    base_url = settings.get("base_url", "https://api.openai.com/v1")
    
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
        
        # Create chat request
        chat_request = ChatRequest(
            message=user_message,
            provider_type=provider_type,
            provider_settings=provider_settings,
            chat_controls=chat_controls,
            system_prompt=""  # No system prompt for generation tasks
        )
        
        logger.debug(f"AI generation: {provider} - {instructions[:30]}...")
        
        # Use synchronous wrapper to call AI provider
        result = _run_async_ai_call(provider, chat_request)
        
        return result
        
    except Exception as e:
        logger.error(f"Error in generate(): {e}")
        return f"Error generating response: {str(e)}"


@plugin_registry.register("reflect")
def reflect(*args, _script_context=None, **kwargs) -> str:
    """
    Self-reflective AI processing with flexible signature support and safety mechanisms.
    
    This function enables AI personas to reflect on their own thoughts and actions,
    creating self-modifying behavior while preventing infinite loops through
    comprehensive safety checks.
    
    Supported signatures:
        ctx.reflect('instructions')
        ctx.reflect('instructions', 'input_data')
        ctx.reflect('provider_name', 'model_id', 'instructions')
        ctx.reflect('provider_name', 'model_id', 'instructions', 'input_data')
    
    Safety features:
    - Maximum reflection depth limiting (3 levels)
    - Direct module recursion prevention  
    - Timing-based restrictions (no nested BEFORE timing)
    - Audit trail for debugging and self-awareness
    
    Args:
        *args: Variable arguments matching one of the supported signatures
        _script_context: Script execution context (auto-injected)
        **kwargs: Keyword arguments for fine-tuning (temperature, max_tokens, etc.)
        
    Returns:
        AI-generated reflection response or error message if reflection is blocked
        
    Examples:
        # Self-assessment after AI response (most common use case)
        quality = ctx.reflect("Rate my last response quality 1-10 and suggest improvements")
        
        # Adaptive behavior based on conversation context
        tone = ctx.reflect("What communication style would work best here?", recent_messages)
        
        # Cross-module reflection for complex reasoning
        analysis = ctx.reflect("openai", "gpt-4", "Analyze this conversation pattern", chat_history)
        
        # With additional parameters for creative reflection
        creative_idea = ctx.reflect("Generate a creative solution", temperature=0.8, max_tokens=300)
        
        # Concise reflection for simple assessments
        quick_rating = ctx.reflect("Rate this 1-10", max_tokens=20)
    """
    try:
        # Import ExecutionTiming for safety checks
        from app.models import ExecutionTiming
        
        # Safety check - verify script context is available
        if not _script_context:
            logger.error("reflect() called without script context - safety mechanisms unavailable")
            return "Error: Reflection requires script context for safety mechanisms"
        
        # Parse arguments based on signature (same as generate())
        if len(args) == 0:
            logger.error("reflect() called with no arguments")
            return "Error: No reflection instructions provided"
        
        elif len(args) == 1:
            # ctx.reflect('instructions')
            instructions = args[0]
            input_text = None
            provider = None
            model = None
            
        elif len(args) == 2:
            # ctx.reflect('instructions', 'input_data')
            instructions = args[0]
            input_text = args[1]
            provider = None
            model = None
            
        elif len(args) == 3:
            # ctx.reflect('provider_name', 'model_id', 'instructions')
            provider = args[0]
            model = args[1]
            instructions = args[2]
            input_text = None
            
        elif len(args) == 4:
            # ctx.reflect('provider_name', 'model_id', 'instructions', 'input_data')
            provider = args[0]
            model = args[1]
            instructions = args[2]
            input_text = args[3]
            
        else:
            logger.error(f"reflect() called with invalid number of arguments: {len(args)}")
            return "Error: Invalid number of arguments for reflection"
        
        # Validate required parameters
        if not instructions or not instructions.strip():
            logger.error("reflect() called with empty instructions")
            return "Error: Reflection instructions cannot be empty"
        
        # CRITICAL SAFETY CHECK: Verify reflection is allowed
        # We need to determine the current module and timing, but for now use a default approach
        current_module_id = getattr(_script_context, 'current_module_id', 'unknown_module')
        current_timing = getattr(_script_context, 'current_timing', ExecutionTiming.AFTER)
        
        if not _script_context.can_reflect(current_module_id, current_timing):
            blocked_msg = f"Reflection blocked for safety: current depth {_script_context.reflection_depth}, module stack: {_script_context.module_resolution_stack}"
            return blocked_msg
        
        # Enter reflection mode for tracking
        _script_context.enter_reflection(current_module_id, instructions[:100])  # Truncated for logging
        
        try:
            # Get provider and model settings (same logic as generate())
            if not provider and hasattr(_script_context, 'current_provider'):
                provider = _script_context.current_provider or "ollama"
            else:
                provider = provider or "ollama"
            
            # Normalize provider
            provider = provider.lower()
            if provider not in ["ollama", "openai"]:
                logger.error(f"Unsupported provider for reflection: {provider}")
                return f"Error: Unsupported provider '{provider}' for reflection"
            
            provider_type = ProviderType.OLLAMA if provider == "ollama" else ProviderType.OPENAI
            
            # Get provider settings from current session context
            provider_settings = {}
            if hasattr(_script_context, 'current_provider_settings') and _script_context.current_provider_settings:
                try:
                    provider_settings = _script_context.current_provider_settings.copy()
                except (AttributeError, TypeError):
                    provider_settings = {}
            
            # Override model if explicitly provided
            if model and provider_settings:
                provider_settings["model"] = model
            
            # If no provider settings available, we can't make AI calls
            if not provider_settings:
                return "Error: No provider settings available from current chat session for reflection"
            
            # Get chat controls from session or use defaults
            chat_controls = {}
            if hasattr(_script_context, 'current_chat_controls') and _script_context.current_chat_controls:
                try:
                    chat_controls = _script_context.current_chat_controls.copy()
                except (AttributeError, TypeError):
                    chat_controls = {}
            
            # Set defaults for missing chat controls (more conservative for reflection)
            chat_controls.setdefault("temperature", 0.2)  # Lower temperature for more focused reflection
            chat_controls.setdefault("max_tokens", 150)   # Shorter default for concise reflections
            chat_controls.setdefault("stream", False)     # Always non-streaming for scripts
            
            # Apply keyword arguments to chat controls (can override defaults)
            chat_controls.update(kwargs)
            
            # Build the reflection prompt
            if input_text and input_text.strip():
                user_message = f"""Reflect on the following:

Instructions: {instructions}

Context/Input:
{input_text}

Please provide thoughtful self-reflection."""
            else:
                user_message = f"""Reflect on the following:

{instructions}

Please provide thoughtful self-reflection."""
            
            # Create chat request with a minimal system prompt to avoid recursion
            # Use a simple, non-module-based system prompt for reflection
            reflection_system_prompt = "You are an AI engaged in self-reflection. Provide honest, insightful analysis of your thoughts and responses."
            
            chat_request = ChatRequest(
                message=user_message,
                provider_type=provider_type,
                provider_settings=provider_settings,
                chat_controls=chat_controls,
                system_prompt=reflection_system_prompt  # Simple system prompt to avoid module recursion
            )
            
            # Use synchronous wrapper to call AI provider (same as generate())
            result = _run_async_ai_call(provider, chat_request)
            
            return result
            
        finally:
            # Always exit reflection mode to maintain proper depth tracking
            _script_context.exit_reflection()
            
    except Exception as e:
        logger.error(f"Error in reflect(): {e}")
        return f"Error during reflection: {str(e)}"