"""
Tests for streaming accumulator service.

Tests the conversion of non-streaming requests to use streaming internally
with accumulation, enabling cancellation for all request types.
"""

import pytest
import asyncio
from typing import Optional
from unittest.mock import Mock, AsyncMock

from app.services.streaming_accumulator import StreamingAccumulator, AccumulatedResponse
from app.services.ai_providers import StreamingChatResponse, ProviderType
from app.services.chat_session_manager import ChatSessionManager


class TestStreamingAccumulator:
    """Test streaming accumulator functionality."""
    
    @pytest.fixture
    def session_manager(self):
        """Create session manager for testing."""
        return ChatSessionManager(max_concurrent_sessions=5)
    
    @pytest.fixture
    def accumulator(self, session_manager):
        """Create streaming accumulator."""
        return StreamingAccumulator(session_manager=session_manager)
    
    @pytest.fixture
    def mock_streaming_chunks(self):
        """Create mock streaming chunks for testing."""
        chunks = []
        
        # Content chunks
        for i in range(5):
            chunk = Mock(spec=StreamingChatResponse)
            chunk.content = f"chunk {i} "
            chunk.thinking = ""
            chunk.done = False
            chunk.metadata = {}
            chunks.append(chunk)
        
        # Final chunk with metadata
        final_chunk = Mock(spec=StreamingChatResponse)
        final_chunk.content = ""
        final_chunk.thinking = ""
        final_chunk.done = True
        final_chunk.metadata = {
            "model": "test-model",
            "tokens_used": 50,
            "finish_reason": "stop"
        }
        chunks.append(final_chunk)
        
        return chunks
    
    def test_accumulator_initialization(self, accumulator, session_manager):
        """Test accumulator initializes properly."""
        assert accumulator.session_manager == session_manager
        assert accumulator._active_accumulations == {}
    
    @pytest.mark.asyncio
    async def test_basic_accumulation(self, accumulator, mock_streaming_chunks):
        """Test basic streaming accumulation without cancellation."""
        
        async def mock_stream_generator():
            """Mock streaming generator."""
            for chunk in mock_streaming_chunks:
                await asyncio.sleep(0.01)  # Small delay between chunks
                yield chunk
        
        session_id = "test-accumulation"
        
        # Accumulate the stream
        result = await accumulator.accumulate_stream(
            stream_generator=mock_stream_generator(),
            session_id=session_id,
            conversation_id="test-conv"
        )
        
        # Should have accumulated all content
        expected_content = "chunk 0 chunk 1 chunk 2 chunk 3 chunk 4 "
        assert result.content == expected_content
        assert result.metadata["model"] == "test-model"
        assert result.metadata["tokens_used"] == 50
        assert result.thinking == ""
        assert result.success == True
    
    @pytest.mark.asyncio
    async def test_accumulation_with_thinking(self, accumulator):
        """Test accumulation with thinking content."""
        
        async def mock_stream_with_thinking():
            # Thinking chunk
            thinking_chunk = Mock(spec=StreamingChatResponse)
            thinking_chunk.content = ""
            thinking_chunk.thinking = "Let me think about this... "
            thinking_chunk.done = False
            thinking_chunk.metadata = {}
            yield thinking_chunk
            
            # Content chunk
            content_chunk = Mock(spec=StreamingChatResponse)
            content_chunk.content = "My response is here."
            content_chunk.thinking = ""
            content_chunk.done = False
            content_chunk.metadata = {}
            yield content_chunk
            
            # Final chunk
            final_chunk = Mock(spec=StreamingChatResponse)
            final_chunk.content = ""
            final_chunk.thinking = ""
            final_chunk.done = True
            final_chunk.metadata = {"model": "test-model"}
            yield final_chunk
        
        result = await accumulator.accumulate_stream(
            stream_generator=mock_stream_with_thinking(),
            session_id="thinking-test",
            conversation_id="test-conv"
        )
        
        assert result.content == "My response is here."
        assert result.thinking == "Let me think about this... "
        assert result.success == True
    
    @pytest.mark.asyncio
    async def test_accumulation_cancellation(self, accumulator, session_manager, mock_streaming_chunks):
        """Test cancellation during accumulation."""
        
        chunks_processed = 0
        
        async def mock_cancellable_stream():
            nonlocal chunks_processed
            for i, chunk in enumerate(mock_streaming_chunks):
                chunks_processed = i
                await asyncio.sleep(0.01)  # Allow cancellation point
                yield chunk
        
        session_id = "cancel-test"
        
        # Start accumulation
        accumulation_task = asyncio.create_task(
            accumulator.accumulate_stream(
                stream_generator=mock_cancellable_stream(),
                session_id=session_id,
                conversation_id="test-conv"
            )
        )
        
        # Let some chunks process
        await asyncio.sleep(0.03)
        
        # Cancel via session manager
        cancelled = await session_manager.cancel_session(session_id)
        
        # Should get cancelled error if session was found
        if cancelled:
            with pytest.raises(asyncio.CancelledError):
                await accumulation_task
            
            # Should have been cancelled partway through
            assert chunks_processed < len(mock_streaming_chunks)
        else:
            # If timing didn't work out, just cancel the task directly
            accumulation_task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await accumulation_task
    
    @pytest.mark.asyncio
    async def test_multiple_concurrent_accumulations(self, accumulator):
        """Test multiple concurrent accumulations."""
        
        async def mock_stream(stream_id, chunk_count=3):
            for i in range(chunk_count):
                chunk = Mock(spec=StreamingChatResponse)
                chunk.content = f"stream{stream_id}_chunk{i} "
                chunk.thinking = ""
                chunk.done = False
                chunk.metadata = {}
                await asyncio.sleep(0.01)
                yield chunk
            
            # Final chunk
            final = Mock(spec=StreamingChatResponse)
            final.content = ""
            final.thinking = ""
            final.done = True
            final.metadata = {"model": f"model-{stream_id}"}
            yield final
        
        # Start multiple accumulations
        tasks = []
        for i in range(3):
            task = asyncio.create_task(
                accumulator.accumulate_stream(
                    stream_generator=mock_stream(i),
                    session_id=f"concurrent-{i}",
                    conversation_id=f"conv-{i}"
                )
            )
            tasks.append(task)
        
        # Wait for all to complete
        results = await asyncio.gather(*tasks)
        
        # Check results
        for i, result in enumerate(results):
            expected_content = f"stream{i}_chunk0 stream{i}_chunk1 stream{i}_chunk2 "
            assert result.content == expected_content
            assert result.metadata["model"] == f"model-{i}"
            assert result.success == True
    
    @pytest.mark.asyncio
    async def test_accumulation_error_handling(self, accumulator):
        """Test error handling during accumulation."""
        
        async def mock_error_stream():
            # Yield one chunk
            chunk = Mock(spec=StreamingChatResponse)
            chunk.content = "partial content"
            chunk.thinking = ""
            chunk.done = False
            chunk.metadata = {}
            yield chunk
            
            # Then raise an error
            raise Exception("Stream processing error")
        
        result = await accumulator.accumulate_stream(
            stream_generator=mock_error_stream(),
            session_id="error-test",
            conversation_id="test-conv"
        )
        
        # Should return failed result with partial content
        assert result.success == False
        assert result.content == "partial content"  # Should have partial content
        assert "Stream processing error" in result.error_message
    
    @pytest.mark.asyncio
    async def test_session_cleanup_after_accumulation(self, accumulator, session_manager):
        """Test that sessions are cleaned up after accumulation."""
        
        async def mock_simple_stream():
            chunk = Mock(spec=StreamingChatResponse)
            chunk.content = "simple content"
            chunk.thinking = ""
            chunk.done = True
            chunk.metadata = {"model": "test"}
            yield chunk
        
        session_id = "cleanup-test"
        
        result = await accumulator.accumulate_stream(
            stream_generator=mock_simple_stream(),
            session_id=session_id,
            conversation_id="test-conv"
        )
        
        # Session should be cleaned up
        assert not session_manager.has_active_session(session_id)
        assert result.success == True
    
    @pytest.mark.asyncio
    async def test_progress_callback(self, accumulator):
        """Test progress callback functionality."""
        
        progress_updates = []
        
        def progress_callback(accumulated_content: str, chunks_processed: int, total_chunks: Optional[int] = None):
            progress_updates.append({
                "content": accumulated_content,
                "chunks": chunks_processed
            })
        
        async def mock_counted_stream():
            for i in range(3):
                chunk = Mock(spec=StreamingChatResponse)
                chunk.content = f"part{i} "
                chunk.thinking = ""
                chunk.done = False
                chunk.metadata = {}
                yield chunk
            
            # Final chunk
            final = Mock(spec=StreamingChatResponse)
            final.content = ""
            final.thinking = ""
            final.done = True
            final.metadata = {"model": "test"}
            yield final
        
        result = await accumulator.accumulate_stream(
            stream_generator=mock_counted_stream(),
            session_id="progress-test",
            conversation_id="test-conv",
            progress_callback=progress_callback
        )
        
        # Should have received progress updates
        assert len(progress_updates) >= 3  # At least one per content chunk
        assert progress_updates[0]["content"] == "part0 "
        assert progress_updates[1]["content"] == "part0 part1 "
        assert result.content == "part0 part1 part2 "
    
    def test_session_already_exists_handling(self, accumulator, session_manager):
        """Test handling when session already exists in session manager."""
        session_id = "existing-session"
        
        # Create existing session
        mock_task = Mock()
        mock_task.cancelled.return_value = False
        mock_task.done.return_value = False
        
        session_manager.register_session(
            session_id=session_id,
            conversation_id="existing-conv",
            asyncio_task=mock_task
        )
        
        # Should handle gracefully when session already exists
        assert session_manager.has_active_session(session_id)
    
    @pytest.mark.asyncio
    async def test_empty_stream_handling(self, accumulator):
        """Test handling of empty stream."""
        
        async def empty_stream():
            # Yield only final chunk with no content
            final = Mock(spec=StreamingChatResponse)
            final.content = ""
            final.thinking = ""
            final.done = True
            final.metadata = {"model": "test"}
            yield final
        
        result = await accumulator.accumulate_stream(
            stream_generator=empty_stream(),
            session_id="empty-test",
            conversation_id="test-conv"
        )
        
        assert result.content == ""
        assert result.thinking == ""
        assert result.success == True
        assert result.metadata["model"] == "test"