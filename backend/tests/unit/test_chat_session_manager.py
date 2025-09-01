"""
Unit tests for ChatSessionManager - handles active chat sessions with cancellation tokens.

Following TDD approach: tests first, then implementation.
"""

import pytest
import asyncio
import uuid
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timedelta

from app.services.chat_session_manager import (
    ChatSessionManager,
    ChatCancellationToken,
    SessionStatus
)


class TestChatCancellationToken:
    """Test the ChatCancellationToken data structure."""
    
    def test_token_creation(self):
        """Test basic token creation with required fields."""
        session_id = "test-session-123"
        conversation_id = "conv-456"
        
        # Create mock asyncio task
        mock_task = Mock()
        mock_task.cancelled.return_value = False
        mock_task.done.return_value = False
        
        token = ChatCancellationToken(
            session_id=session_id,
            conversation_id=conversation_id,
            asyncio_task=mock_task,
            current_stage=2
        )
        
        assert token.session_id == session_id
        assert token.conversation_id == conversation_id
        assert token.asyncio_task == mock_task
        assert token.current_stage == 2
        assert token.cancelled == False
        assert isinstance(token.created_at, datetime)
    
    def test_token_cancellation_status(self):
        """Test cancellation status detection."""
        mock_task = Mock()
        mock_task.cancelled.return_value = True
        mock_task.done.return_value = True
        
        token = ChatCancellationToken(
            session_id="test",
            conversation_id="conv",
            asyncio_task=mock_task
        )
        
        assert token.is_cancelled() == True
    
    def test_token_completion_status(self):
        """Test task completion detection."""
        mock_task = Mock()
        mock_task.cancelled.return_value = False
        mock_task.done.return_value = True
        
        token = ChatCancellationToken(
            session_id="test",
            conversation_id="conv", 
            asyncio_task=mock_task
        )
        
        assert token.is_completed() == True
    
    def test_token_active_status(self):
        """Test active status (not cancelled and not done)."""
        mock_task = Mock()
        mock_task.cancelled.return_value = False
        mock_task.done.return_value = False
        
        token = ChatCancellationToken(
            session_id="test",
            conversation_id="conv",
            asyncio_task=mock_task
        )
        
        assert token.is_active() == True


