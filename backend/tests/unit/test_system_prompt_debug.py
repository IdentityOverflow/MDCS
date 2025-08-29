"""
Unit tests for SystemPromptState debugging and inspection utilities.

Tests the debugging tools that help developers understand and troubleshoot
the system prompt evolution through the execution pipeline.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock

from app.services.system_prompt_state import SystemPromptState, ModuleResolutionWarning
from app.services.system_prompt_debug import (
    SystemPromptInspector,
    inspect_state,
    compare_states,
    extract_debug_json,
    debug_prompt_state
)


class TestSystemPromptInspector:
    """Test cases for SystemPromptInspector class."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.inspector = SystemPromptInspector()
        
        # Create a sample SystemPromptState for testing
        self.sample_state = SystemPromptState(
            conversation_id="test-conv-123",
            persona_id="test-persona-456",
            execution_timestamp=datetime.now(timezone.utc),
            original_template="You are an AI assistant. @greeting @context",
            stage1_resolved="You are an AI assistant. Hello! Background context loaded.",
            stage2_resolved="You are an AI assistant. Hello! Background context loaded. Ready to assist with full context awareness.",
            main_response_prompt="You are an AI assistant. Hello! Background context loaded. Ready to assist with full context awareness.",
            stage4_context={"conversation_summary": "User greeting interaction"},
            stage5_context={"response_quality": "8/10 - clear and helpful"},
            resolved_modules=["greeting", "context", "summary_module", "quality_assessor"],
            execution_stages=[1, 2, 4, 5],
            stage_timings={1: 0.05, 2: 0.15, 4: 0.03, 5: 0.22},
            total_execution_time=0.45,
            variables_by_stage={
                4: {"summary_module": {"conversation_summary": "User greeting interaction"}},
                5: {"quality_assessor": {"response_quality": "8/10 - clear and helpful"}}
            }
        )
        
        # Add a warning for testing
        warning = ModuleResolutionWarning(
            module_name="missing_module",
            warning_type="module_not_found", 
            message="Module 'missing_module' not found in registry",
            stage=1
        )
        self.sample_state.warnings.append(warning)
    
    def test_format_state_summary(self):
        """Test formatting basic state summary."""
        summary = self.inspector.format_state_summary(self.sample_state)
        
        # Check key sections are present
        assert "System Prompt State Summary" in summary
        assert "test-conv-123" in summary
        assert "test-persona-456" in summary
        assert "Prompt Evolution:" in summary
        assert "Execution Info:" in summary
        assert "0.450s" in summary  # Total execution time
        assert "greeting, context, summary_module" in summary  # Truncated modules list
        assert "POST_RESPONSE Context:" in summary
    
    def test_format_detailed_inspection(self):
        """Test formatting detailed inspection report."""
        detailed = self.inspector.format_detailed_inspection(self.sample_state)
        
        # Check comprehensive sections are present
        assert "Detailed SystemPromptState Inspection" in detailed
        assert "Full Prompt Evolution:" in detailed
        assert "Execution Metadata:" in detailed
        assert "Performance Analysis:" in detailed
        assert "Warnings and Issues:" in detailed
        assert "POST_RESPONSE Variables:" in detailed
        
        # Check specific content
        assert "You are an AI assistant. @greeting @context" in detailed  # Original
        assert "Ready to assist with full context awareness" in detailed  # Stage 2
        assert "Stage 1 (Simple + IMMEDIATE Non-AI): 0.050s" in detailed  # Timing
        assert "missing_module" in detailed  # Warning
        assert "response_quality" in detailed  # Stage 5 context
    
    def test_compare_states(self):
        """Test comparing two different states."""
        # Create a second state with some differences
        state2 = SystemPromptState(
            conversation_id="test-conv-124",
            persona_id="test-persona-456",
            execution_timestamp=datetime.now(timezone.utc),
            original_template="You are an AI assistant. @greeting",
            stage1_resolved="You are an AI assistant. Hi there!",
            resolved_modules=["greeting", "mood_detector"],  # Different modules
            execution_stages=[1, 2],  # Different stages
            stage_timings={1: 0.03, 2: 0.12},
            total_execution_time=0.15
        )
        
        comparison = self.inspector.compare_states(self.sample_state, state2)
        
        # Check comparison sections
        assert "SystemPromptState Comparison" in comparison
        assert "Execution Stages:" in comparison
        assert "Resolved Modules:" in comparison
        assert "Performance:" in comparison
        
        # Check specific comparisons
        assert "[1, 2, 4, 5]" in comparison and "[1, 2]" in comparison  # Stage difference
        assert "Added: ['mood_detector']" in comparison  # Module changes
        assert "0.300s" in comparison  # Performance difference (0.45 - 0.15)
    
    def test_extract_debug_data(self):
        """Test extracting structured debug data."""
        debug_data = self.inspector.extract_debug_data(self.sample_state)
        
        # Check structure
        assert isinstance(debug_data, dict)
        assert debug_data["conversation_id"] == "test-conv-123"
        assert debug_data["persona_id"] == "test-persona-456"
        assert debug_data["total_execution_time"] == 0.45
        
        # Check nested structures
        assert "prompt_evolution" in debug_data
        assert debug_data["prompt_evolution"]["original"] == "You are an AI assistant. @greeting @context"
        
        assert "execution_metadata" in debug_data
        assert debug_data["execution_metadata"]["stages_executed"] == [1, 2, 4, 5]
        assert debug_data["execution_metadata"]["resolved_modules"] == ["greeting", "context", "summary_module", "quality_assessor"]
        
        assert "performance_metrics" in debug_data
        assert debug_data["performance_metrics"]["total_time"] == 0.45
        
        assert "warnings" in debug_data
        assert len(debug_data["warnings"]) == 1
        assert debug_data["warnings"][0]["module_name"] == "missing_module"
    
    def test_text_truncation(self):
        """Test text truncation utility."""
        # Test normal text
        result = self.inspector._truncate_text("This is a normal text", 50)
        assert result == "This is a normal text"
        
        # Test long text
        long_text = "This is a very long text that should be truncated because it exceeds the maximum length"
        result = self.inspector._truncate_text(long_text, 30)
        assert len(result) == 30
        assert result.endswith("...")
        
        # Test empty text
        result = self.inspector._truncate_text("", 50)
        assert result == "(empty)"
        
        # Test None
        result = self.inspector._truncate_text(None, 50)
        assert result == "(empty)"


