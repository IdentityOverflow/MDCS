"""
Integration tests for AI reflection system.

Tests the core reflection safety mechanisms and integration points
with focused, realistic scenarios.
"""

import pytest
from unittest.mock import Mock, patch
from app.services.module_resolver import ModuleResolver
from app.models import Module, ModuleType, ExecutionTiming
from app.core.script_context import ScriptExecutionContext
from app.plugins.ai_plugins import reflect


class TestReflectionIntegration:
    """Integration tests for the complete reflection system."""

    def setup_method(self):
        """Set up integration test fixtures."""
        self.mock_db_session = Mock()

    def test_reflect_function_direct_integration(self):
        """Test reflect() function works with proper context integration."""
        # Create a properly configured context
        context = ScriptExecutionContext(
            conversation_id="test-123",
            persona_id="persona-456",
            db_session=self.mock_db_session
        )
        
        # Set up provider settings for reflection
        context.current_provider = "ollama"
        context.current_provider_settings = {
            "host": "http://localhost:11434",
            "model": "tinydolphin"
        }
        context.current_chat_controls = {}  # Start with empty to see defaults
        
        with patch('app.plugins.ai_plugins._run_async_ai_call') as mock_ai_call:
            mock_ai_call.return_value = "I think this is a thoughtful question that deserves careful consideration."
            
            # Test basic reflection call
            result = reflect(
                "What are your thoughts on this conversation?",
                _script_context=context
            )
            
            assert "thoughtful question" in result
            assert "careful consideration" in result
            
            # Verify AI call was made with conservative defaults
            mock_ai_call.assert_called_once()
            args, kwargs = mock_ai_call.call_args
            chat_request = args[1]
            assert chat_request.chat_controls["temperature"] == 0.2  # Conservative default
            assert "Reflect on the following" in chat_request.message

    def test_reflection_safety_blocks_recursion(self):
        """Test that reflection safety correctly blocks recursive calls."""
        context = ScriptExecutionContext(
            conversation_id="test-123",
            persona_id="persona-456",
            db_session=self.mock_db_session
        )
        
        # Set up provider settings
        context.current_provider = "ollama"
        context.current_provider_settings = {"host": "http://localhost:11434", "model": "dolphin"}
        context.current_chat_controls = {}
        
        # Add current module to resolution stack and set reflection depth > 0 (simulating nested self-recursion)
        context.module_resolution_stack = ["self_analyzer"]
        context.current_module_id = "self_analyzer"
        context.current_timing = ExecutionTiming.AFTER
        context.reflection_depth = 1  # Simulate being in a nested reflection
        
        # Test that nested reflection is blocked
        result = reflect(
            "Analyze my own analysis recursively",
            _script_context=context
        )
        
        assert "Reflection blocked for safety" in result
        assert "self_analyzer" in result

    def test_reflection_cross_module_allowed(self):
        """Test that cross-module reflection is allowed."""
        context = ScriptExecutionContext(
            conversation_id="test-123",
            persona_id="persona-456",
            db_session=self.mock_db_session
        )
        
        # Set up provider settings
        context.current_provider = "ollama"
        context.current_provider_settings = {"host": "http://localhost:11434", "model": "dolphin"}
        context.current_chat_controls = {}
        
        # Module A is in resolution stack, but we're reflecting as Module B
        context.module_resolution_stack = ["personality_adapter"]
        context.current_module_id = "mood_analyzer"  # Different module
        context.current_timing = ExecutionTiming.AFTER
        
        with patch('app.plugins.ai_plugins._run_async_ai_call') as mock_ai_call:
            mock_ai_call.return_value = "Use a warm, encouraging tone"
            
            # Test cross-module reflection (allowed)
            result = reflect(
                "What emotional tone should I use?",
                _script_context=context
            )
            
            assert "warm, encouraging tone" in result
            mock_ai_call.assert_called_once()

    def test_reflection_depth_limiting_integration(self):
        """Test reflection depth limiting works in practice."""
        context = ScriptExecutionContext(
            conversation_id="test-123",
            persona_id="persona-456", 
            db_session=self.mock_db_session
        )
        
        # Set up provider settings
        context.current_provider = "ollama"
        context.current_provider_settings = {"host": "http://localhost:11434", "model": "dolphin"}
        context.current_chat_controls = {}
        
        # Set reflection depth to maximum
        context.reflection_depth = 3
        context.current_module_id = "deep_thinker"
        context.current_timing = ExecutionTiming.AFTER
        
        # Test that reflection is blocked at max depth
        result = reflect(
            "Think even deeper about this",
            _script_context=context
        )
        
        assert "Reflection blocked for safety" in result
        assert "current depth 3" in result

    def test_reflection_audit_trail_tracking(self):
        """Test that reflection audit trail is properly maintained."""
        context = ScriptExecutionContext(
            conversation_id="test-123",
            persona_id="persona-456",
            db_session=self.mock_db_session
        )
        
        # Test building reflection chain
        context.enter_reflection("module_a", "First reflection")
        context.enter_reflection("module_b", "Second reflection")
        
        audit_trail = context.get_reflection_audit_trail()
        
        assert len(audit_trail) == 2
        assert audit_trail[0]["module_id"] == "module_a"
        assert audit_trail[1]["module_id"] == "module_b"
        assert audit_trail[0]["depth"] == 1
        assert audit_trail[1]["depth"] == 2
        assert "timestamp" in audit_trail[0]
        assert "timestamp" in audit_trail[1]

    def test_module_resolution_stack_integration(self):
        """Test that module resolution stack is properly integrated with context."""
        context = ScriptExecutionContext(
            conversation_id="test-123",
            persona_id="persona-456", 
            db_session=self.mock_db_session
        )
        
        # Test that resolver stack syncs with context
        resolver_stack = {"module_a", "module_b"}
        context.module_resolution_stack = list(resolver_stack)
        
        # Test safety checks work with the stack
        assert context.can_reflect("module_c", ExecutionTiming.AFTER) is True   # Different module
        
        # At depth 0, modules can reflect during their own execution
        assert context.can_reflect("module_a", ExecutionTiming.AFTER) is True  # Same module but depth 0
        assert context.can_reflect("module_b", ExecutionTiming.AFTER) is True  # Same module but depth 0
        
        # At depth > 0, same modules should be blocked
        context.reflection_depth = 1
        assert context.can_reflect("module_a", ExecutionTiming.AFTER) is False  # Same module at depth > 0
        assert context.can_reflect("module_b", ExecutionTiming.AFTER) is False  # Same module at depth > 0