class TestChatSessionManager:
    """Test the ChatSessionManager functionality."""
    
    @pytest.fixture
    def session_manager(self):
        """Create a ChatSessionManager instance for testing."""
        return ChatSessionManager()
    
    @pytest.fixture
    def mock_task(self):
        """Create a mock asyncio task."""
        task = Mock()
        task.cancelled.return_value = False
        task.done.return_value = False
        task.cancel = Mock()
        return task
    
    def test_manager_initialization(self, session_manager):
        """Test session manager starts with empty state."""
        assert len(session_manager.active_sessions) == 0
        assert session_manager.max_concurrent_sessions == 10
    
    def test_register_session(self, session_manager, mock_task):
        """Test registering a new chat session."""
        session_id = "test-session"
        conversation_id = "conv-123"
        
        token = session_manager.register_session(
            session_id=session_id,
            conversation_id=conversation_id,
            asyncio_task=mock_task,
            current_stage=1
        )
        
        assert token.session_id == session_id
        assert token.conversation_id == conversation_id
        assert session_id in session_manager.active_sessions
        assert session_manager.active_sessions[session_id] == token
        assert len(session_manager.active_sessions) == 1
    
    def test_register_duplicate_session(self, session_manager, mock_task):
        """Test registering duplicate session_id raises error."""
        session_id = "duplicate"
        
        # Register first session
        session_manager.register_session(
            session_id=session_id,
            conversation_id="conv1",
            asyncio_task=mock_task
        )
        
        # Try to register duplicate
        with pytest.raises(ValueError, match="Session .* already active"):
            session_manager.register_session(
                session_id=session_id,
                conversation_id="conv2", 
                asyncio_task=Mock()
            )
    
    def test_get_session_exists(self, session_manager, mock_task):
        """Test getting an existing session."""
        session_id = "existing"
        token = session_manager.register_session(
            session_id=session_id,
            conversation_id="conv",
            asyncio_task=mock_task
        )
        
        retrieved = session_manager.get_session(session_id)
        assert retrieved == token
    
    def test_get_session_not_exists(self, session_manager):
        """Test getting non-existent session returns None."""
        result = session_manager.get_session("nonexistent")
        assert result is None
    
    def test_has_active_session(self, session_manager, mock_task):
        """Test checking if session is active."""
        session_id = "active_test"
        
        # No session initially
        assert session_manager.has_active_session(session_id) == False
        
        # Register session
        session_manager.register_session(
            session_id=session_id,
            conversation_id="conv",
            asyncio_task=mock_task
        )
        
        # Should be active now
        assert session_manager.has_active_session(session_id) == True
    
    @pytest.mark.asyncio
    async def test_cancel_session_success(self, session_manager, mock_task):
        """Test successful session cancellation."""
        session_id = "cancel_test"
        mock_task.cancel = Mock()
        
        # Register session
        session_manager.register_session(
            session_id=session_id,
            conversation_id="conv",
            asyncio_task=mock_task
        )
        
        # Cancel session
        result = await session_manager.cancel_session(session_id)
        
        assert result == True
        mock_task.cancel.assert_called_once()
        
        # Session should be marked as cancelled
        token = session_manager.get_session(session_id)
        assert token.cancelled == True
    
    @pytest.mark.asyncio
    async def test_cancel_session_not_exists(self, session_manager):
        """Test cancelling non-existent session."""
        result = await session_manager.cancel_session("nonexistent")
        assert result == False
    
    @pytest.mark.asyncio
    async def test_cancel_session_already_cancelled(self, session_manager):
        """Test cancelling already cancelled session."""
        session_id = "already_cancelled"
        mock_task = Mock()
        mock_task.cancel = Mock()
        mock_task.cancelled.return_value = True
        
        token = session_manager.register_session(
            session_id=session_id,
            conversation_id="conv",
            asyncio_task=mock_task
        )
        token.cancelled = True
        
        # Try to cancel again
        result = await session_manager.cancel_session(session_id)
        assert result == False
        mock_task.cancel.assert_not_called()
    
    def test_remove_session(self, session_manager, mock_task):
        """Test removing session from active list."""
        session_id = "remove_test"
        
        # Register and verify
        session_manager.register_session(
            session_id=session_id,
            conversation_id="conv",
            asyncio_task=mock_task
        )
        assert len(session_manager.active_sessions) == 1
        
        # Remove and verify
        removed = session_manager.remove_session(session_id)
        assert removed == True
        assert len(session_manager.active_sessions) == 0
        assert session_id not in session_manager.active_sessions
    
    def test_remove_session_not_exists(self, session_manager):
        """Test removing non-existent session."""
        result = session_manager.remove_session("nonexistent")
        assert result == False
    
    @pytest.mark.asyncio
    async def test_cleanup_completed_sessions(self, session_manager):
        """Test cleanup of completed/cancelled sessions."""
        # Create different types of tasks
        active_task = Mock()
        active_task.cancelled.return_value = False
        active_task.done.return_value = False
        
        completed_task = Mock()
        completed_task.cancelled.return_value = False
        completed_task.done.return_value = True
        
        cancelled_task = Mock()
        cancelled_task.cancelled.return_value = True
        cancelled_task.done.return_value = True
        
        # Register sessions
        session_manager.register_session("active", "conv1", active_task)
        session_manager.register_session("completed", "conv2", completed_task)
        session_manager.register_session("cancelled", "conv3", cancelled_task)
        
        assert len(session_manager.active_sessions) == 3
        
        # Cleanup should remove completed and cancelled
        cleaned_count = await session_manager.cleanup_completed_sessions()
        
        assert cleaned_count == 2
        assert len(session_manager.active_sessions) == 1
        assert "active" in session_manager.active_sessions
        assert "completed" not in session_manager.active_sessions
        assert "cancelled" not in session_manager.active_sessions
    
    def test_get_session_status(self, session_manager, mock_task):
        """Test getting session status."""
        # Non-existent session
        status = session_manager.get_session_status("nonexistent")
        assert status == SessionStatus.NOT_FOUND
        
        # Active session
        session_id = "status_test"
        session_manager.register_session(
            session_id=session_id,
            conversation_id="conv",
            asyncio_task=mock_task
        )
        
        status = session_manager.get_session_status(session_id)
        assert status == SessionStatus.ACTIVE
        
        # Cancelled session
        token = session_manager.get_session(session_id)
        token.cancelled = True
        
        status = session_manager.get_session_status(session_id)
        assert status == SessionStatus.CANCELLED
        
        # Completed session
        token.cancelled = False
        mock_task.done.return_value = True
        
        status = session_manager.get_session_status(session_id)
        assert status == SessionStatus.COMPLETED
    
    def test_get_active_session_count(self, session_manager, mock_task):
        """Test getting count of active sessions."""
        assert session_manager.get_active_session_count() == 0
        
        # Add some sessions
        for i in range(3):
            session_manager.register_session(
                session_id=f"session_{i}",
                conversation_id=f"conv_{i}",
                asyncio_task=Mock()
            )
        
        assert session_manager.get_active_session_count() == 3
    
    def test_max_concurrent_sessions_limit(self, session_manager, mock_task):
        """Test max concurrent sessions limit enforcement."""
        session_manager.max_concurrent_sessions = 2
        
        # Register up to limit
        session_manager.register_session("session_1", "conv_1", mock_task)
        session_manager.register_session("session_2", "conv_2", Mock())
        
        # Try to exceed limit
        with pytest.raises(RuntimeError, match="Maximum concurrent sessions"):
            session_manager.register_session("session_3", "conv_3", Mock())
    
    @pytest.mark.asyncio
    async def test_cancel_all_sessions(self, session_manager):
        """Test cancelling all active sessions."""
        # Create multiple sessions
        tasks = []
        for i in range(3):
            task = Mock()
            task.cancel = Mock()
            task.cancelled.return_value = False
            task.done.return_value = False
            tasks.append(task)
            
            session_manager.register_session(
                session_id=f"session_{i}",
                conversation_id=f"conv_{i}",
                asyncio_task=task
            )
        
        assert len(session_manager.active_sessions) == 3
        
        # Cancel all
        cancelled_count = await session_manager.cancel_all_sessions()
        
        assert cancelled_count == 3
        
        # Verify all tasks were cancelled
        for task in tasks:
            task.cancel.assert_called_once()
        
        # Verify all tokens marked as cancelled
        for token in session_manager.active_sessions.values():
            assert token.cancelled == True
    
    def test_update_session_stage(self, session_manager, mock_task):
        """Test updating session's current stage."""
        session_id = "stage_test"
        token = session_manager.register_session(
            session_id=session_id,
            conversation_id="conv",
            asyncio_task=mock_task,
            current_stage=1
        )
        
        assert token.current_stage == 1
        
        # Update stage
        result = session_manager.update_session_stage(session_id, 3)
        assert result == True
        assert token.current_stage == 3
        
        # Try to update non-existent session
        result = session_manager.update_session_stage("nonexistent", 5)
        assert result == False