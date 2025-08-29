"""
Unit tests for the reflect() plugin function.

Tests the AI self-reflection capability with comprehensive safety mechanisms,
argument parsing, and proper integration with the script execution context.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from app.plugins.ai_plugins import reflect
from app.core.script_context import ScriptExecutionContext
from app.models import ExecutionContext


class TestReflectPlugin:
    """Test cases for the reflect() plugin function."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.mock_db_session = Mock()
        self.mock_context = Mock(spec=ScriptExecutionContext)
        
        # Set up mock context with reflection safety attributes
        self.mock_context.reflection_depth = 0
        self.mock_context.module_resolution_stack = []
        self.mock_context.current_provider = "ollama"
        self.mock_context.current_provider_settings = {
            "host": "http://localhost:11434",
            "model": "tinydolphin"
        }
        self.mock_context.current_chat_controls = {}
        
        # Mock safety methods
        self.mock_context.can_reflect.return_value = True
        self.mock_context.enter_reflection = Mock()
        self.mock_context.exit_reflection = Mock()
        self.mock_context.get_reflection_audit_trail.return_value = []

    def test_reflect_requires_script_context(self):
        """Test that reflect() requires script context for safety."""
        result = reflect("Test reflection")
        
        assert "Error: Reflection requires script context" in result

    def test_reflect_requires_instructions(self):
        """Test that reflect() requires non-empty instructions."""
        result = reflect(_script_context=self.mock_context)
        
        assert "Error: No reflection instructions provided" in result

    def test_reflect_blocks_empty_instructions(self):
        """Test that reflect() blocks empty instructions."""
        result = reflect("", _script_context=self.mock_context)
        
        assert "Error: Reflection instructions cannot be empty" in result

    def test_reflect_respects_safety_check(self):
        """Test that reflect() respects safety check from can_reflect()."""
        # Make safety check fail
        self.mock_context.can_reflect.return_value = False
        
        result = reflect("Test reflection", _script_context=self.mock_context)
        
        assert "Reflection blocked for safety" in result
        self.mock_context.can_reflect.assert_called_once()

    def test_reflect_single_argument_signature(self):
        """Test reflect() with single argument (instructions only)."""
        with patch('app.plugins.ai_plugins._run_async_ai_call') as mock_ai_call:
            mock_ai_call.return_value = "I reflected on the instructions and found them thoughtful."
            
            result = reflect("Analyze my thinking patterns", _script_context=self.mock_context)
            
            assert "I reflected on the instructions" in result
            self.mock_context.enter_reflection.assert_called_once()
            self.mock_context.exit_reflection.assert_called_once()

    def test_reflect_two_argument_signature(self):
        """Test reflect() with instructions and input data."""
        with patch('app.plugins.ai_plugins._run_async_ai_call') as mock_ai_call:
            mock_ai_call.return_value = "After analyzing the input, I see patterns."
            
            result = reflect(
                "What patterns do you see?", 
                "Some input data here",
                _script_context=self.mock_context
            )
            
            assert "After analyzing the input" in result
            # Verify AI call was made with both instructions and input
            mock_ai_call.assert_called_once()
            args, kwargs = mock_ai_call.call_args
            chat_request = args[1]  # Second argument is ChatRequest
            assert "Context/Input:" in chat_request.message
            assert "Some input data here" in chat_request.message

    def test_reflect_four_argument_signature(self):
        """Test reflect() with provider, model, instructions, and input."""
        with patch('app.plugins.ai_plugins._run_async_ai_call') as mock_ai_call:
            mock_ai_call.return_value = "Reflection using specific provider."
            
            result = reflect(
                "openai",
                "gpt-4", 
                "Deep analysis request",
                "Complex input data",
                _script_context=self.mock_context
            )
            
            assert "Reflection using specific provider" in result
            # Verify specific provider was used
            args, kwargs = mock_ai_call.call_args
            provider = args[0]  # First argument is provider
            assert provider == "openai"

    def test_reflect_invalid_argument_count(self):
        """Test reflect() with invalid number of arguments."""
        result = reflect("a", "b", "c", "d", "e", _script_context=self.mock_context)
        
        assert "Error: Invalid number of arguments" in result

    def test_reflect_unsupported_provider(self):
        """Test reflect() with unsupported provider."""
        result = reflect(
            "unsupported_provider", 
            "model", 
            "instructions",
            _script_context=self.mock_context
        )
        
        assert "Error: Unsupported provider 'unsupported_provider'" in result

    def test_reflect_no_provider_settings(self):
        """Test reflect() when no provider settings are available."""
        # Remove provider settings
        self.mock_context.current_provider_settings = {}
        
        result = reflect("Test reflection", _script_context=self.mock_context)
        
        assert "Error: No provider settings available" in result

    def test_reflect_uses_conservative_defaults(self):
        """Test that reflect() uses conservative defaults for chat controls."""
        with patch('app.plugins.ai_plugins._run_async_ai_call') as mock_ai_call:
            mock_ai_call.return_value = "Reflected response"
            
            reflect("Test reflection", _script_context=self.mock_context)
            
            # Verify conservative defaults were used
            args, kwargs = mock_ai_call.call_args
            chat_request = args[1]
            chat_controls = chat_request.chat_controls
            
            assert chat_controls["temperature"] == 0.2  # Lower than default
            assert chat_controls["max_tokens"] == 150   # Concise limit for reflections
            assert chat_controls["stream"] is False     # Always non-streaming

    def test_reflect_keyword_arguments_override_defaults(self):
        """Test that keyword arguments can override default chat controls."""
        with patch('app.plugins.ai_plugins._run_async_ai_call') as mock_ai_call:
            mock_ai_call.return_value = "Creative reflection"
            
            reflect(
                "Creative thinking task", 
                _script_context=self.mock_context,
                temperature=0.8,
                max_tokens=1200
            )
            
            # Verify overrides were applied
            args, kwargs = mock_ai_call.call_args
            chat_request = args[1]
            chat_controls = chat_request.chat_controls
            
            assert chat_controls["temperature"] == 0.8
            assert chat_controls["max_tokens"] == 1200

    def test_reflect_uses_minimal_system_prompt(self):
        """Test that reflect() uses a minimal system prompt to avoid recursion."""
        with patch('app.plugins.ai_plugins._run_async_ai_call') as mock_ai_call:
            mock_ai_call.return_value = "Simple reflection"
            
            reflect("Test reflection", _script_context=self.mock_context)
            
            # Verify minimal system prompt
            args, kwargs = mock_ai_call.call_args
            chat_request = args[1]
            system_prompt = chat_request.system_prompt
            
            assert "self-reflection" in system_prompt.lower()
            assert len(system_prompt) < 200  # Should be brief
            # Should not contain module references
            assert "@" not in system_prompt

    def test_reflect_calls_safety_methods_correctly(self):
        """Test that reflect() calls all safety methods in correct order."""
        with patch('app.plugins.ai_plugins._run_async_ai_call') as mock_ai_call:
            mock_ai_call.return_value = "Safe reflection"
            
            reflect("Safe test", _script_context=self.mock_context)
            
            # Verify safety methods were called in order
            self.mock_context.can_reflect.assert_called_once()
            self.mock_context.enter_reflection.assert_called_once()
            self.mock_context.exit_reflection.assert_called_once()
            
            # Verify enter_reflection was called with correct parameters
            enter_args = self.mock_context.enter_reflection.call_args[0]
            assert enter_args[1] == "Safe test"  # Truncated instructions

    def test_reflect_exits_on_exception(self):
        """Test that reflect() always calls exit_reflection even on exception."""
        with patch('app.plugins.ai_plugins._run_async_ai_call') as mock_ai_call:
            mock_ai_call.side_effect = Exception("AI call failed")
            
            result = reflect("Test reflection", _script_context=self.mock_context)
            
            assert "Error during reflection" in result
            # Should call exit_reflection (only once in the finally block)
            self.mock_context.exit_reflection.assert_called()

    def test_reflect_truncates_long_instructions_in_logging(self):
        """Test that long instructions are truncated for logging."""
        long_instructions = "A" * 200  # 200 character instructions
        
        with patch('app.plugins.ai_plugins._run_async_ai_call') as mock_ai_call:
            mock_ai_call.return_value = "Reflected on long instructions"
            
            reflect(long_instructions, _script_context=self.mock_context)
            
            # Verify truncation in enter_reflection call
            enter_args = self.mock_context.enter_reflection.call_args[0]
            logged_instructions = enter_args[1]
            assert len(logged_instructions) <= 100

    def test_reflect_handles_missing_context_attributes_gracefully(self):
        """Test that reflect() handles missing context attributes gracefully."""
        # Create minimal context without some attributes  
        minimal_context = Mock()
        minimal_context.can_reflect.return_value = True
        minimal_context.enter_reflection = Mock()
        minimal_context.exit_reflection = Mock()
        # Set a valid provider but no provider settings
        minimal_context.current_provider = "ollama"
        minimal_context.current_provider_settings = None  # Explicitly None
        minimal_context.current_chat_controls = None      # Explicitly None
        
        # Missing provider settings should cause graceful failure
        result = reflect("Test reflection", _script_context=minimal_context)
        
        assert "Error: No provider settings available" in result
        # Should still call safety methods
        minimal_context.exit_reflection.assert_called()


