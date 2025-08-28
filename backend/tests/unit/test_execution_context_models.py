"""
Unit tests for ExecutionContext enum and ConversationState model.

Tests the new staged execution models and their functionality.
"""

import pytest
import uuid
from datetime import datetime
from unittest.mock import Mock

from app.models import (
    Module, ModuleType, ExecutionContext, 
    ConversationState, ExecutionStage
)


class TestExecutionContextEnum:
    """Test the ExecutionContext enum."""
    
    def test_enum_values(self):
        """Test that ExecutionContext has correct values."""
        assert ExecutionContext.IMMEDIATE.value == "IMMEDIATE"
        assert ExecutionContext.POST_RESPONSE.value == "POST_RESPONSE"
        assert ExecutionContext.ON_DEMAND.value == "ON_DEMAND"
    
    def test_enum_ordering(self):
        """Test that enum values are in expected order."""
        contexts = list(ExecutionContext)
        assert len(contexts) == 3
        assert ExecutionContext.IMMEDIATE in contexts
        assert ExecutionContext.POST_RESPONSE in contexts
        assert ExecutionContext.ON_DEMAND in contexts
    
    def test_string_representation(self):
        """Test string representation of enum values."""
        assert str(ExecutionContext.IMMEDIATE) == "ExecutionContext.IMMEDIATE"
        assert ExecutionContext.IMMEDIATE.value == "IMMEDIATE"


class TestExecutionStageEnum:
    """Test the ExecutionStage enum."""
    
    def test_enum_values(self):
        """Test that ExecutionStage has correct values."""
        assert ExecutionStage.STAGE4.value == "stage4"
        assert ExecutionStage.STAGE5.value == "stage5"
    
    def test_enum_count(self):
        """Test that we have exactly the expected stages."""
        stages = list(ExecutionStage)
        assert len(stages) == 2


