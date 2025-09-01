"""
Integration tests for chat API cancellation functionality.

Tests the end-to-end cancellation behavior without complex API mocking.
"""

import pytest
import asyncio
import uuid
from unittest.mock import Mock, AsyncMock, patch

from app.api.chat_with_cancellation import (
    cancel_chat_session,
    get_session_status,
    get_active_sessions
)
from app.services.chat_session_manager import ChatSessionManager, SessionStatus


class TestChatCancellationIntegration:
    """Integration tests for chat cancellation."""
    
    @pytest.fixture
    def session_manager(self):
        """Create session manager for testing."""
        return ChatSessionManager(max_concurrent_sessions=5)
    
    @pytest.mark.asyncio
    async def test_cancel_session_endpoint_logic(self, session_manager):
        """Test the session cancellation endpoint logic."""
        
        # Create a mock active session
        session_id = str(uuid.uuid4())
        mock_task = Mock()
        mock_task.cancelled.return_value = False
        mock_task.done.return_value = False
        mock_task.cancel = Mock()
        
        token = session_manager.register_session(
            session_id=session_id,
            conversation_id="test-conv",
            asyncio_task=mock_task
        )
        
        assert session_manager.has_active_session(session_id)
        
        # Test cancellation endpoint logic
        result = await cancel_chat_session(session_id, session_manager)
        
        # Should return success
        assert result["cancelled"] == True
        assert result["session_id"] == session_id
        assert "Session cancelled successfully" in result["message"]
        
        # Verify task was cancelled
        mock_task.cancel.assert_called_once()
        assert token.cancelled == True
    
    @pytest.mark.asyncio
    async def test_cancel_nonexistent_session_endpoint(self, session_manager):
        """Test cancelling a session that doesn't exist."""
        
        nonexistent_id = str(uuid.uuid4())
        
        result = await cancel_chat_session(nonexistent_id, session_manager)
        
        assert result["cancelled"] == False
        assert result["session_id"] == nonexistent_id
        assert "Session not found" in result["message"]
    
    @pytest.mark.asyncio
    async def test_session_status_endpoint_logic(self, session_manager):
        """Test session status endpoint logic."""
        
        # Test with active session
        session_id = str(uuid.uuid4())
        mock_task = Mock()
        mock_task.cancelled.return_value = False
        mock_task.done.return_value = False
        
        session_manager.register_session(
            session_id=session_id,
            conversation_id="test-conv",
            asyncio_task=mock_task
        )
        
        result = await get_session_status(session_id, session_manager)
        
        assert result["session_id"] == session_id
        assert result["status"] == SessionStatus.ACTIVE.value
        assert result["active"] == True
    
    @pytest.mark.asyncio
    async def test_session_status_completed_session(self, session_manager):
        """Test session status for completed session."""
        
        session_id = str(uuid.uuid4())
        mock_task = Mock()
        mock_task.cancelled.return_value = False
        mock_task.done.return_value = True
        
        session_manager.register_session(
            session_id=session_id,
            conversation_id="test-conv",
            asyncio_task=mock_task
        )
        
        result = await get_session_status(session_id, session_manager)
        
        assert result["session_id"] == session_id
        assert result["status"] == SessionStatus.COMPLETED.value
        assert result["active"] == False
    
    @pytest.mark.asyncio
    async def test_session_status_not_found(self, session_manager):
        """Test session status for non-existent session."""
        
        nonexistent_id = str(uuid.uuid4())
        
        result = await get_session_status(nonexistent_id, session_manager)
        
        assert result["session_id"] == nonexistent_id
        assert result["status"] == SessionStatus.NOT_FOUND.value
        assert result["active"] == False
    
    @pytest.mark.asyncio
    async def test_active_sessions_endpoint_logic(self, session_manager):
        """Test active sessions endpoint logic."""
        
        # Create multiple active sessions
        sessions = []
        for i in range(3):
            session_id = str(uuid.uuid4())
            mock_task = Mock()
            mock_task.cancelled.return_value = False
            mock_task.done.return_value = False
            
            token = session_manager.register_session(
                session_id=session_id,
                conversation_id=f"conv-{i}",
                asyncio_task=mock_task,
                current_stage=i + 1
            )
            sessions.append((session_id, token))
        
        result = await get_active_sessions(session_manager)
        
        assert result["active_session_count"] == 3
        assert len(result["sessions"]) == 3
        
        # Check session details
        returned_session_ids = {s["session_id"] for s in result["sessions"]}
        expected_session_ids = {s[0] for s in sessions}
        assert returned_session_ids == expected_session_ids
        
        # Check session details are included
        for session_info in result["sessions"]:
            assert "conversation_id" in session_info
            assert "current_stage" in session_info
            assert "created_at" in session_info
            assert "is_cancelled" in session_info
            assert "is_active" in session_info
    
    @pytest.mark.asyncio
    async def test_active_sessions_with_mixed_states(self, session_manager):
        """Test active sessions endpoint with mixed session states."""
        
        # Active session
        active_id = str(uuid.uuid4())
        active_task = Mock()
        active_task.cancelled.return_value = False
        active_task.done.return_value = False
        
        session_manager.register_session(
            session_id=active_id,
            conversation_id="active-conv",
            asyncio_task=active_task
        )
        
        # Completed session
        completed_id = str(uuid.uuid4())
        completed_task = Mock()
        completed_task.cancelled.return_value = False
        completed_task.done.return_value = True
        
        session_manager.register_session(
            session_id=completed_id,
            conversation_id="completed-conv",
            asyncio_task=completed_task
        )
        
        # Cancelled session
        cancelled_id = str(uuid.uuid4())
        cancelled_task = Mock()
        cancelled_task.cancelled.return_value = True
        cancelled_task.done.return_value = True
        
        cancelled_token = session_manager.register_session(
            session_id=cancelled_id,
            conversation_id="cancelled-conv",
            asyncio_task=cancelled_task
        )
        cancelled_token.cancelled = True
        
        result = await get_active_sessions(session_manager)
        
        # Should show all sessions (they haven't been cleaned up yet)
        assert result["active_session_count"] == 3
        assert len(result["sessions"]) == 3
        
        # Find each session in results
        session_by_id = {s["session_id"]: s for s in result["sessions"]}
        
        assert session_by_id[active_id]["is_active"] == True
        assert session_by_id[active_id]["is_cancelled"] == False
        
        assert session_by_id[completed_id]["is_active"] == False
        assert session_by_id[completed_id]["is_cancelled"] == False
        
        assert session_by_id[cancelled_id]["is_active"] == False
        assert session_by_id[cancelled_id]["is_cancelled"] == True
    
    @pytest.mark.asyncio
    async def test_concurrent_session_operations(self, session_manager):
        """Test concurrent session operations."""
        
        # Create multiple sessions concurrently
        async def create_and_cancel_session(session_id):
            mock_task = Mock()
            mock_task.cancelled.return_value = False
            mock_task.done.return_value = False
            mock_task.cancel = Mock()
            
            # Register session
            session_manager.register_session(
                session_id=session_id,
                conversation_id=f"conv-{session_id}",
                asyncio_task=mock_task
            )
            
            # Small delay
            await asyncio.sleep(0.01)
            
            # Cancel session
            result = await cancel_chat_session(session_id, session_manager)
            return result
        
        # Run multiple concurrent operations
        session_ids = [str(uuid.uuid4()) for _ in range(5)]
        tasks = [
            asyncio.create_task(create_and_cancel_session(sid))
            for sid in session_ids
        ]
        
        results = await asyncio.gather(*tasks)
        
        # All should have been cancelled successfully
        for result in results:
            assert result["cancelled"] == True
    
    @pytest.mark.asyncio
    async def test_session_lifecycle_through_endpoints(self, session_manager):
        """Test complete session lifecycle through endpoint functions."""
        
        session_id = str(uuid.uuid4())
        
        # 1. Initially not found
        status_result = await get_session_status(session_id, session_manager)
        assert status_result["status"] == SessionStatus.NOT_FOUND.value
        
        # 2. Create active session
        mock_task = Mock()
        mock_task.cancelled.return_value = False
        mock_task.done.return_value = False
        mock_task.cancel = Mock()
        
        session_manager.register_session(
            session_id=session_id,
            conversation_id="lifecycle-test",
            asyncio_task=mock_task
        )
        
        # 3. Should be active
        status_result = await get_session_status(session_id, session_manager)
        assert status_result["status"] == SessionStatus.ACTIVE.value
        assert status_result["active"] == True
        
        # 4. Should appear in active sessions
        active_result = await get_active_sessions(session_manager)
        session_ids = {s["session_id"] for s in active_result["sessions"]}
        assert session_id in session_ids
        
        # 5. Cancel session
        cancel_result = await cancel_chat_session(session_id, session_manager)
        assert cancel_result["cancelled"] == True
        
        # 6. Should be cancelled
        status_result = await get_session_status(session_id, session_manager)
        assert status_result["status"] == SessionStatus.CANCELLED.value
        assert status_result["active"] == False
        
        # Verify task was cancelled
        mock_task.cancel.assert_called_once()