class TestReflectIntegrationScenarios:
    """Integration tests for reflect() in realistic scenarios."""

    def setup_method(self):
        """Set up integration test fixtures."""
        self.mock_db_session = Mock()
        
    def test_after_timing_reflection_scenario(self):
        """Test realistic AFTER timing reflection scenario."""
        context = Mock(spec=ScriptExecutionContext)
        context.reflection_depth = 0
        context.module_resolution_stack = []
        context.can_reflect.return_value = True
        context.enter_reflection = Mock()
        context.exit_reflection = Mock()
        context.current_provider = "ollama"
        context.current_provider_settings = {"host": "http://localhost:11434", "model": "dolphin"}
        context.current_chat_controls = {"temperature": 0.7}
        
        with patch('app.plugins.ai_plugins._run_async_ai_call') as mock_ai_call:
            mock_ai_call.return_value = "I rate my previous response 8/10. It was clear but could be more concise."
            
            result = reflect(
                "Rate my last response quality from 1-10 and suggest improvements",
                _script_context=context
            )
            
            assert "8/10" in result
            assert "concise" in result
            context.can_reflect.assert_called_once()

    def test_blocked_reflection_provides_audit_info(self):
        """Test that blocked reflection provides useful audit information."""
        context = Mock(spec=ScriptExecutionContext)
        context.reflection_depth = 3  # At maximum depth
        context.module_resolution_stack = ["self_analyzer", "mood_detector"]
        context.can_reflect.return_value = False
        context.get_reflection_audit_trail.return_value = [
            {"module_id": "self_analyzer", "instructions": "analyzing", "depth": 1},
            {"module_id": "mood_detector", "instructions": "mood check", "depth": 2}
        ]
        
        result = reflect("Attempt deep reflection", _script_context=context)
        
        assert "Reflection blocked for safety" in result
        assert "current depth 3" in result
        assert "self_analyzer" in result or "mood_detector" in result