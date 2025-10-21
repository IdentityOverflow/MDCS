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


def _run_cancellable_ai_call(provider: str, chat_request: ChatRequest, cancellation_token=None) -> str:
    """
    Run an AI call with full cancellation support using CancellationToken.

    This converts non-streaming requests to streaming internally for cancellation support.

    Args:
        provider: Provider type ("ollama" or "openai")
        chat_request: The chat request to process
        cancellation_token: CancellationToken for cancellation tracking

    Returns:
        AI response content

    Raises:
        asyncio.CancelledError: If the operation is cancelled
    """
    if not cancellation_token:
        # No cancellation token - fall back to regular synchronous call
        return _run_async_ai_call(provider, chat_request)

    # Check if we're already in an async context or need to run one
    try:
        import asyncio
        from ..services.streaming_accumulator import StreamingAccumulator

        async def _async_cancellable_wrapper():
            try:
                # Initialize appropriate service
                if provider == "ollama":
                    from ..services.providers.ollama.service import OllamaService
                    service = OllamaService()
                else:
                    from ..services.providers.openai.service import OpenAIService
                    service = OpenAIService()

                # Validate provider settings
                if not service.validate_settings(chat_request.provider_settings):
                    raise ValueError(f"Invalid provider settings for {provider}")

                # Force streaming mode for cancellation support
                chat_request.chat_controls["stream"] = True
                logger.info(f"AI module streaming request - provider_settings: {chat_request.provider_settings}")
                logger.info(f"AI module streaming request - chat_controls: {chat_request.chat_controls}")

                # Get streaming response with cancellation token
                stream = service.send_message_stream(chat_request, cancellation_token=cancellation_token)

                # Use StreamingAccumulator with aggressive cancellation checking for modules
                # Check every chunk (interval=1) for responsive cancellation in plugins
                accumulator = StreamingAccumulator(cancellation_check_interval=1)
                result = await accumulator.accumulate_stream(
                    stream,
                    cancellation_token=cancellation_token
                )
                return result.content
            except asyncio.CancelledError:
                logger.info(f"AI plugin call cancelled for session {cancellation_token.session_id}")
                raise
            except Exception as e:
                logger.error(f"Error in cancellable AI call: {e}")
                raise
        
        # Try to run in current event loop or create new one
        try:
            loop = asyncio.get_running_loop()
            # We're in an async context BUT the event loop is blocked by sync code
            # So we can't use run_coroutine_threadsafe (would deadlock)
            # Instead, run in a separate thread with its own event loop
            pass

        except RuntimeError:
            # No event loop running - we're in pure sync context
            pass

        # Always run in a separate thread to avoid blocking
        import concurrent.futures
        import time
        import threading

        # Create a threading event for cross-thread cancellation signaling
        cancel_event = threading.Event()

        def run_with_cancel_check():
            """Wrapper that runs async code and periodically checks for cancellation."""
            async def _wrapper_with_cancel():
                # Create task for the AI call
                task = asyncio.create_task(_async_cancellable_wrapper())

                # Poll for cancellation in parallel with the AI call
                while not task.done():
                    # Check if outer thread signaled cancellation
                    if cancel_event.is_set():
                        logger.warning(f"🛑 Inner thread detected cancel signal, cancelling task")
                        task.cancel()
                        try:
                            await task
                        except asyncio.CancelledError:
                            raise

                    # Short sleep to avoid busy-waiting
                    await asyncio.sleep(0.01)  # Check every 10ms

                # Return result
                return await task

            return asyncio.run(_wrapper_with_cancel())

        with concurrent.futures.ThreadPoolExecutor() as executor:
            # Run async code in separate thread with its own event loop
            future = executor.submit(run_with_cancel_check)

            # Poll for cancellation while waiting for result
            start_time = time.time()
            poll_count = 0
            while not future.done():
                poll_count += 1

                # Check for cancellation every poll
                if cancellation_token:
                    is_cancelled = cancellation_token.is_cancelled()
                    if is_cancelled:
                        elapsed = time.time() - start_time
                        import datetime
                        timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
                        logger.warning(f"🛑 [{timestamp}] CANCELLATION DETECTED in plugin after {poll_count} polls ({elapsed:.2f}s) for session {cancellation_token.session_id}")
                        print(f"🛑 [{timestamp}] CANCELLATION DETECTED - State: {cancellation_token._state}")
                        # Signal the inner thread to cancel
                        cancel_event.set()
                        # Wait a bit for the inner thread to respond
                        time.sleep(0.1)
                        # Now raise the cancellation error
                        raise asyncio.CancelledError(f"Session {cancellation_token.session_id} cancelled")

                # Wait for a short period with timeout
                try:
                    result = future.result(timeout=0.01)  # Poll every 10ms for faster cancellation detection
                    elapsed = time.time() - start_time
                    logger.debug(f"Plugin AI call completed after {poll_count} polls ({elapsed:.2f}s)")
                    return result
                except concurrent.futures.TimeoutError:
                    # Check for overall timeout (30 seconds)
                    if time.time() - start_time > 30:
                        logger.error("Plugin AI call timed out after 30 seconds")
                        raise TimeoutError("AI call timed out after 30 seconds")
                    continue

            return future.result()
            
    except Exception as e:
        logger.error(f"Error setting up cancellable AI call: {e}")
        # Fall back to regular synchronous call
        return _run_async_ai_call(provider, chat_request)