class TestModuleEnhancements:
    """Test the enhancements to the Module model for staged execution."""
    
    def test_execution_context_properties(self):
        """Test the execution context boolean properties."""
        # Test IMMEDIATE context
        module = Module(
            name="test_immediate",
            type=ModuleType.SIMPLE,
            execution_context=ExecutionContext.IMMEDIATE
        )
        
        assert module.is_immediate_context is True
        assert module.is_post_response_context is False
        assert module.is_on_demand_context is False
        
        # Test POST_RESPONSE context
        module.execution_context = ExecutionContext.POST_RESPONSE
        assert module.is_immediate_context is False
        assert module.is_post_response_context is True
        assert module.is_on_demand_context is False
        
        # Test ON_DEMAND context
        module.execution_context = ExecutionContext.ON_DEMAND
        assert module.is_immediate_context is False
        assert module.is_post_response_context is False
        assert module.is_on_demand_context is True
    
    def test_execution_stage_priority(self):
        """Test execution stage priority calculation."""
        # IMMEDIATE without AI - Stage 1
        module = Module(
            name="test1",
            type=ModuleType.SIMPLE,
            execution_context=ExecutionContext.IMMEDIATE,
            requires_ai_inference=False
        )
        assert module.execution_stage_priority == 1
        
        # IMMEDIATE with AI - Stage 2
        module.requires_ai_inference = True
        assert module.execution_stage_priority == 2
        
        # POST_RESPONSE without AI - Stage 4
        module.execution_context = ExecutionContext.POST_RESPONSE
        module.requires_ai_inference = False
        assert module.execution_stage_priority == 4
        
        # POST_RESPONSE with AI - Stage 5
        module.requires_ai_inference = True
        assert module.execution_stage_priority == 5
        
        # ON_DEMAND - High priority (not in main pipeline)
        module.execution_context = ExecutionContext.ON_DEMAND
        assert module.execution_stage_priority == 999
    
    def test_get_stage_name(self):
        """Test human-readable stage name generation."""
        module = Module(
            name="test",
            type=ModuleType.SIMPLE,
            execution_context=ExecutionContext.IMMEDIATE,
            requires_ai_inference=False
        )
        
        # Test all stage combinations
        stage_tests = [
            (ExecutionContext.IMMEDIATE, False, "Stage 1: Template preparation"),
            (ExecutionContext.IMMEDIATE, True, "Stage 2: Pre-response AI processing"),
            (ExecutionContext.POST_RESPONSE, False, "Stage 4: Post-response processing"),
            (ExecutionContext.POST_RESPONSE, True, "Stage 5: Post-response AI analysis"),
            (ExecutionContext.ON_DEMAND, False, "On-demand execution"),
            (ExecutionContext.ON_DEMAND, True, "On-demand execution"),
        ]
        
        for context, ai_inference, expected_name in stage_tests:
            module.execution_context = context
            module.requires_ai_inference = ai_inference
            assert module.get_stage_name() == expected_name
    
    def test_analyze_script_method(self):
        """Test the analyze_script method."""
        module = Module(
            name="test_analysis",
            type=ModuleType.ADVANCED,
            execution_context=ExecutionContext.IMMEDIATE,
            requires_ai_inference=False,
            script='response = ctx.reflect("How did this go?")'
        )
        
        # Call analyze_script
        analysis_result = module.analyze_script()
        
        # Should return dictionary with analysis results
        assert isinstance(analysis_result, dict)
        assert 'requires_ai_inference' in analysis_result
        assert 'uses_reflect' in analysis_result
        assert 'analysis_success' in analysis_result
        
        # Module's requires_ai_inference should be updated
        assert module.requires_ai_inference is True  # Updated by analysis
        
        # Script analysis metadata should be populated
        assert module.script_analysis_metadata is not None
        assert isinstance(module.script_analysis_metadata, dict)
    
    def test_analyze_script_simple_module(self):
        """Test analyze_script with simple module (no script)."""
        module = Module(
            name="test_simple",
            type=ModuleType.SIMPLE,
            execution_context=ExecutionContext.IMMEDIATE
        )
        
        analysis_result = module.analyze_script()
        assert analysis_result == {}  # Empty dict for simple modules
    
    def test_refresh_ai_analysis(self):
        """Test the refresh_ai_analysis method."""
        module = Module(
            name="test_refresh",
            type=ModuleType.ADVANCED,
            script='result = ctx.get_current_time()',
            requires_ai_inference=True  # Initially wrong
        )
        
        # Mock database session
        mock_session = Mock()
        
        # Call refresh_ai_analysis
        module.refresh_ai_analysis(mock_session)
        
        # Should update requires_ai_inference based on actual script content
        assert module.requires_ai_inference is False  # Corrected by analysis
        
        # Should call flush on session if provided
        mock_session.flush.assert_called_once()


