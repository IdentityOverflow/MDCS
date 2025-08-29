"""
Unit tests for AI reflection safety mechanisms.

Tests the core safety systems that prevent infinite loops and ensure safe
self-modification behavior in advanced modules using the reflect() function.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from app.core.script_context import ScriptExecutionContext
from app.models import ModuleType, ExecutionContext


class TestReflectionSafety:
    """Test cases for reflection safety mechanisms."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.mock_db_session = Mock()
        self.base_context = ScriptExecutionContext(
            conversation_id="test-conv-123",
            persona_id="test-persona-456",
            db_session=self.mock_db_session
        )

    def test_reflection_depth_tracking_initialization(self):
        """Test that reflection depth is initialized to 0."""
        assert hasattr(self.base_context, 'reflection_depth')
        assert self.base_context.reflection_depth == 0

    def test_module_resolution_stack_initialization(self):
        """Test that module resolution stack is initialized empty."""
        assert hasattr(self.base_context, 'module_resolution_stack')
        assert self.base_context.module_resolution_stack == []

    def test_reflection_chain_initialization(self):
        """Test that reflection chain is initialized empty."""
        assert hasattr(self.base_context, 'reflection_chain')
        assert self.base_context.reflection_chain == []

    def test_can_reflect_basic_case(self):
        """Test can_reflect allows reflection in basic case."""
        # Should allow reflection when no constraints are active
        result = self.base_context.can_reflect("test_module", "POST_RESPONSE")
        assert result is True

    def test_can_reflect_blocks_at_max_depth(self):
        """Test can_reflect blocks reflection at maximum depth."""
        # Set reflection depth to maximum
        self.base_context.reflection_depth = 3
        
        result = self.base_context.can_reflect("test_module", "POST_RESPONSE")
        assert result is False

    def test_can_reflect_allows_under_max_depth(self):
        """Test can_reflect allows reflection under maximum depth."""
        # Set reflection depth below maximum
        self.base_context.reflection_depth = 2
        
        result = self.base_context.can_reflect("test_module", "POST_RESPONSE")
        assert result is True

    def test_can_reflect_blocks_direct_recursion(self):
        """Test can_reflect blocks direct module self-recursion during nested reflection."""
        # Add module to resolution stack
        self.base_context.module_resolution_stack = ["recursive_module"]
        # Set reflection depth > 0 to simulate nested reflection
        self.base_context.reflection_depth = 1
        
        # Should block the same module from reflecting during nested reflection
        result = self.base_context.can_reflect("recursive_module", "POST_RESPONSE")
        assert result is False

    def test_can_reflect_allows_cross_module_reflection(self):
        """Test can_reflect allows different modules to reflect."""
        # Add module A to resolution stack
        self.base_context.module_resolution_stack = ["module_a"]
        
        # Should allow module B to reflect
        result = self.base_context.can_reflect("module_b", "POST_RESPONSE")
        assert result is True

    def test_can_reflect_allows_custom_timing(self):
        """Test can_reflect allows CUSTOM timing modules to reflect."""
        result = self.base_context.can_reflect("test_module", "ON_DEMAND")
        assert result is True

    def test_can_reflect_blocks_nested_before_timing(self):
        """Test can_reflect blocks nested BEFORE timing reflections."""
        # Set reflection depth > 0 to simulate nesting
        self.base_context.reflection_depth = 1
        
        result = self.base_context.can_reflect("test_module", "IMMEDIATE")
        assert result is False

    def test_can_reflect_allows_first_level_before_timing(self):
        """Test can_reflect allows first-level BEFORE timing reflections."""
        # Reflection depth = 0 (no nesting)
        self.base_context.reflection_depth = 0
        
        result = self.base_context.can_reflect("test_module", "IMMEDIATE")
        assert result is True

    def test_can_reflect_always_allows_after_timing(self):
        """Test can_reflect always allows AFTER timing (most common use case)."""
        # Even with some depth, AFTER should be allowed
        self.base_context.reflection_depth = 2
        
        result = self.base_context.can_reflect("test_module", "POST_RESPONSE")
        assert result is True

    def test_can_reflect_allows_custom_timing(self):
        """Test can_reflect allows CUSTOM timing modules."""
        self.base_context.reflection_depth = 1
        
        result = self.base_context.can_reflect("test_module", "ON_DEMAND")
        assert result is True

    def test_enter_reflection_increments_depth(self):
        """Test entering reflection increments depth counter."""
        initial_depth = self.base_context.reflection_depth
        
        self.base_context.enter_reflection("test_module", "test instructions")
        
        assert self.base_context.reflection_depth == initial_depth + 1

    def test_enter_reflection_adds_to_chain(self):
        """Test entering reflection adds entry to reflection chain."""
        initial_chain_length = len(self.base_context.reflection_chain)
        
        self.base_context.enter_reflection("test_module", "test instructions")
        
        assert len(self.base_context.reflection_chain) == initial_chain_length + 1
        chain_entry = self.base_context.reflection_chain[-1]
        assert chain_entry["module_id"] == "test_module"
        assert chain_entry["instructions"] == "test instructions"
        assert "timestamp" in chain_entry

    def test_exit_reflection_decrements_depth(self):
        """Test exiting reflection decrements depth counter."""
        # Enter reflection first
        self.base_context.enter_reflection("test_module", "test instructions")
        depth_after_enter = self.base_context.reflection_depth
        
        self.base_context.exit_reflection()
        
        assert self.base_context.reflection_depth == depth_after_enter - 1

    def test_exit_reflection_prevents_negative_depth(self):
        """Test exiting reflection doesn't go below 0 depth."""
        # Ensure we start at 0
        assert self.base_context.reflection_depth == 0
        
        # Try to exit when already at 0
        self.base_context.exit_reflection()
        
        # Should still be 0, not negative
        assert self.base_context.reflection_depth == 0

    def test_add_module_to_resolution_stack(self):
        """Test adding module to resolution stack."""
        initial_stack = self.base_context.module_resolution_stack.copy()
        
        self.base_context.add_module_to_resolution_stack("new_module")
        
        assert "new_module" not in initial_stack
        assert "new_module" in self.base_context.module_resolution_stack

    def test_remove_module_from_resolution_stack(self):
        """Test removing module from resolution stack."""
        # Add module first
        self.base_context.add_module_to_resolution_stack("temp_module")
        assert "temp_module" in self.base_context.module_resolution_stack
        
        # Remove module
        self.base_context.remove_module_from_resolution_stack("temp_module")
        
        assert "temp_module" not in self.base_context.module_resolution_stack

    def test_remove_nonexistent_module_from_stack(self):
        """Test removing non-existent module from stack doesn't error."""
        # Should not raise exception
        self.base_context.remove_module_from_resolution_stack("nonexistent_module")
        
        # Stack should be unchanged
        assert isinstance(self.base_context.module_resolution_stack, list)

    def test_get_reflection_audit_trail(self):
        """Test getting reflection audit trail for debugging."""
        # Add some reflection entries
        self.base_context.enter_reflection("module_a", "first reflection")
        self.base_context.enter_reflection("module_b", "second reflection")
        
        audit_trail = self.base_context.get_reflection_audit_trail()
        
        assert len(audit_trail) == 2
        assert audit_trail[0]["module_id"] == "module_a"
        assert audit_trail[1]["module_id"] == "module_b"
        assert audit_trail[0]["instructions"] == "first reflection"

    def test_reflection_chain_max_length(self):
        """Test reflection chain doesn't grow indefinitely."""
        # Add many reflection entries
        for i in range(20):
            self.base_context.enter_reflection(f"module_{i}", f"instruction_{i}")
        
        # Should be limited to prevent memory issues
        assert len(self.base_context.reflection_chain) <= 10  # Reasonable limit

    def test_complex_safety_scenario(self):
        """Test complex scenario with multiple safety constraints."""
        # Set up complex state
        self.base_context.reflection_depth = 2
        self.base_context.module_resolution_stack = ["module_a", "module_b"]
        
        # Test various constraints
        assert self.base_context.can_reflect("module_a", "POST_RESPONSE") is False  # Direct recursion
        assert self.base_context.can_reflect("module_c", "POST_RESPONSE") is True   # Different module
        assert self.base_context.can_reflect("module_c", "IMMEDIATE") is False # Nested BEFORE
        assert self.base_context.can_reflect("module_c", "ON_DEMAND") is True  # Custom timing allowed

    def test_safety_with_edge_case_values(self):
        """Test safety mechanisms with edge case values."""
        # Test with None values
        result = self.base_context.can_reflect(None, "POST_RESPONSE")
        assert result is False  # Should handle None gracefully
        
        # Test with empty string
        result = self.base_context.can_reflect("", "POST_RESPONSE")
        assert result is False  # Should handle empty string

    def test_reflection_context_isolation(self):
        """Test that reflection context is properly isolated."""
        # This will be used when we implement context isolation
        # For now, verify the structure exists
        assert hasattr(self.base_context, 'conversation_id')
        assert hasattr(self.base_context, 'persona_id')
        assert hasattr(self.base_context, 'current_provider')
        assert hasattr(self.base_context, 'current_provider_settings')