def _sync_ollama_call(chat_request: ChatRequest) -> str:
    """Make a synchronous HTTP call to Ollama."""
    import requests
    import json
    
    # Extract settings
    settings = chat_request.provider_settings
    host = settings.get("host", "http://localhost:11434")
    model = settings.get("model")
    
    if not model:
        raise ValueError("No model specified in provider settings - cannot make AI call")
    
    # Build request
    messages = []
    if chat_request.system_prompt:
        messages.append({"role": "system", "content": chat_request.system_prompt})
    messages.append({"role": "user", "content": chat_request.message})
    
    payload = {
        "model": model,
        "messages": messages,
        "stream": chat_request.chat_controls.get("stream", False),
        "options": {
            "temperature": chat_request.chat_controls.get("temperature", 0.1),
            "num_predict": chat_request.chat_controls.get("max_tokens", 1000)
        }
    }
    
    # Make request
    url = f"{host.rstrip('/')}/api/chat"
    response = requests.post(url, json=payload, timeout=30)
    response.raise_for_status()
    
    # Parse JSON response - handle both single JSON and streaming format
    try:
        result = response.json()
        return result.get("message", {}).get("content", "")
    except json.JSONDecodeError as e:
        # Response might be in streaming format (multiple JSON objects)
        response_text = response.text.strip()
        
        # Try to extract content from streaming JSON response
        try:
            import re
            # Look for the last "content" field in streaming response
            content_matches = re.findall(r'"content"\s*:\s*"([^"]*)"', response_text)
            if content_matches:
                # Join all content parts (streaming responses split content)
                return "".join(content_matches)
        except:
            pass
        
        # Try to parse the last complete JSON object
        try:
            lines = response_text.split('\n')
            for line in reversed(lines):
                if line.strip() and line.strip().startswith('{'):
                    last_json = json.loads(line.strip())
                    content = last_json.get("message", {}).get("content", "")
                    if content:
                        return content
        except:
            pass
        
        logger.error(f"Ollama JSON parsing failed: {e}")
        logger.error(f"Response content (first 200 chars): {response_text[:200]}")
        return f"Response parsing error: {str(e)}"


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