class TestConversationStateModel:
    """Test the ConversationState model."""
    
    def test_model_creation(self):
        """Test basic ConversationState model creation."""
        conversation_id = str(uuid.uuid4())
        module_id = str(uuid.uuid4())
        
        state = ConversationState(
            conversation_id=conversation_id,
            module_id=module_id,
            execution_stage="stage5",
            variables={"mood": "happy", "score": 8.5},
            execution_metadata={"success": True, "duration": 250},
            executed_at=datetime.utcnow()  # Set explicitly for test
        )
        
        assert str(state.conversation_id) == conversation_id
        assert str(state.module_id) == module_id
        assert state.execution_stage == "stage5"
        assert state.variables["mood"] == "happy"
        assert state.execution_metadata["success"] is True
        assert state.executed_at is not None  # Should have default
    
    def test_repr_string(self):
        """Test string representation of ConversationState."""
        state = ConversationState(
            conversation_id=str(uuid.uuid4()),
            module_id=str(uuid.uuid4()),
            execution_stage="stage4",
            variables={"test": "value"}
        )
        
        repr_str = repr(state)
        assert "ConversationState" in repr_str
        assert "stage=stage4" in repr_str
        assert "1 vars" in repr_str
    
    def test_to_dict_method(self):
        """Test conversion to dictionary."""
        conversation_id = str(uuid.uuid4())
        module_id = str(uuid.uuid4())
        
        state = ConversationState(
            conversation_id=conversation_id,
            module_id=module_id,
            execution_stage="stage5",
            variables={"result": "success"},
            execution_metadata={"tokens": 42}
        )
        
        state_dict = state.to_dict()
        
        # Check all expected keys
        expected_keys = {
            'id', 'conversation_id', 'module_id', 'execution_stage',
            'variables', 'execution_metadata', 'executed_at', 'module_name'
        }
        assert set(state_dict.keys()) == expected_keys
        
        # Check values
        assert state_dict['conversation_id'] == conversation_id
        assert state_dict['module_id'] == module_id
        assert state_dict['execution_stage'] == "stage5"
        assert state_dict['variables'] == {"result": "success"}
        assert state_dict['execution_metadata'] == {"tokens": 42}
        assert state_dict['module_name'] is None  # No module relationship in test
    
    def test_store_execution_result_new(self):
        """Test storing a new execution result."""
        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.first.return_value = None  # No existing
        
        conversation_id = str(uuid.uuid4())
        module_id = str(uuid.uuid4())
        variables = {"mood": "excellent", "insights": ["helpful", "clear"]}
        metadata = {"success": True, "duration": 300}
        
        result_state = ConversationState.store_execution_result(
            mock_session,
            conversation_id,
            module_id,
            "stage5",
            variables,
            metadata
        )
        
        # Should create new ConversationState
        assert isinstance(result_state, ConversationState)
        assert str(result_state.conversation_id) == conversation_id
        assert str(result_state.module_id) == module_id
        assert result_state.execution_stage == "stage5"
        assert result_state.variables == variables
        assert result_state.execution_metadata == metadata
        
        # Should add to session and flush
        mock_session.add.assert_called_once_with(result_state)
        mock_session.flush.assert_called_once()
    
    def test_store_execution_result_update_existing(self):
        """Test updating an existing execution result."""
        # Mock existing state
        existing_state = ConversationState(
            conversation_id=str(uuid.uuid4()),
            module_id=str(uuid.uuid4()),
            execution_stage="stage5",
            variables={"old": "data"},
            execution_metadata={"old": "metadata"}
        )
        
        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.first.return_value = existing_state
        
        new_variables = {"new": "data", "updated": True}
        new_metadata = {"success": True, "updated": True}
        
        result_state = ConversationState.store_execution_result(
            mock_session,
            str(existing_state.conversation_id),
            str(existing_state.module_id),
            "stage5",
            new_variables,
            new_metadata
        )
        
        # Should return the updated existing state
        assert result_state is existing_state
        assert result_state.variables == new_variables
        assert result_state.execution_metadata == new_metadata
        
        # Should flush but not add (already exists)
        mock_session.flush.assert_called_once()
        mock_session.add.assert_not_called()
    
    def test_get_for_conversation(self):
        """Test getting all states for a conversation."""
        conversation_id = str(uuid.uuid4())
        
        # Mock query chain
        mock_session = Mock()
        mock_query = Mock()
        mock_filter = Mock()
        mock_order = Mock()
        
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.order_by.return_value = mock_order
        
        # Call method
        result = ConversationState.get_for_conversation(mock_session, conversation_id)
        
        # Should return the ordered query
        assert result is mock_order
        
        # Verify query chain
        mock_session.query.assert_called_once_with(ConversationState)
        # Note: Can't easily test the filter condition without complex mocking
    
    def test_get_latest_for_module(self):
        """Test getting latest state for a specific module."""
        conversation_id = str(uuid.uuid4())
        module_id = str(uuid.uuid4())
        
        # Mock query chain
        mock_session = Mock()
        mock_query = Mock()
        mock_filter = Mock()
        mock_order = Mock()
        
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.order_by.return_value = mock_order
        mock_order.first.return_value = "latest_state"
        
        # Call method
        result = ConversationState.get_latest_for_module(mock_session, conversation_id, module_id)
        
        # Should return first result from ordered query
        assert result == "latest_state"
        
        # Verify method calls
        mock_session.query.assert_called_once_with(ConversationState)
        mock_order.first.assert_called_once()


