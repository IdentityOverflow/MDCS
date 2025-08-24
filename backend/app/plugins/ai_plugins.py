"""
AI text processing plugin functions for advanced modules.

Provides AI-powered text processing capabilities including summarization,
analysis, transformation, and other AI-based text operations.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Union
from sqlalchemy.orm import Session

from app.core.script_plugins import plugin_registry
from app.services.ai_providers import ChatRequest, ProviderType
from app.services.ollama_service import OllamaService
from app.services.openai_service import OpenAIService

logger = logging.getLogger(__name__)


class SyncAIProcessor:
    """
    Synchronous wrapper for async AI providers.
    
    Handles the async/sync bridge for plugin functions that need to call
    AI providers from within synchronous script execution context.
    """
    
    @staticmethod
    def run_async_ai_call(provider: str, chat_request: ChatRequest) -> str:
        """
        Run an async AI call synchronously.
        
        Args:
            provider: Provider type ("ollama" or "openai")
            chat_request: The chat request to process
            
        Returns:
            AI response content
        """
        try:
            # Get or create event loop
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # We're in an async context, but need to run sync
                    # This is a complex case - for now, return a placeholder
                    logger.warning("Attempted to run AI call from within async context - not supported yet")
                    return "[AI Processing temporarily unavailable in async context]"
                else:
                    # Loop exists but not running
                    return loop.run_until_complete(SyncAIProcessor._async_ai_call(provider, chat_request))
            except RuntimeError:
                # No event loop exists, create one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(SyncAIProcessor._async_ai_call(provider, chat_request))
                    return result
                finally:
                    loop.close()
                    asyncio.set_event_loop(None)
                    
        except Exception as e:
            logger.error(f"Error in sync AI call: {e}")
            return f"Error processing with AI: {str(e)}"
    
    @staticmethod
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


@plugin_registry.register("ai_process_text")
def ai_process_text(
    text: str,
    instruction: str,
    provider: str = "ollama",
    model: Optional[str] = None,
    provider_settings: Optional[Dict[str, Any]] = None,
    temperature: float = 0.1,
    max_tokens: int = 1000,
    db_session: Session = None
) -> str:
    """
    Process text using AI with custom instructions.
    
    Args:
        text: The text to process
        instruction: Instructions for how to process the text (e.g., "Summarize this", "Extract key points")
        provider: AI provider to use ("ollama" or "openai", default: "ollama")
        model: Specific model to use (optional, uses provider default if not specified)
        provider_settings: Provider connection settings (optional, uses defaults if not provided)
        temperature: AI temperature setting (0.0-1.0, default: 0.1 for consistent results)
        max_tokens: Maximum tokens in response (default: 1000)
        db_session: Database session (auto-injected)
        
    Returns:
        Processed text result from AI
        
    Example:
        summary = ctx.ai_process_text(
            "Long article text here...", 
            "Summarize this article in 3 bullet points"
        )
        
        key_points = ctx.ai_process_text(
            conversation_text,
            "Extract the main topics discussed",
            temperature=0.3
        )
        
        analysis = ctx.ai_process_text(
            user_message,
            "Analyze the sentiment and extract any questions",
            provider="openai",
            model="gpt-4"
        )
    """
    try:
        # Validate inputs
        if not text or not text.strip():
            logger.warning("ai_process_text called with empty text")
            return ""
            
        if not instruction or not instruction.strip():
            logger.warning("ai_process_text called with empty instruction")
            return text
            
        # Normalize provider type
        provider = provider.lower()
        if provider not in ["ollama", "openai"]:
            logger.error(f"Unsupported provider: {provider}")
            return f"Error: Unsupported provider '{provider}'"
            
        provider_type = ProviderType.OLLAMA if provider == "ollama" else ProviderType.OPENAI
        
        # Set up default provider settings if none provided
        if provider_settings is None:
            if provider == "ollama":
                provider_settings = {
                    "host": "http://localhost:11434",
                    "model": model or "llama3.2:3b"  # Default to smaller, faster model
                }
            else:  # openai
                provider_settings = {
                    "api_key": "required",  # This should be provided by the user
                    "model": model or "gpt-3.5-turbo"
                }
        elif model:
            # Override model if explicitly provided
            provider_settings = dict(provider_settings)
            provider_settings["model"] = model
            
        # Build the processing prompt
        system_prompt = f"""You are a text processing assistant. Follow the user's instructions exactly and provide only the requested output without additional commentary or formatting unless specifically requested.

Instructions: {instruction}"""
        
        user_message = f"""Please process the following text according to the instructions:

{text}"""
        
        # Create chat request
        chat_request = ChatRequest(
            message=user_message,
            provider_type=provider_type,
            provider_settings=provider_settings,
            chat_controls={
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": False  # Always use non-streaming for script processing
            },
            system_prompt=system_prompt
        )
        
        logger.info(f"Processing text with {provider}: instruction='{instruction[:50]}...', text_length={len(text)}")
        
        # Use synchronous wrapper to call AI provider
        result = SyncAIProcessor.run_async_ai_call(provider, chat_request)
        
        return result
        
    except Exception as e:
        logger.error(f"Error in ai_process_text: {e}")
        return f"Error processing text: {str(e)}"


@plugin_registry.register("ai_summarize")
def ai_summarize(
    text: str,
    max_sentences: int = 3,
    provider: str = "ollama",
    model: Optional[str] = None,
    provider_settings: Optional[Dict[str, Any]] = None,
    db_session: Session = None
) -> str:
    """
    Summarize text using AI in a specified number of sentences.
    
    Args:
        text: Text to summarize
        max_sentences: Maximum number of sentences in summary (default: 3)
        provider: AI provider to use ("ollama" or "openai", default: "ollama")
        model: Specific model to use (optional)
        provider_settings: Provider connection settings (optional)
        db_session: Database session (auto-injected)
        
    Returns:
        AI-generated summary
        
    Example:
        summary = ctx.ai_summarize(long_conversation, max_sentences=2)
        brief = ctx.ai_summarize(article_text, max_sentences=1, provider="openai")
    """
    instruction = f"Summarize this text in exactly {max_sentences} sentence{'s' if max_sentences != 1 else ''}. Be concise and capture the main points."
    
    return ai_process_text(
        text=text,
        instruction=instruction,
        provider=provider,
        model=model,
        provider_settings=provider_settings,
        temperature=0.1,
        max_tokens=500,
        db_session=db_session
    )


@plugin_registry.register("ai_extract_topics")
def ai_extract_topics(
    text: str,
    max_topics: int = 5,
    provider: str = "ollama",
    model: Optional[str] = None,
    provider_settings: Optional[Dict[str, Any]] = None,
    db_session: Session = None
) -> str:
    """
    Extract main topics from text using AI.
    
    Args:
        text: Text to analyze for topics
        max_topics: Maximum number of topics to extract (default: 5)
        provider: AI provider to use ("ollama" or "openai", default: "ollama")
        model: Specific model to use (optional)
        provider_settings: Provider connection settings (optional)
        db_session: Database session (auto-injected)
        
    Returns:
        List of main topics as a formatted string
        
    Example:
        topics = ctx.ai_extract_topics(conversation_history)
        main_themes = ctx.ai_extract_topics(document_text, max_topics=3)
    """
    instruction = f"Extract the {max_topics} most important topics or themes from this text. Return them as a numbered list with brief descriptions."
    
    return ai_process_text(
        text=text,
        instruction=instruction,
        provider=provider,
        model=model,
        provider_settings=provider_settings,
        temperature=0.2,
        max_tokens=400,
        db_session=db_session
    )


@plugin_registry.register("ai_analyze_sentiment")
def ai_analyze_sentiment(
    text: str,
    provider: str = "ollama",
    model: Optional[str] = None,
    provider_settings: Optional[Dict[str, Any]] = None,
    db_session: Session = None
) -> str:
    """
    Analyze the sentiment and emotional tone of text using AI.
    
    Args:
        text: Text to analyze
        provider: AI provider to use ("ollama" or "openai", default: "ollama")
        model: Specific model to use (optional)
        provider_settings: Provider connection settings (optional)
        db_session: Database session (auto-injected)
        
    Returns:
        Sentiment analysis result
        
    Example:
        sentiment = ctx.ai_analyze_sentiment(user_message)
        mood = ctx.ai_analyze_sentiment(conversation_text)
    """
    instruction = "Analyze the sentiment and emotional tone of this text. Provide a brief assessment including overall sentiment (positive/negative/neutral) and key emotional indicators."
    
    return ai_process_text(
        text=text,
        instruction=instruction,
        provider=provider,
        model=model,
        provider_settings=provider_settings,
        temperature=0.1,
        max_tokens=200,
        db_session=db_session
    )


@plugin_registry.register("ai_extract_questions")
def ai_extract_questions(
    text: str,
    provider: str = "ollama",
    model: Optional[str] = None,
    provider_settings: Optional[Dict[str, Any]] = None,
    db_session: Session = None
) -> str:
    """
    Extract questions and requests from text using AI.
    
    Args:
        text: Text to analyze for questions
        provider: AI provider to use ("ollama" or "openai", default: "ollama")
        model: Specific model to use (optional)
        provider_settings: Provider connection settings (optional)
        db_session: Database session (auto-injected)
        
    Returns:
        List of extracted questions and requests
        
    Example:
        questions = ctx.ai_extract_questions(user_messages)
        requests = ctx.ai_extract_questions(conversation_history)
    """
    instruction = "Extract all questions, requests, and action items from this text. List them clearly, one per line."
    
    return ai_process_text(
        text=text,
        instruction=instruction,
        provider=provider,
        model=model,
        provider_settings=provider_settings,
        temperature=0.1,
        max_tokens=300,
        db_session=db_session
    )