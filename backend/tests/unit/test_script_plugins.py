"""
Unit tests for the Script Plugin Registry System.

Tests the auto-discovery decorator system for registering plugin functions
that can be used in advanced module scripts.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import importlib
import sys
from app.core.script_plugins import ScriptPluginRegistry, plugin_registry


class TestScriptPluginRegistry:
    """Test cases for the ScriptPluginRegistry class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.registry = ScriptPluginRegistry()

    def test_register_single_function(self):
        """Test registering a single function with decorator."""
        @self.registry.register("test_function")
        def sample_function():
            return "test result"
        
        context = self.registry.get_context()
        
        assert "test_function" in context
        assert context["test_function"] is sample_function
        assert context["test_function"]() == "test result"

    def test_register_multiple_functions(self):
        """Test registering multiple functions."""
        @self.registry.register("function_one")
        def func_one():
            return "one"
        
        @self.registry.register("function_two")
        def func_two():
            return "two"
        
        context = self.registry.get_context()
        
        assert "function_one" in context
        assert "function_two" in context
        assert context["function_one"]() == "one"
        assert context["function_two"]() == "two"

    def test_register_function_with_parameters(self):
        """Test registering function that takes parameters."""
        @self.registry.register("add_numbers")
        def add(a, b):
            return a + b
        
        context = self.registry.get_context()
        
        assert "add_numbers" in context
        assert context["add_numbers"](5, 3) == 8

    def test_register_function_returns_original(self):
        """Test that decorator returns the original function unchanged."""
        def original_function():
            return "original"
        
        decorated = self.registry.register("test_name")(original_function)
        
        assert decorated is original_function
        assert decorated() == "original"

    def test_get_context_returns_copy(self):
        """Test that get_context returns a copy, not the original dict."""
        @self.registry.register("test_func")
        def test_func():
            pass
        
        context1 = self.registry.get_context()
        context2 = self.registry.get_context()
        
        # Should be equal but not the same object
        assert context1 == context2
        assert context1 is not context2
        
        # Modifying one shouldn't affect the other
        context1["new_key"] = "value"
        assert "new_key" not in context2

    def test_register_overwrites_duplicate_names(self):
        """Test that registering the same name overwrites previous function."""
        @self.registry.register("duplicate_name")
        def first_function():
            return "first"
        
        @self.registry.register("duplicate_name")
        def second_function():
            return "second"
        
        context = self.registry.get_context()
        
        assert context["duplicate_name"]() == "second"

    def test_empty_registry_context(self):
        """Test that empty registry returns empty context."""
        context = self.registry.get_context()
        assert context == {}

    @patch('app.core.script_plugins.pkgutil.walk_packages')
    @patch('app.core.script_plugins.importlib.import_module')
    def test_load_all_plugins_success(self, mock_import_module, mock_walk_packages):
        """Test successful loading of all plugin modules."""
        # Create a mock plugins package
        mock_plugins_package = Mock()
        mock_plugins_package.__path__ = ['/fake/path']
        mock_plugins_package.__name__ = 'app.plugins'
        
        # Mock plugin modules discovery  
        mock_walk_packages.return_value = [
            (None, "app.plugins.time_plugins", False),
            (None, "app.plugins.core_plugins", False)
        ]
        
        # Mock import behavior: first call returns package, subsequent calls import modules
        mock_import_module.side_effect = [
            mock_plugins_package,  # First call to import app.plugins
            Mock(),  # Second call to import time_plugins
            Mock()   # Third call to import core_plugins
        ]
        
        self.registry.load_all_plugins()
        
        # Should have attempted to import package + 2 modules = 3 calls
        assert mock_import_module.call_count == 3
        mock_import_module.assert_any_call("app.plugins")
        mock_import_module.assert_any_call("app.plugins.time_plugins")
        mock_import_module.assert_any_call("app.plugins.core_plugins")

    @patch('app.core.script_plugins.pkgutil.walk_packages')
    @patch('app.core.script_plugins.importlib.import_module')
    def test_load_all_plugins_with_import_error(self, mock_import_module, mock_walk_packages):
        """Test plugin loading continues even if one module fails to import."""
        # Create a mock plugins package
        mock_plugins_package = Mock()
        mock_plugins_package.__path__ = ['/fake/path']
        mock_plugins_package.__name__ = 'app.plugins'
        
        # Mock plugin modules
        mock_walk_packages.return_value = [
            (None, "app.plugins.working_plugin", False),
            (None, "app.plugins.broken_plugin", False)
        ]
        
        # Mock imports: package succeeds, working plugin succeeds, broken plugin fails
        mock_import_module.side_effect = [
            mock_plugins_package,  # app.plugins import succeeds
            Mock(),  # working_plugin import succeeds
            ImportError("Module not found")  # broken_plugin import fails
        ]
        
        # Should not raise exception
        self.registry.load_all_plugins()
        
        # Should have attempted all imports (package + 2 modules)
        assert mock_import_module.call_count == 3

    @patch('app.core.script_plugins.pkgutil.walk_packages')
    @patch('app.core.script_plugins.importlib.import_module')
    def test_load_all_plugins_skips_already_loaded(self, mock_import_module, mock_walk_packages):
        """Test that already loaded plugins are not loaded again."""
        # Create a mock plugins package
        mock_plugins_package = Mock()
        mock_plugins_package.__path__ = ['/fake/path']
        mock_plugins_package.__name__ = 'app.plugins'
        
        # Mock plugin modules
        mock_walk_packages.return_value = [
            (None, "app.plugins.test_plugin", False)
        ]
        
        # Mock import behavior
        mock_import_module.side_effect = [
            mock_plugins_package,  # First call to load_all_plugins: import app.plugins
            Mock(),  # First call to load_all_plugins: import test_plugin
            mock_plugins_package,  # Second call to load_all_plugins: import app.plugins again
            # No additional import for test_plugin because it's already loaded
        ]
        
        # Load plugins twice
        self.registry.load_all_plugins()
        self.registry.load_all_plugins()
        
        # Should import package twice (2 calls to load_all_plugins) + plugin once = 3 total
        assert mock_import_module.call_count == 3
        
        # Verify test_plugin was only imported once
        test_plugin_calls = [call for call in mock_import_module.call_args_list 
                           if call[0][0] == "app.plugins.test_plugin"]
        assert len(test_plugin_calls) == 1


