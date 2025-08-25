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
    Run an async AI call, handling both sync and async contexts.
    
    Args:
        provider: Provider type ("ollama" or "openai")
        chat_request: The chat request to process
        
    Returns:
        AI response content
    """
    try:
        # Check if we're in an async context
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're in an async context - run AI call in separate thread
                
                # Create a thread to run the async call
                def run_in_thread():
                    # Create new event loop in thread
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(_async_ai_call(provider, chat_request))
                    finally:
                        new_loop.close()
                
                # Run in thread and wait for result
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_in_thread)
                    result = future.result(timeout=30)  # 30 second timeout
                    return result
            else:
                # Loop exists but not running
                return loop.run_until_complete(_async_ai_call(provider, chat_request))
        except RuntimeError:
            # No event loop exists, create one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(_async_ai_call(provider, chat_request))
                return result
            finally:
                loop.close()
                asyncio.set_event_loop(None)
                
    except Exception as e:
        logger.error(f"Error in sync AI call: {e}")
        return f"Error processing with AI: {str(e)}"


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
        
        logger.info(f"Generating with {provider}: instructions='{instructions[:50]}...', input_length={len(input_text) if input_text else 0}")
        
        # Use synchronous wrapper to call AI provider
        result = _run_async_ai_call(provider, chat_request)
        
        return result
        
    except Exception as e:
        logger.error(f"Error in generate(): {e}")
        return f"Error generating response: {str(e)}"