class TestReflectionIntegrationSafety:
    """Integration tests for reflection safety in realistic scenarios."""

    def setup_method(self):
        """Set up integration test fixtures."""
        self.mock_db_session = Mock()
        
    def test_safe_after_timing_reflection_scenario(self):
        """Test safe AFTER timing reflection scenario."""
        context = ScriptExecutionContext(
            conversation_id="test-123",
            persona_id="persona-456", 
            db_session=self.mock_db_session
        )
        
        # Simulate AFTER timing module reflection (most common use case)
        assert context.can_reflect("response_analyzer", "POST_RESPONSE") is True
        
        # Add module to resolution stack (simulating module resolution)
        context.add_module_to_resolution_stack("response_analyzer")
        
        # Enter reflection
        context.enter_reflection("response_analyzer", "Analyze my response quality")
        
        # Should still allow other modules to reflect
        assert context.can_reflect("mood_detector", "POST_RESPONSE") is True
        
        # But not the same module (due to resolution stack)
        assert context.can_reflect("response_analyzer", "POST_RESPONSE") is False

    def test_cross_module_reflection_chain(self):
        """Test safe cross-module reflection chains."""
        context = ScriptExecutionContext(
            conversation_id="test-123",
            persona_id="persona-456",
            db_session=self.mock_db_session
        )
        
        # Module A starts reflecting
        context.add_module_to_resolution_stack("personality_adapter")
        assert context.can_reflect("mood_analyzer", "POST_RESPONSE") is True
        
        # Module A reflects using Module B - this should work
        # Add Module B to resolution stack to simulate it being resolved
        context.add_module_to_resolution_stack("mood_analyzer")
        context.enter_reflection("mood_analyzer", "What mood should I use?")
        
        # Now Module B is in a reflection, but can still reflect to Module C
        assert context.can_reflect("conversation_summarizer", "POST_RESPONSE") is True
        
        # But Module B cannot reflect back to itself (in resolution stack) or Module A (in resolution stack)
        assert context.can_reflect("mood_analyzer", "POST_RESPONSE") is False
        assert context.can_reflect("personality_adapter", "POST_RESPONSE") is False

    def test_reflection_depth_cascade_prevention(self):
        """Test prevention of excessive reflection depth cascades."""
        context = ScriptExecutionContext(
            conversation_id="test-123",
            persona_id="persona-456",
            db_session=self.mock_db_session
        )
        
        # Build up reflection depth to just under limit
        for i in range(2):
            context.enter_reflection(f"module_{i}", f"reflection {i}")
        
        # Should still allow one more level
        assert context.can_reflect("final_module", "POST_RESPONSE") is True
        
        # Enter final level
        context.enter_reflection("final_module", "final reflection")
        
        # Now should block any more reflections
        assert context.can_reflect("overflow_module", "POST_RESPONSE") is False