class TestReflectionSafetyScenarios:
    """Test realistic reflection safety scenarios."""

    def setup_method(self):
        """Set up safety scenario tests."""
        self.mock_db_session = Mock()

    def test_nested_before_timing_blocked(self):
        """Test that nested BEFORE timing reflections are blocked."""
        context = ScriptExecutionContext(
            conversation_id="test-123",
            persona_id="persona-456",
            db_session=self.mock_db_session
        )
        
        # Simulate being in a reflection already
        context.reflection_depth = 1
        
        # BEFORE timing should be blocked when nested
        assert context.can_reflect("some_module", ExecutionTiming.BEFORE) is False
        # But AFTER and CUSTOM should still be allowed
        assert context.can_reflect("some_module", ExecutionTiming.AFTER) is True
        assert context.can_reflect("some_module", ExecutionTiming.CUSTOM) is True

    def test_reflection_chain_length_limiting(self):
        """Test that reflection chains don't grow indefinitely."""
        context = ScriptExecutionContext(
            conversation_id="test-123", 
            persona_id="persona-456",
            db_session=self.mock_db_session
        )
        
        # Add many reflections to test limiting
        for i in range(15):
            context.enter_reflection(f"module_{i}", f"reflection_{i}")
        
        # Should be limited to MAX_REFLECTION_CHAIN_LENGTH (10)
        chain = context.get_reflection_audit_trail()
        assert len(chain) <= 10
        
        # Should keep the most recent entries
        assert chain[-1]["module_id"] == "module_14"

    def test_complex_safety_scenario_integration(self):
        """Test complex scenario with multiple safety constraints active."""
        context = ScriptExecutionContext(
            conversation_id="test-123",
            persona_id="persona-456",
            db_session=self.mock_db_session
        )
        
        # Set up complex state
        context.reflection_depth = 2
        context.module_resolution_stack = ["module_a", "module_b"]
        
        # Test comprehensive safety checks
        test_cases = [
            ("module_a", ExecutionTiming.AFTER, False, "Direct recursion"),
            ("module_c", ExecutionTiming.AFTER, True, "Different module, AFTER timing"),
            ("module_c", ExecutionTiming.BEFORE, False, "Nested BEFORE timing"),
            ("module_c", ExecutionTiming.CUSTOM, True, "Different module, CUSTOM timing"),
        ]
        
        for module_id, timing, expected, reason in test_cases:
            result = context.can_reflect(module_id, timing)
            assert result == expected, f"Failed for {reason}: {module_id} with {timing}"