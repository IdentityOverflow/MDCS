"""
Tests for enhanced AI providers with session management and cancellation support.
"""

import pytest
import asyncio
import uuid
from unittest.mock import Mock, AsyncMock, patch

from app.services.ai_providers import ChatRequest, ProviderType, ProviderFactory
from app.services.ollama_service_with_cancellation import OllamaServiceWithCancellation
from app.services.openai_service_with_cancellation import OpenAIServiceWithCancellation
from app.services.chat_session_manager import ChatSessionManager


class TestEnhancedProviders:
    """Test enhanced AI providers with session management."""
    
    @pytest.fixture
    def session_manager(self):
        """Create session manager for testing."""
        return ChatSessionManager(max_concurrent_sessions=5)
    
    @pytest.fixture
    def ollama_request(self):
        """Basic Ollama request for testing."""
        return ChatRequest(
            message="Test message",
            provider_type=ProviderType.OLLAMA,
            provider_settings={
                "host": "http://localhost:11434",
                "model": "llama3.2"
            },
            chat_controls={"stream": False},
            system_prompt=""
        )
    
    @pytest.fixture
    def openai_request(self):
        """Basic OpenAI request for testing."""
        return ChatRequest(
            message="Test message",
            provider_type=ProviderType.OPENAI,
            provider_settings={
                "base_url": "https://api.openai.com/v1",
                "api_key": "test-key",
                "default_model": "gpt-4"
            },
            chat_controls={"stream": False},
            system_prompt=""
        )
    
    def test_enhanced_ollama_service_creation(self, session_manager):
        """Test creating enhanced Ollama service with session manager."""
        service = OllamaServiceWithCancellation(session_manager=session_manager)
        
        assert service.session_manager == session_manager
        assert service._current_session_id is None
        
        # Test setting session ID
        session_id = "test-session-123"
        service.set_session_id(session_id)
        assert service._current_session_id == session_id
    
    def test_enhanced_openai_service_creation(self, session_manager):
        """Test creating enhanced OpenAI service with session manager."""
        service = OpenAIServiceWithCancellation(session_manager=session_manager)
        
        assert service.session_manager == session_manager
        assert service._current_session_id is None
        
        # Test setting session ID
        session_id = "test-session-456"
        service.set_session_id(session_id)
        assert service._current_session_id == session_id
    
    def test_provider_factory_enhanced_creation(self):
        """Test creating enhanced providers via factory."""
        # Test Ollama enhanced provider
        ollama_enhanced = ProviderFactory.create_provider(
            ProviderType.OLLAMA, 
            with_cancellation=True
        )
        assert isinstance(ollama_enhanced, OllamaServiceWithCancellation)
        
        # Test OpenAI enhanced provider
        openai_enhanced = ProviderFactory.create_provider(
            ProviderType.OPENAI,
            with_cancellation=True
        )
        assert isinstance(openai_enhanced, OpenAIServiceWithCancellation)
        
        # Test standard providers (backward compatibility)
        from app.services.ollama_service import OllamaService
        from app.services.openai_service import OpenAIService
        
        ollama_standard = ProviderFactory.create_provider(
            ProviderType.OLLAMA,
            with_cancellation=False
        )
        assert isinstance(ollama_standard, OllamaService)
        assert not isinstance(ollama_standard, OllamaServiceWithCancellation)
    
    @pytest.mark.asyncio
    async def test_session_registration_and_cleanup(self, session_manager, ollama_request):
        """Test that enhanced providers register and clean up sessions properly."""
        service = OllamaServiceWithCancellation(session_manager=session_manager)
        session_id = "test-cleanup-session"
        conversation_id = "test-conversation"
        
        # Mock the base service method to simulate a quick response
        async def mock_send_message(request):
            await asyncio.sleep(0.01)  # Brief delay
            return Mock(content="Mock response", model="llama3.2")
        
        with patch.object(service.__class__.__bases__[0], 'send_message', side_effect=mock_send_message):
            # Before request: no active sessions
            assert session_manager.get_active_session_count() == 0
            
            # Execute request with session
            response = await service.send_message_with_session(
                ollama_request,
                session_id=session_id,
                conversation_id=conversation_id
            )
            
            # After request: session should be cleaned up
            assert session_manager.get_active_session_count() == 0
            assert not session_manager.has_active_session(session_id)
    
    @pytest.mark.asyncio
    async def test_session_cancellation_propagation(self, session_manager, ollama_request):
        """Test that session cancellation properly propagates to provider tasks."""
        service = OllamaServiceWithCancellation(session_manager=session_manager)
        session_id = "test-cancel-session"
        
        # Mock a long-running operation that can be cancelled
        async def mock_long_operation(request):
            await asyncio.sleep(0.1)  # Long enough to be cancelled
            return Mock(content="Should not reach here", model="llama3.2")
        
        with patch.object(service.__class__.__bases__[0], 'send_message', side_effect=mock_long_operation):
            # Start the request in a task
            request_task = asyncio.create_task(
                service.send_message_with_session(
                    ollama_request,
                    session_id=session_id,
                    conversation_id="test-conv"
                )
            )
            
            # Let it register with session manager
            await asyncio.sleep(0.02)
            
            # Verify session is registered
            assert session_manager.has_active_session(session_id)
            
            # Cancel via session manager
            cancelled = await session_manager.cancel_session(session_id)
            assert cancelled == True
            
            # The request task should be cancelled
            with pytest.raises(asyncio.CancelledError):
                await request_task
    
    @pytest.mark.asyncio
    async def test_streaming_session_management(self, session_manager, ollama_request):
        """Test session management for streaming requests."""
        service = OllamaServiceWithCancellation(session_manager=session_manager)
        session_id = "test-stream-session"
        
        # Make it a streaming request
        ollama_request.chat_controls["stream"] = True
        
        # Mock streaming response
        async def mock_stream_response(request):
            for i in range(5):
                await asyncio.sleep(0.01)  # Allow cancellation points
                yield Mock(content=f"chunk {i}", done=(i == 4))
        
        with patch.object(service.__class__.__bases__[0], 'send_message_stream', side_effect=mock_stream_response):
            chunks_received = 0
            
            try:
                async for chunk in service.send_message_stream_with_session(
                    ollama_request,
                    session_id=session_id,
                    conversation_id="stream-conv"
                ):
                    chunks_received += 1
                    if chunks_received == 3:
                        # Cancel mid-stream via session manager
                        await session_manager.cancel_session(session_id)
                        
            except asyncio.CancelledError:
                # Expected when cancelled
                pass
            
            # Should have received some chunks before cancellation
            assert chunks_received >= 1
            assert chunks_received < 5  # Should not complete all chunks
    
    @pytest.mark.asyncio
    async def test_error_handling_with_session_cleanup(self, session_manager, ollama_request):
        """Test that sessions are cleaned up properly even when errors occur."""
        service = OllamaServiceWithCancellation(session_manager=session_manager)
        session_id = "test-error-session"
        
        # Mock an operation that raises an error
        async def mock_error_operation(request):
            await asyncio.sleep(0.01)
            raise Exception("Simulated provider error")
        
        with patch.object(service.__class__.__bases__[0], 'send_message', side_effect=mock_error_operation):
            with pytest.raises(Exception, match="Simulated provider error"):
                await service.send_message_with_session(
                    ollama_request,
                    session_id=session_id,
                    conversation_id="error-conv"
                )
            
            # Session should still be cleaned up after error
            assert not session_manager.has_active_session(session_id)
    
    @pytest.mark.asyncio
    async def test_backward_compatibility_methods(self, session_manager, ollama_request):
        """Test that backward compatibility methods work with session management."""
        service = OllamaServiceWithCancellation(session_manager=session_manager)
        
        # Set a session ID
        test_session_id = "backward-compat-test"
        service.set_session_id(test_session_id)
        
        # Mock the base method
        async def mock_response(request):
            await asyncio.sleep(0.01)
            return Mock(content="Backward compatible response", model="llama3.2")
        
        with patch.object(service.__class__.__bases__[0], 'send_message', side_effect=mock_response):
            # Call the backward compatibility method (no explicit session management)
            response = await service.send_message(ollama_request)
            
            # Should still work and clean up session
            assert response is not None
            assert not session_manager.has_active_session(test_session_id)
    
    @pytest.mark.asyncio
    async def test_concurrent_sessions_limit_enforcement(self, ollama_request):
        """Test that session manager enforces concurrent session limits."""
        # Create session manager with low limit
        limited_manager = ChatSessionManager(max_concurrent_sessions=2)
        service = OllamaServiceWithCancellation(session_manager=limited_manager)
        
        # Mock long-running operations
        async def mock_long_operation(request):
            await asyncio.sleep(0.1)
            return Mock(content="response", model="llama3.2")
        
        with patch.object(service.__class__.__bases__[0], 'send_message', side_effect=mock_long_operation):
            # Start maximum allowed concurrent sessions
            tasks = []
            for i in range(2):
                task = asyncio.create_task(
                    service.send_message_with_session(
                        ollama_request,
                        session_id=f"concurrent-{i}",
                        conversation_id=f"conv-{i}"
                    )
                )
                tasks.append(task)
            
            # Let them register
            await asyncio.sleep(0.02)
            
            # Try to exceed limit - should raise RuntimeError
            with pytest.raises(RuntimeError, match="Maximum concurrent sessions"):
                await service.send_message_with_session(
                    ollama_request,
                    session_id="exceeds-limit",
                    conversation_id="excess-conv"
                )
            
            # Cancel all tasks for cleanup
            for task in tasks:
                task.cancel()
                
            # Wait for cancellation to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Verify at least some tasks were cancelled
            cancelled_count = sum(1 for result in results if isinstance(result, asyncio.CancelledError))
            assert cancelled_count > 0