class TestGlobalPluginRegistry:
    """Test cases for the global plugin registry instance."""

    def test_global_registry_exists(self):
        """Test that global registry instance exists and is a ScriptPluginRegistry."""
        from app.core.script_plugins import plugin_registry
        
        assert plugin_registry is not None
        assert isinstance(plugin_registry, ScriptPluginRegistry)

    def test_global_registry_registration(self):
        """Test registering function with global registry."""
        # Clean up any existing registrations for this test
        original_functions = plugin_registry._functions.copy()
        plugin_registry._functions.clear()
        
        try:
            @plugin_registry.register("global_test_func")
            def global_test():
                return "global result"
            
            context = plugin_registry.get_context()
            
            assert "global_test_func" in context
            assert context["global_test_func"]() == "global result"
            
        finally:
            # Restore original state
            plugin_registry._functions = original_functions


class TestPluginFunctionExamples:
    """Test examples of typical plugin functions."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.registry = ScriptPluginRegistry()

    def test_time_plugin_example(self):
        """Test example time plugin function."""
        from datetime import datetime
        
        @self.registry.register("get_current_time")
        def get_current_time(format: str = "%Y-%m-%d %H:%M"):
            return datetime.now().strftime(format)
        
        context = self.registry.get_context()
        
        # Should return current time in default format
        result = context["get_current_time"]()
        assert len(result) == 16  # "YYYY-MM-DD HH:MM" length
        assert "-" in result and ":" in result
        
        # Should accept custom format
        custom_result = context["get_current_time"]("%Y")
        assert len(custom_result) == 4  # Just the year

    def test_database_plugin_example(self):
        """Test example database plugin function with session injection."""
        @self.registry.register("count_items")
        def count_items(table_name: str, db_session=None):
            # In real implementation, would query database
            if db_session is None:
                return 0
            return getattr(db_session, f"count_{table_name}", lambda: 42)()
        
        context = self.registry.get_context()
        
        # Without db_session
        result = context["count_items"]("messages")
        assert result == 0
        
        # With mock db_session
        mock_session = Mock()
        mock_session.count_messages = Mock(return_value=100)
        
        result = context["count_items"]("messages", db_session=mock_session)
        assert result == 100

    def test_string_processing_plugin_example(self):
        """Test example string processing plugin function."""
        @self.registry.register("process_text")
        def process_text(text: str, operation: str = "upper"):
            operations = {
                "upper": text.upper,
                "lower": text.lower,
                "title": text.title,
                "reverse": lambda: text[::-1]
            }
            return operations.get(operation, lambda: text)()
        
        context = self.registry.get_context()
        func = context["process_text"]
        
        assert func("hello world") == "HELLO WORLD"
        assert func("Hello World", "lower") == "hello world"
        assert func("hello world", "title") == "Hello World"
        assert func("hello", "reverse") == "olleh"
        assert func("test", "unknown") == "test"  # Unknown operation returns original


class TestAIPlugins:
    """Test cases for AI text processing plugin functions."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Use global registry to access actual AI plugins
        from app.core.script_plugins import plugin_registry
        plugin_registry.load_all_plugins()
        self.plugin_context = plugin_registry.get_context()

    def test_ai_plugins_loaded(self):
        """Test that AI processing plugins are loaded correctly."""
        expected_ai_functions = [
            "ai_process_text",
            "ai_summarize", 
            "ai_extract_topics",
            "ai_analyze_sentiment",
            "ai_extract_questions"
        ]
        
        for func_name in expected_ai_functions:
            assert func_name in self.plugin_context, f"AI function {func_name} not loaded"
            assert callable(self.plugin_context[func_name]), f"AI function {func_name} not callable"

    def test_ai_process_text_function_signature(self):
        """Test that ai_process_text function exists and handles parameters correctly."""
        ai_process_text = self.plugin_context["ai_process_text"]
        
        # Test with minimal parameters (should not crash)
        result = ai_process_text("test text", "summarize this")
        
        # Should return a string (even if it's an error message or placeholder)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_ai_summarize_function_signature(self):
        """Test that ai_summarize function exists and handles parameters correctly.""" 
        ai_summarize = self.plugin_context["ai_summarize"]
        
        # Test with minimal parameters
        result = ai_summarize("This is a long text that needs to be summarized for testing purposes.")
        
        # Should return a string
        assert isinstance(result, str)
        assert len(result) > 0

    def test_ai_functions_handle_empty_input(self):
        """Test that AI functions handle empty/invalid input gracefully."""
        ai_process_text = self.plugin_context["ai_process_text"]
        
        # Test with empty text
        result = ai_process_text("", "summarize")
        assert isinstance(result, str)
        assert result == ""  # Should return empty string for empty input
        
        # Test with empty instruction
        result = ai_process_text("some text", "")
        assert isinstance(result, str)
        assert result == "some text"  # Should return original text for empty instruction

    def test_ai_functions_parameter_validation(self):
        """Test that AI functions validate parameters correctly."""
        ai_process_text = self.plugin_context["ai_process_text"]
        
        # Test with invalid provider
        result = ai_process_text("test", "summarize", provider="invalid_provider")
        assert isinstance(result, str)
        assert "Unsupported provider" in result or "Error" in result