class TestConvenienceFunctions:
    """Test cases for convenience functions."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.sample_state = SystemPromptState(
            conversation_id="test-conv",
            persona_id="test-persona",
            execution_timestamp=datetime.now(timezone.utc),
            original_template="Simple template",
            stage1_resolved="Simple resolved",
            resolved_modules=["simple_module"],
            execution_stages=[1],
            stage_timings={1: 0.02},
            total_execution_time=0.02
        )
    
    def test_inspect_state_basic(self):
        """Test basic state inspection convenience function."""
        result = inspect_state(self.sample_state, detailed=False)
        
        assert "System Prompt State Summary" in result
        assert "test-conv" in result
        assert "Simple template" in result
    
    def test_inspect_state_detailed(self):
        """Test detailed state inspection convenience function."""
        result = inspect_state(self.sample_state, detailed=True)
        
        assert "Detailed SystemPromptState Inspection" in result
        assert "Full Prompt Evolution:" in result
    
    def test_extract_debug_json(self):
        """Test JSON debug data extraction."""
        json_str = extract_debug_json(self.sample_state)
        
        # Should be valid JSON
        import json
        data = json.loads(json_str)
        
        assert data["conversation_id"] == "test-conv"
        assert data["persona_id"] == "test-persona"
        assert "prompt_evolution" in data
        assert "performance_metrics" in data
    
    def test_compare_states_convenience(self):
        """Test states comparison convenience function."""
        state2 = SystemPromptState(
            conversation_id="test-conv-2",
            persona_id="test-persona",
            execution_timestamp=datetime.now(timezone.utc),
            original_template="Different template",
            resolved_modules=["different_module"],
            execution_stages=[1, 2],
            stage_timings={1: 0.01, 2: 0.05},
            total_execution_time=0.06
        )
        
        comparison = compare_states(self.sample_state, state2)
        
        assert "SystemPromptState Comparison" in comparison
        assert "test-conv" in comparison
        assert "test-conv-2" in comparison


class TestDebugPluginFunction:
    """Test cases for debug_prompt_state plugin function."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.mock_context = Mock()
        self.sample_state = SystemPromptState(
            conversation_id="plugin-test",
            persona_id="test-persona",
            execution_timestamp=datetime.now(timezone.utc),
            original_template="Plugin test template",
            resolved_modules=["test_module"],
            execution_stages=[1],
            stage_timings={1: 0.01},
            total_execution_time=0.01
        )
    
    def test_debug_prompt_state_without_context(self):
        """Test debug plugin function without script context."""
        result = debug_prompt_state()
        
        assert "Error: debug_prompt_state requires script context" in result
    
    def test_debug_prompt_state_without_state_methods(self):
        """Test debug plugin function with context lacking state methods."""
        basic_context = Mock()
        # Don't add get_system_prompt_state method
        
        result = debug_prompt_state(_script_context=basic_context)
        
        # The function should detect missing state methods and return appropriate message
        assert "SystemPromptState tracking not available" in result or "Error inspecting SystemPromptState" in result
    
    def test_debug_prompt_state_no_current_state(self):
        """Test debug plugin function when no state is currently tracked."""
        self.mock_context.get_system_prompt_state.return_value = None
        
        result = debug_prompt_state(_script_context=self.mock_context)
        
        assert "No SystemPromptState currently tracked" in result
    
    def test_debug_prompt_state_basic_summary(self):
        """Test debug plugin function returning basic summary."""
        self.mock_context.get_system_prompt_state.return_value = self.sample_state
        
        result = debug_prompt_state(_script_context=self.mock_context)
        
        assert "System Prompt State Summary" in result
        assert "plugin-test" in result
        assert "Plugin test template" in result
    
    def test_debug_prompt_state_detailed(self):
        """Test debug plugin function returning detailed inspection."""
        self.mock_context.get_system_prompt_state.return_value = self.sample_state
        
        result = debug_prompt_state(detailed=True, _script_context=self.mock_context)
        
        assert "Detailed SystemPromptState Inspection" in result
        assert "Full Prompt Evolution:" in result
        assert "plugin-test" in result
    
    def test_debug_prompt_state_exception_handling(self):
        """Test debug plugin function handles exceptions gracefully."""
        self.mock_context.get_system_prompt_state.side_effect = Exception("State access error")
        
        result = debug_prompt_state(_script_context=self.mock_context)
        
        assert "Error inspecting SystemPromptState" in result
        assert "State access error" in result


