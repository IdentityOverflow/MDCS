"""
Unit tests for the Script Execution Context.

Tests the context object that provides access to conversation data, plugin functions,
and database sessions for advanced module scripts.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from app.core.script_context import ScriptExecutionContext


class TestScriptExecutionContext:
    """Test cases for the ScriptExecutionContext class."""

    def test_context_initialization_basic(self):
        """Test basic context initialization with required parameters."""
        mock_db_session = Mock()
        
        context = ScriptExecutionContext(
            conversation_id="test-123",
            persona_id="persona-456",
            db_session=mock_db_session
        )
        
        assert context.conversation_id == "test-123"
        assert context.persona_id == "persona-456"
        assert context.db_session is mock_db_session
        assert context.trigger_data == {}

    def test_context_initialization_with_trigger_data(self):
        """Test context initialization with trigger data."""
        mock_db_session = Mock()
        trigger_data = {
            "last_user_message": "Hello world",
            "message_count": 5,
            "triggered_by": "keyword"
        }
        
        context = ScriptExecutionContext(
            conversation_id="test-123",
            persona_id="persona-456",
            db_session=mock_db_session,
            trigger_data=trigger_data
        )
        
        assert context.trigger_data == trigger_data
        assert context.trigger_data["last_user_message"] == "Hello world"

    def test_plugin_function_access_via_getattr(self):
        """Test accessing plugin functions via attribute access."""
        mock_db_session = Mock()
        
        # Mock plugin registry to return a test function
        with patch('app.core.script_context.plugin_registry') as mock_registry:
            mock_registry.get_context.return_value = {
                "test_function": lambda x: x * 2
            }
            
            context = ScriptExecutionContext(
                conversation_id="test-123",
                persona_id="persona-456",
                db_session=mock_db_session
            )
            
            # Should be able to access plugin function as attribute
            result = context.test_function(5)
            assert result == 10

    def test_plugin_function_with_db_session_injection(self):
        """Test plugin function with automatic db_session injection."""
        mock_db_session = Mock()
        
        def mock_plugin_function(table_name, db_session=None):
            """Mock plugin function that expects db_session parameter."""
            if db_session is not None:
                return f"Queried {table_name} with session {id(db_session)}"
            return f"Queried {table_name} without session"
        
        with patch('app.core.script_context.plugin_registry') as mock_registry:
            mock_registry.get_context.return_value = {
                "query_table": mock_plugin_function
            }
            
            context = ScriptExecutionContext(
                conversation_id="test-123",
                persona_id="persona-456",
                db_session=mock_db_session
            )
            
            # Call plugin function - db_session should be auto-injected
            result = context.query_table("messages")
            assert "with session" in result
            assert str(id(mock_db_session)) in result

    def test_plugin_function_without_db_session_parameter(self):
        """Test plugin function that doesn't need db_session injection."""
        mock_db_session = Mock()
        
        def mock_simple_function(value):
            """Mock plugin function that doesn't need db_session."""
            return f"Value: {value}"
        
        with patch('app.core.script_context.plugin_registry') as mock_registry:
            mock_registry.get_context.return_value = {
                "simple_func": mock_simple_function
            }
            
            context = ScriptExecutionContext(
                conversation_id="test-123",
                persona_id="persona-456",
                db_session=mock_db_session
            )
            
            # Call plugin function - should work without db_session
            result = context.simple_func("test")
            assert result == "Value: test"

    def test_nonexistent_plugin_function_raises_attribute_error(self):
        """Test that accessing nonexistent plugin function raises AttributeError."""
        mock_db_session = Mock()
        
        with patch('app.core.script_context.plugin_registry') as mock_registry:
            mock_registry.get_context.return_value = {}
            
            context = ScriptExecutionContext(
                conversation_id="test-123",
                persona_id="persona-456",
                db_session=mock_db_session
            )
            
            with pytest.raises(AttributeError) as exc_info:
                _ = context.nonexistent_function
            
            assert "nonexistent_function" in str(exc_info.value)
            assert "not available" in str(exc_info.value)

    def test_context_provides_conversation_access_methods(self):
        """Test that context provides methods for conversation access."""
        mock_db_session = Mock()
        
        # Mock plugin functions that would be used for conversation access
        def mock_get_history(conv_id, limit=10, db_session=None):
            return [{"role": "user", "content": "Hello"}] * min(limit, 5)
        
        def mock_get_message_count(conv_id, db_session=None):
            return 42
        
        with patch('app.core.script_context.plugin_registry') as mock_registry:
            mock_registry.get_context.return_value = {
                "get_conversation_history": mock_get_history,
                "get_message_count": mock_get_message_count
            }
            
            context = ScriptExecutionContext(
                conversation_id="test-123",
                persona_id="persona-456",
                db_session=mock_db_session
            )
            
            # Test conversation history access
            history = context.get_conversation_history("test-123", 3)
            assert len(history) == 3
            assert history[0]["role"] == "user"
            
            # Test message count access
            count = context.get_message_count("test-123")
            assert count == 42

    def test_context_attribute_access_for_built_in_attributes(self):
        """Test that built-in attributes are accessible normally."""
        mock_db_session = Mock()
        
        context = ScriptExecutionContext(
            conversation_id="test-123",
            persona_id="persona-456",
            db_session=mock_db_session
        )
        
        # Built-in attributes should be accessible
        assert context.conversation_id == "test-123"
        assert context.persona_id == "persona-456"
        assert context.db_session is mock_db_session
        assert hasattr(context, "__dict__")

    def test_plugin_function_error_handling(self):
        """Test error handling when plugin function raises exception."""
        mock_db_session = Mock()
        
        def failing_function():
            raise ValueError("Test error")
        
        with patch('app.core.script_context.plugin_registry') as mock_registry:
            mock_registry.get_context.return_value = {
                "failing_func": failing_function
            }
            
            context = ScriptExecutionContext(
                conversation_id="test-123",
                persona_id="persona-456",
                db_session=mock_db_session
            )
            
            # Plugin function error should propagate
            with pytest.raises(ValueError) as exc_info:
                context.failing_func()
            
            assert "Test error" in str(exc_info.value)

    def test_context_with_real_plugin_functions(self):
        """Test context with actual loaded plugin functions."""
        mock_db_session = Mock()
        
        # Load real plugins for this test
        from app.core.script_plugins import plugin_registry
        plugin_registry.load_all_plugins()
        
        context = ScriptExecutionContext(
            conversation_id="test-123",
            persona_id="persona-456",
            db_session=mock_db_session
        )
        
        # Test real plugin functions
        current_time = context.get_current_time("%H:%M")
        assert ":" in current_time
        assert len(current_time) == 5  # HH:MM format
        
        # Test function with parameters
        joined = context.join_strings(["a", "b", "c"], " | ")
        assert joined == "a | b | c"
        
        # Test business hours function
        is_business = context.is_business_hours()
        assert isinstance(is_business, bool)