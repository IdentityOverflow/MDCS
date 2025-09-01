"""
Integration tests for provider cancellation with ChatSessionManager.

Tests the integration between providers and the chat session manager
to ensure proper cancellation behavior.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from app.services.ai_providers import ChatRequest, ProviderType
from app.services.ollama_service import OllamaService
from app.services.openai_service import OpenAIService
from app.services.chat_session_manager import ChatSessionManager, ChatCancellationToken


class TestProviderSessionIntegration:
    """Test integration between providers and session manager."""
    
    @pytest.fixture
    def session_manager(self):
        """Create session manager for testing."""
        return ChatSessionManager(max_concurrent_sessions=5)
    
    @pytest.fixture
    def ollama_request(self):
        """Basic Ollama request."""
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
    
    @pytest.mark.asyncio
    async def test_session_manager_provider_lifecycle(self, session_manager, ollama_request):
        """Test complete lifecycle of session management with provider."""
        
        async def mock_provider_operation():
            """Mock long-running provider operation."""
            await asyncio.sleep(0.1)
            return {"status": "completed"}
        
        # Create a task for the provider operation
        provider_task = asyncio.create_task(mock_provider_operation())
        
        # Register with session manager
        session_id = "test-session-001"
        token = session_manager.register_session(
            session_id=session_id,
            conversation_id="conv-123",
            asyncio_task=provider_task,
            current_stage=1
        )
        
        assert session_manager.has_active_session(session_id)
        assert token.is_active()
        
        # Cancel via session manager
        cancelled = await session_manager.cancel_session(session_id)
        assert cancelled == True
        assert token.is_cancelled()
        
        # Provider task should be cancelled
        with pytest.raises(asyncio.CancelledError):
            await provider_task
    
    @pytest.mark.asyncio
    async def test_multiple_sessions_concurrent_cancellation(self, session_manager):
        """Test cancelling multiple concurrent sessions."""
        
        async def long_operation(delay):
            await asyncio.sleep(delay)
            return f"completed after {delay}s"
        
        # Create multiple sessions
        sessions = []
        for i in range(3):
            task = asyncio.create_task(long_operation(0.1 + i * 0.05))
            session_id = f"session-{i}"
            
            token = session_manager.register_session(
                session_id=session_id,
                conversation_id=f"conv-{i}",
                asyncio_task=task,
                current_stage=i + 1
            )
            sessions.append((session_id, task, token))
        
        assert session_manager.get_active_session_count() == 3
        
        # Cancel all sessions
        cancelled_count = await session_manager.cancel_all_sessions()
        assert cancelled_count == 3
        
        # All tasks should be cancelled
        for session_id, task, token in sessions:
            assert token.is_cancelled()
            with pytest.raises(asyncio.CancelledError):
                await task
    
    @pytest.mark.asyncio
    async def test_session_cleanup_after_completion(self, session_manager):
        """Test automatic cleanup of completed sessions."""
        
        async def quick_operation():
            await asyncio.sleep(0.02)
            return "done"
        
        async def cancelled_operation():
            await asyncio.sleep(0.1)
            return "should not complete"
        
        # Create completed task
        completed_task = asyncio.create_task(quick_operation())
        session_manager.register_session("completed", "conv1", completed_task)
        
        # Create cancelled task
        cancelled_task = asyncio.create_task(cancelled_operation())
        cancelled_token = session_manager.register_session("cancelled", "conv2", cancelled_task)
        cancelled_task.cancel()
        
        # Wait for completion
        await asyncio.sleep(0.05)
        
        assert session_manager.get_active_session_count() == 2
        
        # Cleanup completed sessions
        cleaned_count = await session_manager.cleanup_completed_sessions()
        assert cleaned_count == 2
        assert session_manager.get_active_session_count() == 0
    
    @pytest.mark.asyncio
    async def test_session_stage_tracking(self, session_manager):
        """Test tracking execution stages in session manager."""
        
        async def staged_operation():
            # Simulate multi-stage processing
            for stage in [1, 2, 3, 4, 5]:
                session_manager.update_session_stage("staged", stage)
                await asyncio.sleep(0.01)
            return "all stages completed"
        
        task = asyncio.create_task(staged_operation())
        token = session_manager.register_session(
            session_id="staged",
            conversation_id="conv",
            asyncio_task=task,
            current_stage=1
        )
        
        # Let some stages complete
        await asyncio.sleep(0.03)
        
        # Check stage was updated
        assert token.current_stage > 1  # Should have progressed
        
        # Cancel mid-execution
        await session_manager.cancel_session("staged")
        
        # Task should be cancelled
        with pytest.raises(asyncio.CancelledError):
            await task
    
    @pytest.mark.asyncio
    async def test_session_conversation_filtering(self, session_manager):
        """Test filtering sessions by conversation ID."""
        
        async def mock_task():
            await asyncio.sleep(0.1)
            return "done"
        
        # Create sessions for different conversations
        conv1_sessions = []
        conv2_sessions = []
        
        for i in range(2):
            # Conversation 1 sessions
            task1 = asyncio.create_task(mock_task())
            session_manager.register_session(f"conv1-session-{i}", "conv-1", task1)
            conv1_sessions.append(task1)
            
            # Conversation 2 sessions  
            task2 = asyncio.create_task(mock_task())
            session_manager.register_session(f"conv2-session-{i}", "conv-2", task2)
            conv2_sessions.append(task2)
        
        # Check filtering
        conv1_active = session_manager.get_sessions_by_conversation("conv-1")
        conv2_active = session_manager.get_sessions_by_conversation("conv-2")
        
        assert len(conv1_active) == 2
        assert len(conv2_active) == 2
        assert all(s.conversation_id == "conv-1" for s in conv1_active)
        assert all(s.conversation_id == "conv-2" for s in conv2_active)
        
        # Cancel all sessions
        await session_manager.cancel_all_sessions()


class TestProviderCancellationIntegrationSimple:
    """Simple integration tests to verify cancellation works end-to-end."""
    
    @pytest.mark.asyncio
    async def test_basic_task_cancellation(self):
        """Test basic asyncio task cancellation behavior."""
        
        async def cancellable_operation():
            try:
                await asyncio.sleep(0.1)
                return "completed"
            except asyncio.CancelledError:
                # Re-raise to properly handle cancellation
                raise
        
        task = asyncio.create_task(cancellable_operation())
        
        # Let it start
        await asyncio.sleep(0.05)
        
        # Cancel
        task.cancel()
        
        # Should propagate CancelledError
        with pytest.raises(asyncio.CancelledError):
            await task
        
        # Verify task state
        assert task.cancelled()
        assert task.done()
    
    @pytest.mark.asyncio
    async def test_nested_cancellation_propagation(self):
        """Test that cancellation propagates through nested calls."""
        
        async def inner_operation():
            await asyncio.sleep(0.1)
            return "inner done"
        
        async def outer_operation():
            try:
                result = await inner_operation()
                return f"outer: {result}"
            except asyncio.CancelledError:
                # Should propagate cancellation
                raise
        
        task = asyncio.create_task(outer_operation())
        await asyncio.sleep(0.05)
        task.cancel()
        
        with pytest.raises(asyncio.CancelledError):
            await task
    
    @pytest.mark.asyncio
    async def test_generator_cancellation(self):
        """Test cancellation of async generators (for streaming)."""
        
        async def stream_generator():
            for i in range(10):
                await asyncio.sleep(0.01)  # Cancellation point
                yield f"chunk-{i}"
        
        async def consume_stream():
            chunks = []
            async for chunk in stream_generator():
                chunks.append(chunk)
            return chunks
        
        task = asyncio.create_task(consume_stream())
        
        # Let some chunks process
        await asyncio.sleep(0.03)
        
        # Cancel
        task.cancel()
        
        with pytest.raises(asyncio.CancelledError):
            await task


class TestProviderWithSessionManagerMethods:
    """Test methods that providers will use to integrate with session manager."""
    
    def test_session_manager_as_dependency(self):
        """Test session manager can be used as dependency."""
        from app.services.chat_session_manager import get_chat_session_manager
        
        manager = get_chat_session_manager()
        assert isinstance(manager, ChatSessionManager)
        assert manager.max_concurrent_sessions == 10  # Default value
    
    @pytest.mark.asyncio 
    async def test_session_manager_max_concurrent_limit(self):
        """Test session manager enforces concurrent limits."""
        manager = ChatSessionManager(max_concurrent_sessions=2)
        
        async def mock_task():
            await asyncio.sleep(0.1)
            return "done"
        
        # Register up to limit
        task1 = asyncio.create_task(mock_task())
        task2 = asyncio.create_task(mock_task())
        
        manager.register_session("session1", "conv1", task1)
        manager.register_session("session2", "conv2", task2)
        
        # Try to exceed limit
        task3 = asyncio.create_task(mock_task())
        with pytest.raises(RuntimeError, match="Maximum concurrent sessions"):
            manager.register_session("session3", "conv3", task3)
        
        # Cleanup
        await manager.cancel_all_sessions()
        task3.cancel()
        
        with pytest.raises(asyncio.CancelledError):
            await task3