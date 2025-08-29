"""
Unit tests for SystemPromptState tracking functionality.

Tests the core system prompt state tracking that provides complete visibility
into how the system prompt evolves through the 5-stage execution pipeline.
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, Any
from unittest.mock import Mock

from app.services.system_prompt_state import (
    SystemPromptState,
    PromptStateManager
)
from app.services.staged_module_resolver import ModuleResolutionWarning


class TestSystemPromptState:
    """Test cases for SystemPromptState dataclass."""
    
    def test_create_basic_system_prompt_state(self):
        """Test creating a basic SystemPromptState."""
        state = SystemPromptState(
            conversation_id="test-conv-123",
            persona_id="test-persona-456", 
            execution_timestamp=datetime.utcnow(),
            original_template="You are an AI assistant. @greeting"
        )
        
        assert state.conversation_id == "test-conv-123"
        assert state.persona_id == "test-persona-456"
        assert state.original_template == "You are an AI assistant. @greeting"
        assert state.stage1_resolved == ""
        assert state.stage2_resolved == ""
        assert state.main_response_prompt == ""
        assert state.stage4_context == {}
        assert state.stage5_context == {}
        assert state.resolved_modules == []
        assert state.warnings == []
        assert state.execution_stages == []
        assert state.variables_by_stage == {}
        assert state.stage_timings == {}
        assert state.total_execution_time == 0.0
    
    def test_update_stage1_resolution(self):
        """Test updating state after Stage 1 resolution."""
        state = SystemPromptState(
            conversation_id="test-conv",
            persona_id="test-persona",
            execution_timestamp=datetime.utcnow(),
            original_template="You are an AI assistant. @greeting @mood"
        )
        
        # Simulate Stage 1 completion
        state.stage1_resolved = "You are an AI assistant. Hello! I'm happy today!"
        state.resolved_modules = ["greeting", "mood"]
        state.execution_stages = [1]
        state.stage_timings = {1: 0.05}
        
        assert state.stage1_resolved == "You are an AI assistant. Hello! I'm happy today!"
        assert state.resolved_modules == ["greeting", "mood"]
        assert state.execution_stages == [1]
        assert state.stage_timings[1] == 0.05
    
    def test_complete_stage_progression(self):
        """Test complete progression through all stages."""
        state = SystemPromptState(
            conversation_id="test-conv",
            persona_id="test-persona",
            execution_timestamp=datetime.utcnow(),
            original_template="Assistant: @greeting\n\n@context_module"
        )
        
        # Stage 1: Simple modules + immediate non-AI
        state.stage1_resolved = "Assistant: Hello!\n\n@context_module"
        state.resolved_modules.append("greeting")
        state.execution_stages.append(1)
        state.stage_timings[1] = 0.03
        
        # Stage 2: Immediate AI modules
        state.stage2_resolved = "Assistant: Hello!\n\nContext: Current conversation focuses on testing"
        state.resolved_modules.append("context_module")
        state.main_response_prompt = state.stage2_resolved  # This goes to main AI
        state.execution_stages.append(2)
        state.stage_timings[2] = 0.15
        
        # Stage 4: POST_RESPONSE non-AI
        state.stage4_context = {"summary": "User asked about testing"}
        state.variables_by_stage[4] = state.stage4_context
        state.execution_stages.append(4)
        state.stage_timings[4] = 0.02
        
        # Stage 5: POST_RESPONSE AI
        state.stage5_context = {"quality_rating": "8/10 - Good response"}
        state.variables_by_stage[5] = state.stage5_context
        state.execution_stages.append(5)
        state.stage_timings[5] = 0.25
        
        # Total execution time
        state.total_execution_time = sum(state.stage_timings.values())
        
        # Verify complete state
        assert state.original_template.startswith("Assistant: @greeting")
        assert "@greeting" not in state.stage1_resolved
        assert "@context_module" not in state.stage2_resolved
        assert state.main_response_prompt == state.stage2_resolved
        assert state.stage4_context["summary"] == "User asked about testing"
        assert state.stage5_context["quality_rating"] == "8/10 - Good response"
        assert state.execution_stages == [1, 2, 4, 5]
        assert abs(state.total_execution_time - 0.45) < 0.001  # Handle floating point precision
    
    def test_add_warnings_and_metadata(self):
        """Test adding warnings and execution metadata."""
        state = SystemPromptState(
            conversation_id="test-conv",
            persona_id="test-persona",
            execution_timestamp=datetime.utcnow(),
            original_template="@missing_module @working_module"
        )
        
        # Add warning for missing module
        warning = ModuleResolutionWarning(
            module_name="missing_module",
            warning_type="module_not_found",
            message="Module 'missing_module' not found",
            stage=1
        )
        state.warnings.append(warning)
        
        # Successful resolution of working module
        state.stage1_resolved = "@missing_module Working content"
        state.resolved_modules = ["working_module"]
        
        assert len(state.warnings) == 1
        assert state.warnings[0].module_name == "missing_module"
        assert state.warnings[0].warning_type == "module_not_found"
        assert state.resolved_modules == ["working_module"]
    
    def test_to_dict_serialization(self):
        """Test converting SystemPromptState to dictionary for API responses."""
        timestamp = datetime.utcnow()
        state = SystemPromptState(
            conversation_id="test-conv",
            persona_id="test-persona",
            execution_timestamp=timestamp,
            original_template="Original template",
            stage1_resolved="Stage 1 resolved",
            stage2_resolved="Stage 2 resolved",
            main_response_prompt="Main AI prompt",
            resolved_modules=["mod1", "mod2"],
            execution_stages=[1, 2],
            stage_timings={1: 0.1, 2: 0.2},
            total_execution_time=0.3
        )
        
        result = state.to_dict()
        
        assert result["conversation_id"] == "test-conv"
        assert result["persona_id"] == "test-persona"
        assert result["execution_timestamp"] == timestamp.isoformat()
        assert result["original_template"] == "Original template"
        assert result["stage1_resolved"] == "Stage 1 resolved"
        assert result["stage2_resolved"] == "Stage 2 resolved"
        assert result["main_response_prompt"] == "Main AI prompt"
        assert result["resolved_modules"] == ["mod1", "mod2"]
        assert result["execution_stages"] == [1, 2]
        assert result["stage_timings"] == {1: 0.1, 2: 0.2}
        assert result["total_execution_time"] == 0.3
    
    def test_get_prompt_for_stage(self):
        """Test getting appropriate prompt for different execution stages."""
        state = SystemPromptState(
            conversation_id="test-conv",
            persona_id="test-persona", 
            execution_timestamp=datetime.utcnow(),
            original_template="Original: @module1",
            stage1_resolved="Stage1: Content1",
            stage2_resolved="Stage2: Content1 + AI Content",
            main_response_prompt="Main: Content1 + AI Content",
            stage4_context={"var1": "value1"},
            variables_by_stage={4: {"var1": "value1"}}
        )
        
        # Test getting prompt for Stage 2 (IMMEDIATE AI)
        stage2_prompt = state.get_prompt_for_stage(2)
        assert stage2_prompt == "Stage1: Content1"  # Uses Stage 1 result
        
        # Test getting prompt for Stage 5 (POST_RESPONSE AI)
        stage5_prompt = state.get_prompt_for_stage(5)
        expected = "Main: Content1 + AI Content\n\nCurrent context:\nvar1:\n  value1"
        assert stage5_prompt == expected
        
        # Test unsupported stage
        stage3_prompt = state.get_prompt_for_stage(3)
        assert stage3_prompt == "Original: @module1"
    
    def test_format_stage_variables(self):
        """Test formatting stage variables for context."""
        state = SystemPromptState(
            conversation_id="test-conv",
            persona_id="test-persona",
            execution_timestamp=datetime.utcnow(),
            original_template="Test"
        )
        
        # Test with Stage 4 variables
        state.variables_by_stage[4] = {
            "summary_module": {"conversation_summary": "Brief chat about testing"},
            "mood_detector": {"current_mood": "positive"}
        }
        
        formatted = state._format_stage_variables(4)
        
        assert "summary_module:" in formatted
        assert "conversation_summary: Brief chat about testing" in formatted
        assert "mood_detector:" in formatted
        assert "current_mood: positive" in formatted
    
    def test_performance_analysis(self):
        """Test performance analysis capabilities."""
        state = SystemPromptState(
            conversation_id="test-conv",
            persona_id="test-persona",
            execution_timestamp=datetime.utcnow(),
            original_template="@slow_module @fast_module",
            stage_timings={1: 0.05, 2: 0.50, 4: 0.01, 5: 1.20},
            total_execution_time=1.76
        )
        
        # Get performance summary
        perf_summary = state.get_performance_summary()
        
        assert perf_summary["total_time"] == 1.76
        assert perf_summary["slowest_stage"] == 5
        assert perf_summary["fastest_stage"] == 4
        assert perf_summary["ai_stages_time"] == 1.70  # Stage 2 + 5
        assert abs(perf_summary["non_ai_stages_time"] - 0.06) < 0.001  # Handle floating point precision


class TestPromptStateManager:
    """Test cases for PromptStateManager utility class."""
    
    def test_create_initial_state(self):
        """Test creating initial prompt state."""
        manager = PromptStateManager()
        
        state = manager.create_initial_state(
            conversation_id="test-conv",
            persona_id="test-persona",
            original_template="You are @personality. @context"
        )
        
        assert isinstance(state, SystemPromptState)
        assert state.conversation_id == "test-conv"
        assert state.persona_id == "test-persona"
        assert state.original_template == "You are @personality. @context"
        assert isinstance(state.execution_timestamp, datetime)
    
    def test_update_stage1_completion(self):
        """Test updating state after Stage 1 completion."""
        manager = PromptStateManager()
        state = manager.create_initial_state("conv", "persona", "Original @module")
        
        # Simulate Stage 1 results
        resolved_template = "Original resolved_content"
        resolved_modules = ["module"]
        warnings = []
        execution_time = 0.05
        
        updated_state = manager.update_stage1_completion(
            state, resolved_template, resolved_modules, warnings, execution_time
        )
        
        assert updated_state.stage1_resolved == "Original resolved_content"
        assert updated_state.resolved_modules == ["module"]
        assert updated_state.execution_stages == [1]
        assert updated_state.stage_timings[1] == 0.05
    
    def test_update_stage2_completion(self):
        """Test updating state after Stage 2 completion."""
        manager = PromptStateManager()
        state = manager.create_initial_state("conv", "persona", "Original @ai_module")
        
        # Update Stage 1 first
        state = manager.update_stage1_completion(
            state, "Original content", ["simple_mod"], [], 0.02
        )
        
        # Update Stage 2
        stage2_template = "Original content + AI enhancement"
        additional_modules = ["ai_module"]
        execution_time = 0.15
        
        updated_state = manager.update_stage2_completion(
            state, stage2_template, additional_modules, [], execution_time
        )
        
        assert updated_state.stage2_resolved == "Original content + AI enhancement"
        assert updated_state.main_response_prompt == "Original content + AI enhancement"
        assert "ai_module" in updated_state.resolved_modules
        assert updated_state.execution_stages == [1, 2]
        assert updated_state.stage_timings[2] == 0.15
    
    def test_update_post_response_stages(self):
        """Test updating state after POST_RESPONSE stages."""
        manager = PromptStateManager()
        state = manager.create_initial_state("conv", "persona", "Original")
        
        # Add some initial stages
        state.execution_stages = [1, 2]
        state.main_response_prompt = "Resolved prompt"
        
        # Update Stage 4 (non-AI POST_RESPONSE)
        stage4_variables = {"summary": "Conversation summary"}
        stage4_time = 0.03
        
        updated_state = manager.update_stage4_completion(
            state, stage4_variables, stage4_time
        )
        
        assert updated_state.stage4_context == {"summary": "Conversation summary"}
        assert updated_state.variables_by_stage[4] == {"summary": "Conversation summary"}
        assert 4 in updated_state.execution_stages
        assert updated_state.stage_timings[4] == 0.03
        
        # Update Stage 5 (AI POST_RESPONSE)
        stage5_variables = {"quality": "8/10"}
        stage5_time = 0.20
        
        final_state = manager.update_stage5_completion(
            updated_state, stage5_variables, stage5_time
        )
        
        assert final_state.stage5_context == {"quality": "8/10"}
        assert final_state.variables_by_stage[5] == {"quality": "8/10"}
        assert 5 in final_state.execution_stages
        assert final_state.stage_timings[5] == 0.20
    
    def test_finalize_state(self):
        """Test finalizing prompt state with total execution time."""
        manager = PromptStateManager()
        state = manager.create_initial_state("conv", "persona", "Original")
        
        state.stage_timings = {1: 0.05, 2: 0.15, 4: 0.02, 5: 0.30}
        
        final_state = manager.finalize_state(state)
        
        assert final_state.total_execution_time == 0.52
    
    def test_get_debug_summary(self):
        """Test getting debug summary of prompt state."""
        manager = PromptStateManager()
        state = manager.create_initial_state("conv", "persona", "Original @mod1 @mod2")
        
        # Populate some state
        state.stage1_resolved = "Stage 1 result"
        state.stage2_resolved = "Stage 2 result"
        state.main_response_prompt = "Main prompt"
        state.resolved_modules = ["mod1", "mod2"]
        state.execution_stages = [1, 2]
        state.stage_timings = {1: 0.1, 2: 0.2}
        state.total_execution_time = 0.3
        
        debug_summary = manager.get_debug_summary(state)
        
        assert debug_summary["conversation_id"] == "conv"
        assert debug_summary["persona_id"] == "persona"
        assert "prompt_evolution" in debug_summary
        assert "execution_metadata" in debug_summary
        assert "performance_metrics" in debug_summary
        
        # Check prompt evolution
        evolution = debug_summary["prompt_evolution"]
        assert evolution["original"] == "Original @mod1 @mod2"
        assert evolution["stage1"] == "Stage 1 result"
        assert evolution["stage2"] == "Stage 2 result"
        assert evolution["main_ai"] == "Main prompt"
        
        # Check execution metadata
        metadata = debug_summary["execution_metadata"]
        assert metadata["resolved_modules"] == ["mod1", "mod2"]
        assert metadata["stages_executed"] == [1, 2]
        
        # Check performance metrics
        performance = debug_summary["performance_metrics"]
        assert performance["total_time"] == 0.3
        assert performance["stage_timings"] == {1: 0.1, 2: 0.2}