class TestConversationPlugins:
    """Test cases for conversation access plugin functions."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        from app.core.script_plugins import plugin_registry
        plugin_registry.load_all_plugins()
        self.plugin_context = plugin_registry.get_context()

    def test_conversation_plugins_loaded(self):
        """Test that conversation plugins are loaded correctly."""
        expected_conv_functions = [
            "get_message_count",
            "get_recent_messages",
            "get_conversation_summary", 
            "get_persona_info",
            "get_conversation_history"
        ]
        
        for func_name in expected_conv_functions:
            assert func_name in self.plugin_context, f"Conversation function {func_name} not loaded"
            assert callable(self.plugin_context[func_name]), f"Conversation function {func_name} not callable"

    def test_get_message_count_without_session(self):
        """Test get_message_count handles missing database session gracefully."""
        get_message_count = self.plugin_context["get_message_count"]
        
        # Without db_session should return 0
        result = get_message_count()
        assert result == 0

    def test_get_recent_messages_without_session(self):
        """Test get_recent_messages handles missing database session gracefully."""
        get_recent_messages = self.plugin_context["get_recent_messages"]
        
        # Without db_session should return empty list
        result = get_recent_messages()
        assert result == []
        assert isinstance(result, list)

    def test_conversation_functions_handle_parameters(self):
        """Test that conversation functions accept and handle their parameters correctly."""
        # Test get_message_count with conversation_id
        get_message_count = self.plugin_context["get_message_count"]
        result = get_message_count("test-conversation-id")
        assert isinstance(result, int)
        
        # Test get_recent_messages with limit
        get_recent_messages = self.plugin_context["get_recent_messages"]
        result = get_recent_messages(limit=5)
        assert isinstance(result, list)
        
        # Test get_conversation_summary
        get_conversation_summary = self.plugin_context["get_conversation_summary"]
        result = get_conversation_summary()
        assert isinstance(result, dict)
        
        # Test get_persona_info (now returns DictObject)
        get_persona_info = self.plugin_context["get_persona_info"]
        result = get_persona_info()
        # Should be a DictObject that supports both dict and attribute access
        assert hasattr(result, 'get')  # dict-like behavior
        assert hasattr(result, '_data')  # DictObject internal
        # Since there's no db session, it returns empty DictObject
        assert result.get('name') is None  # Empty result due to no DB session
        assert len(result) == 0  # Should be empty