class TestDebugUtilityIntegration:
    """Integration tests for debug utilities."""
    
    def test_full_debug_workflow(self):
        """Test complete debug workflow from state creation to inspection."""
        # Create a realistic state with full data
        state = SystemPromptState(
            conversation_id="integration-test-456",
            persona_id="debug-persona-789", 
            execution_timestamp=datetime.now(timezone.utc),
            original_template="You are a helpful AI. @personality @context @tools",
            stage1_resolved="You are a helpful AI. Friendly and knowledgeable. Current context loaded. Tools: calculator, search.",
            stage2_resolved="You are a helpful AI. Friendly and knowledgeable. Current context loaded. Tools: calculator, search. Enhanced with situational awareness.",
            main_response_prompt="You are a helpful AI. Friendly and knowledgeable. Current context loaded. Tools: calculator, search. Enhanced with situational awareness.",
            stage4_context={
                "conversation_summary": "User asked for help with math",
                "user_mood": "focused"
            },
            stage5_context={
                "response_effectiveness": "9/10 - very helpful",
                "suggestions": "Consider offering step-by-step explanation"
            },
            resolved_modules=["personality", "context", "tools", "conversation_tracker", "response_analyzer"],
            execution_stages=[1, 2, 4, 5],
            stage_timings={1: 0.04, 2: 0.18, 4: 0.02, 5: 0.25},
            total_execution_time=0.49,
            variables_by_stage={
                4: {
                    "conversation_tracker": {
                        "conversation_summary": "User asked for help with math",
                        "user_mood": "focused"
                    }
                },
                5: {
                    "response_analyzer": {
                        "response_effectiveness": "9/10 - very helpful",
                        "suggestions": "Consider offering step-by-step explanation"
                    }
                }
            }
        )
        
        # Test all debug functions
        inspector = SystemPromptInspector()
        
        # Test summary
        summary = inspector.format_state_summary(state)
        assert len(summary) > 100  # Should be substantial
        assert "integration-test-456" in summary
        assert "0.490s" in summary
        
        # Test detailed inspection
        detailed = inspector.format_detailed_inspection(state)
        assert len(detailed) > len(summary)  # Should be more detailed
        assert "step-by-step explanation" in detailed
        assert "Stage 5 (POST_RESPONSE AI): 0.250s" in detailed
        
        # Test debug data extraction
        debug_data = inspector.extract_debug_data(state)
        assert debug_data["total_execution_time"] == 0.49
        assert debug_data["performance_metrics"]["total_time"] == 0.49
        assert len(debug_data["execution_metadata"]["resolved_modules"]) == 5
        
        # Test JSON serialization
        json_output = extract_debug_json(state)
        import json
        parsed = json.loads(json_output)
        assert parsed["conversation_id"] == "integration-test-456"