async def _generate_async(
    provider: str,
    chat_request: ChatRequest,
    cancellation_token: Optional['CancellationToken'] = None
) -> str:
    """
    Generate AI response asynchronously with cancellation support.

    This is the core async implementation that enables immediate cancellation
    by checking the token during every chunk of streaming.

    Args:
        provider: Provider type ("ollama" or "openai")
        chat_request: The chat request to process
        cancellation_token: Optional cancellation token for immediate cancellation

    Returns:
        AI response content

    Raises:
        asyncio.CancelledError: If cancellation is detected
    """
    # Check cancellation before starting
    if cancellation_token:
        cancellation_token.check_cancelled()

    logger.debug(f"Async AI generation starting: {provider}")

    try:
        # Initialize appropriate service
        if provider == "ollama":
            from ..services.providers.ollama.service import OllamaService
            service = OllamaService()
        else:
            from ..services.providers.openai.service import OpenAIService
            service = OpenAIService()

        # Validate provider settings
        if not service.validate_settings(chat_request.provider_settings):
            raise ValueError(f"Invalid provider settings for {provider}")

        # Force streaming mode for cancellation support
        chat_request.chat_controls["stream"] = True

        # Stream with cancellation checks
        accumulated_content = ""
        chunk_count = 0

        logger.debug(f"Starting AI stream for plugin call")

        async for chunk in service.send_message_stream(chat_request, cancellation_token=cancellation_token):
            # Check cancellation every chunk (immediate detection)
            if cancellation_token:
                cancellation_token.check_cancelled()

            if chunk.content:
                accumulated_content += chunk.content

            chunk_count += 1

            # Log progress periodically
            if chunk_count % 20 == 0:
                logger.debug(f"Plugin AI call: {chunk_count} chunks processed")

        logger.info(f"AI generation completed: {len(accumulated_content)} characters, {chunk_count} chunks")
        return accumulated_content

    except asyncio.CancelledError:
        logger.info(f"AI generation cancelled after processing")
        raise

    except Exception as e:
        logger.error(f"Error in async AI generation: {e}")
        raise


async def _async_ai_call(provider: str, chat_request: ChatRequest) -> str:
    """
    Internal async method to make the actual AI call (non-streaming version).

    DEPRECATED: Use _generate_async() for better cancellation support.

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
        
        # Force streaming mode for cancellation support
        chat_controls["stream"] = True
        logger.info(f"AI module streaming request - provider_settings: {provider_settings}")
        logger.info(f"AI module streaming request - chat_controls: {chat_controls}")
        
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

        # Get cancellation token for cancellation support
        cancellation_token = None
        if _script_context and hasattr(_script_context, 'cancellation_token'):
            cancellation_token = getattr(_script_context, 'cancellation_token', None)

        logger.debug(f"Generate: has_token={cancellation_token is not None}")

        # Use cancellable AI call if cancellation token is available
        # This function properly handles thread-based cancellation
        if cancellation_token:
            logger.debug(f"Using cancellable generate() call for session {cancellation_token.session_id}")
            result = _run_cancellable_ai_call(provider, chat_request, cancellation_token)
        else:
            logger.debug("No cancellation token available, using synchronous generate() call")
            result = _run_async_ai_call(provider, chat_request)

        logger.info(f"Generate result: {len(str(result))} characters")

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
            
            # Force streaming mode for cancellation support
            chat_controls["stream"] = True
            logger.info(f"AI reflection streaming request - provider_settings: {provider_settings}")
            logger.info(f"AI reflection streaming request - chat_controls: {chat_controls}")
            
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
            
            # Get cancellation token for cancellation support
            cancellation_token = None
            if hasattr(_script_context, 'cancellation_token'):
                cancellation_token = getattr(_script_context, 'cancellation_token', None)

            # Use cancellable AI call if cancellation token is available, otherwise fall back to sync
            if cancellation_token:
                logger.debug(f"Using cancellable reflection call for session {cancellation_token.session_id}")
                result = _run_cancellable_ai_call(provider, chat_request, cancellation_token)
            else:
                logger.debug("No cancellation token available, using synchronous reflection call")
                result = _run_async_ai_call(provider, chat_request)
            
            return result
            
        finally:
            # Always exit reflection mode to maintain proper depth tracking
            _script_context.exit_reflection()
            
    except Exception as e:
        logger.error(f"Error in reflect(): {e}")
        return f"Error during reflection: {str(e)}"