"""
Unit tests for the reflect() plugin function.

Tests the AI self-reflection capability with comprehensive safety mechanisms,
simplified signature, and proper integration with SystemPromptState tracking.
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
        
        # Add state-aware methods for the simplified reflect function
        self.mock_context.get_system_prompt_state = Mock()
        self.mock_context.get_current_execution_stage = Mock()
        
        # Return a simple system prompt by default
        self.mock_context.get_system_prompt_state.return_value = Mock()
        self.mock_context.get_system_prompt_state.return_value.get_prompt_for_stage.return_value = "Test system prompt for reflection"
        self.mock_context.get_current_execution_stage.return_value = 5

    def test_reflect_requires_script_context(self):
        """Test that reflect() requires script context for safety."""
        result = reflect("Test reflection")
        
        assert "Error: Reflection requires script context" in result

    def test_reflect_requires_instructions(self):
        """Test that reflect() requires instructions argument."""
        # This should now raise TypeError since instructions is required
        with pytest.raises(TypeError):
            reflect(_script_context=self.mock_context)

    def test_reflect_blocks_empty_instructions(self):
        """Test that reflect() blocks empty instructions."""
        result = reflect("", _script_context=self.mock_context)
        
        assert "Error: Reflection instructions must be a non-empty string" in result

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

    def test_reflect_with_invalid_instructions_type(self):
        """Test reflect() with non-string instructions."""
        result = reflect(123, _script_context=self.mock_context)
        
        assert "Error: Reflection instructions must be a non-empty string" in result

    def test_reflect_with_only_whitespace_instructions(self):
        """Test reflect() with whitespace-only instructions."""
        result = reflect("   \n\t   ", _script_context=self.mock_context)
        
        assert "Error: Reflection instructions must be a non-empty string" in result

    def test_reflect_no_provider_settings(self):
        """Test reflect() when no provider settings are available."""
        # Remove provider settings
        self.mock_context.current_provider_settings = {}
        
        result = reflect("Test reflection", _script_context=self.mock_context)
        
        assert "Error: No provider settings available" in result

    def test_reflect_uses_reasonable_defaults(self):
        """Test that reflect() uses reasonable defaults for chat controls."""
        with patch('app.plugins.ai_plugins._run_async_ai_call') as mock_ai_call:
            mock_ai_call.return_value = "Reflected response"
            
            reflect("Test reflection", _script_context=self.mock_context)
            
            # Verify reasonable defaults were used
            args, kwargs = mock_ai_call.call_args
            chat_request = args[1]
            chat_controls = chat_request.chat_controls
            
            assert chat_controls["temperature"] == 0.3  # Moderate for balanced reflection
            assert chat_controls["max_tokens"] == 200   # Reasonable default for reflections
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

    def test_reflect_requires_state_aware_system_prompt(self):
        """Test that reflect() requires state-aware system prompt to be available."""
        # Mock context without state methods (will fall back and fail gracefully)
        basic_context = Mock()
        basic_context.can_reflect.return_value = True
        basic_context.enter_reflection = Mock()
        basic_context.exit_reflection = Mock()
        basic_context.current_provider = "ollama"
        basic_context.current_provider_settings = {"host": "localhost", "model": "test"}
        basic_context.current_chat_controls = {}
        
        result = reflect("Test reflection", _script_context=basic_context)
        
        # Should fail gracefully when no state-aware prompt is available
        assert "Error: No system prompt state available for reflection" in result

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
        
        # Add state-aware methods for simplified reflect function
        context.get_system_prompt_state = Mock()
        context.get_current_execution_stage = Mock()
        context.get_system_prompt_state.return_value = Mock()
        context.get_system_prompt_state.return_value.get_prompt_for_stage.return_value = "You are a helpful AI assistant ready to provide quality responses."
        context.get_current_execution_stage.return_value = 5
        
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


class TestReflectWithSystemPromptState:
    """Test cases for reflect() integration with SystemPromptState tracking."""

    def setup_method(self):
        """Set up test fixtures with SystemPromptState integration."""
        self.mock_db_session = Mock()
        self.mock_context = Mock(spec=ScriptExecutionContext)
        
        # Base context setup
        self.mock_context.reflection_depth = 0
        self.mock_context.module_resolution_stack = []
        self.mock_context.current_provider = "ollama"
        self.mock_context.current_provider_settings = {
            "host": "http://localhost:11434",
            "model": "test-model"
        }
        self.mock_context.current_chat_controls = {
            "temperature": 0.1,
            "max_tokens": 1000
        }
        self.mock_context.can_reflect.return_value = True
        self.mock_context.enter_reflection = Mock()
        self.mock_context.exit_reflection = Mock()
        
        # Mock SystemPromptState
        from app.services.system_prompt_state import SystemPromptState
        self.mock_prompt_state = Mock(spec=SystemPromptState)
        self.mock_prompt_state.conversation_id = "test-conv"
        self.mock_prompt_state.persona_id = "test-persona"
        self.mock_prompt_state.original_template = "You are an AI assistant. @greeting"
        self.mock_prompt_state.stage1_resolved = "You are an AI assistant. Hello!"
        self.mock_prompt_state.stage2_resolved = "You are an AI assistant. Hello! Ready to help."
        self.mock_prompt_state.main_response_prompt = "You are an AI assistant. Hello! Ready to help."
        self.mock_prompt_state.execution_stages = [1, 2]
        self.mock_prompt_state.resolved_modules = ["greeting"]
        
        # Mock get_prompt_for_stage method
        def mock_get_prompt_for_stage(stage):
            if stage == 2:
                return self.mock_prompt_state.stage1_resolved
            elif stage == 5:
                return f"{self.mock_prompt_state.main_response_prompt}\n\nCurrent context:\nresponse_quality:\n  8/10 - well structured"
            else:
                return self.mock_prompt_state.original_template
        
        self.mock_prompt_state.get_prompt_for_stage.side_effect = mock_get_prompt_for_stage
        
        # Add state-aware methods to context
        self.mock_context.get_system_prompt_state = Mock()
        self.mock_context.get_current_execution_stage = Mock()

    @patch('app.plugins.ai_plugins._run_async_ai_call')
    def test_reflect_uses_stage2_prompt_when_available(self, mock_ai_call):
        """Test reflect() uses Stage 2 resolved prompt when SystemPromptState is available."""
        mock_ai_call.return_value = "Quality assessment: The response demonstrates good structure"
        
        # Make SystemPromptState available during Stage 2 (IMMEDIATE AI)
        self.mock_context.get_system_prompt_state.return_value = self.mock_prompt_state
        self.mock_context.get_current_execution_stage.return_value = 2
        
        result = reflect("Rate the quality of my response preparation", _script_context=self.mock_context)
        
        assert "Quality assessment" in result
        
        # Verify the AI call used the Stage 1 resolved prompt (which Stage 2 uses)
        call_args = mock_ai_call.call_args[0]
        chat_request = call_args[1]
        
        # The system prompt should be the stage-appropriate resolved prompt, not the fallback
        assert chat_request.system_prompt == "You are an AI assistant. Hello!"
        assert "self-reflection" not in chat_request.system_prompt  # Not the fallback prompt

    @patch('app.plugins.ai_plugins._run_async_ai_call')
    def test_reflect_uses_stage5_prompt_with_context(self, mock_ai_call):
        """Test reflect() uses Stage 5 prompt with accumulated POST_RESPONSE context."""
        mock_ai_call.return_value = "Post-response reflection: Based on the accumulated context, I can provide deeper analysis"
        
        # Mock POST_RESPONSE Stage 5 context with accumulated variables
        self.mock_context.get_system_prompt_state.return_value = self.mock_prompt_state
        self.mock_context.get_current_execution_stage.return_value = 5
        
        result = reflect("Reflect on the overall conversation quality", _script_context=self.mock_context)
        
        assert "deeper analysis" in result
        
        # Verify the AI call used Stage 5 prompt with accumulated context
        call_args = mock_ai_call.call_args[0]
        chat_request = call_args[1]
        
        expected_prompt = "You are an AI assistant. Hello! Ready to help.\n\nCurrent context:\nresponse_quality:\n  8/10 - well structured"
        assert chat_request.system_prompt == expected_prompt
        assert "Current context:" in chat_request.system_prompt

    @patch('app.plugins.ai_plugins._run_async_ai_call')
    def test_reflect_fails_gracefully_without_state_tracking(self, mock_ai_call):
        """Test reflect() fails gracefully when SystemPromptState is not available."""
        # No SystemPromptState available
        self.mock_context.get_system_prompt_state.return_value = None
        
        result = reflect("Basic reflection without state", _script_context=self.mock_context)
        
        # Should fail gracefully when no state is available
        assert "Error: No system prompt state available for reflection" in result
        
        # Should not call AI since there's no state-aware system prompt
        mock_ai_call.assert_not_called()

    @patch('app.plugins.ai_plugins._run_async_ai_call')
    def test_reflect_handles_state_access_exception(self, mock_ai_call):
        """Test reflect() handles SystemPromptState access exceptions gracefully."""
        # Mock exception in state access
        self.mock_context.get_system_prompt_state.side_effect = Exception("State access error")
        
        result = reflect("Should handle state access error", _script_context=self.mock_context)
        
        # Should fail gracefully when state access throws exception
        assert "Error: No system prompt state available for reflection" in result
        
        # Should not call AI since state access failed
        mock_ai_call.assert_not_called()

    @patch('app.plugins.ai_plugins._run_async_ai_call')
    def test_reflect_uses_instructions_directly_as_message(self, mock_ai_call):
        """Test reflect() uses instructions directly as user message."""
        mock_ai_call.return_value = "Direct instruction processing"
        
        # Make state available
        self.mock_context.get_system_prompt_state.return_value = self.mock_prompt_state
        self.mock_context.get_current_execution_stage.return_value = 5
        
        result = reflect(
            "Analyze the effectiveness of my last response and suggest specific improvements",
            _script_context=self.mock_context
        )
        
        assert "Direct instruction processing" in result
        
        # Verify instructions are used directly as message
        call_args = mock_ai_call.call_args[0]
        chat_request = call_args[1]
        
        # Should use instructions directly, no formatting
        assert chat_request.message == "Analyze the effectiveness of my last response and suggest specific improvements"
        
        # Should use state-aware system prompt
        expected_prompt = "You are an AI assistant. Hello! Ready to help.\n\nCurrent context:\nresponse_quality:\n  8/10 - well structured"
        assert chat_request.system_prompt == expected_prompt

    def test_reflect_state_integration_architecture(self):
        """Test the architectural integration points for SystemPromptState awareness."""
        # Verify the integration methods exist (architectural test)
        required_methods = [
            'get_system_prompt_state',
            'get_current_execution_stage'
        ]
        
        for method_name in required_methods:
            assert hasattr(self.mock_context, method_name), f"Context should have {method_name} method for state awareness"
        
        # Verify SystemPromptState has required method
        assert hasattr(self.mock_prompt_state, 'get_prompt_for_stage'), "SystemPromptState should have get_prompt_for_stage method"
        
        # Integration should be optional (loose coupling)
        self.mock_context.get_system_prompt_state.return_value = None
        
        # Should fail gracefully when state is unavailable (by design)
        try:
            result = reflect("Test without state", _script_context=self.mock_context)
            # Should return error message, not raise exception
            assert "Error: No system prompt state available for reflection" in result
        except Exception as e:
            pytest.fail(f"reflect() should fail gracefully with error message, but raised: {e}")

    @patch('app.plugins.ai_plugins._run_async_ai_call')
    def test_reflect_unknown_execution_stage_uses_fallback(self, mock_ai_call):
        """Test reflect() uses fallback for unknown execution stages."""
        mock_ai_call.return_value = "Fallback prompt used for unknown stage"
        
        # Mock state but unknown stage
        self.mock_context.get_system_prompt_state.return_value = self.mock_prompt_state
        self.mock_context.get_current_execution_stage.return_value = 99  # Unknown stage
        
        result = reflect("Test unknown stage", _script_context=self.mock_context)
        
        assert "Fallback prompt" in result
        
        # Should use the original template as fallback for unknown stages
        call_args = mock_ai_call.call_args[0]
        chat_request = call_args[1]
        
        assert chat_request.system_prompt == self.mock_prompt_state.original_template