class TestModuleStageQuerying:
    """Test Module.get_modules_for_stage class method."""
    
    def test_stage1_query(self):
        """Test querying for Stage 1 modules."""
        mock_session = Mock()
        mock_query = Mock()
        mock_filter = Mock()
        mock_order = Mock()
        
        # Set up mock chain
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.filter.return_value = mock_order
        mock_order.order_by.return_value = "stage1_modules"
        
        result = Module.get_modules_for_stage(mock_session, 1)
        
        assert result == "stage1_modules"
        mock_session.query.assert_called_once_with(Module)
        # Should filter for IMMEDIATE context and no AI inference
    
    def test_stage2_query(self):
        """Test querying for Stage 2 modules."""
        mock_session = Mock()
        mock_query = Mock()
        mock_filter = Mock()
        mock_order = Mock()
        
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.filter.return_value = mock_order
        mock_order.order_by.return_value = "stage2_modules"
        
        result = Module.get_modules_for_stage(mock_session, 2)
        
        assert result == "stage2_modules"
        # Should filter for IMMEDIATE context and AI inference required
    
    def test_stage4_query(self):
        """Test querying for Stage 4 modules."""
        mock_session = Mock()
        mock_query = Mock()
        mock_filter = Mock()
        mock_order = Mock()
        
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.filter.return_value = mock_order
        mock_order.order_by.return_value = "stage4_modules"
        
        result = Module.get_modules_for_stage(mock_session, 4)
        
        assert result == "stage4_modules"
        # Should filter for POST_RESPONSE context and no AI inference
    
    def test_stage5_query(self):
        """Test querying for Stage 5 modules."""
        mock_session = Mock()
        mock_query = Mock()
        mock_filter = Mock()
        mock_order = Mock()
        
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.filter.return_value = mock_order
        mock_order.order_by.return_value = "stage5_modules"
        
        result = Module.get_modules_for_stage(mock_session, 5)
        
        assert result == "stage5_modules"
        # Should filter for POST_RESPONSE context and AI inference required
    
    def test_invalid_stage_query(self):
        """Test querying for invalid stage number."""
        mock_session = Mock()
        mock_query = Mock()
        mock_filter = Mock()
        
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.filter.return_value = "empty_query"
        
        result = Module.get_modules_for_stage(mock_session, 99)
        
        # Should return empty query for invalid stage
        assert result == "empty_query"
    
    def test_with_persona_filter(self):
        """Test querying with persona ID filter."""
        mock_session = Mock()
        
        # Mock persona with template
        mock_persona = Mock()
        mock_persona.template = "Welcome! @greeting_module Please follow @safety_rules"
        
        # Mock query chains
        mock_query = Mock()
        mock_filter = Mock()
        mock_order = Mock()
        mock_persona_query = Mock()
        
        mock_session.query.side_effect = lambda model: (
            mock_persona_query if model.__name__ == 'Persona' else mock_query
        )
        mock_persona_query.filter.return_value.first.return_value = mock_persona
        mock_query.filter.return_value = mock_filter
        mock_filter.filter.return_value = mock_filter  # Chain multiple filters
        mock_filter.order_by.return_value = "filtered_modules"
        
        persona_id = str(uuid.uuid4())
        result = Module.get_modules_for_stage(mock_session, 1, persona_id)
        
        assert result == "filtered_modules"
        # Should include filter for module names found in persona template