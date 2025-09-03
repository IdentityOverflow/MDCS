"""
Unit tests for the StagedModuleResolver.

Tests the new 5-stage execution pipeline for module resolution.
"""

import pytest
import uuid
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from app.services.staged_module_resolver import StagedModuleResolver
from app.services.staged_module_resolver_base import (
    StagedTemplateResolutionResult,
    PostResponseExecutionResult,
    ModuleResolutionWarning,
    ExecutionStage,
    resolve_template_for_response
)
from app.models import Module, ModuleType, ExecutionContext, ConversationState


class TestStagedModuleResolver:
    """Test the StagedModuleResolver class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_session = Mock()
        self.resolver = StagedModuleResolver(self.mock_session)
        self.conversation_id = str(uuid.uuid4())
        self.persona_id = str(uuid.uuid4())
    
    def test_initialization(self):
        """Test resolver initialization."""
        resolver = StagedModuleResolver()
        assert resolver.db_session is None
        assert resolver._resolution_stack == set()
        
        resolver_with_session = StagedModuleResolver(self.mock_session)
        assert resolver_with_session.db_session == self.mock_session
    
    def test_empty_template_resolution(self):
        """Test resolution of empty templates."""
        result = self.resolver.resolve_template_stage1_and_stage2("")
        
        assert isinstance(result, StagedTemplateResolutionResult)
        assert result.resolved_template == ""
        assert result.warnings == []
        assert result.resolved_modules == []
        assert result.stages_executed == []
        
        # Test None template
        result = self.resolver.resolve_template_stage1_and_stage2(None)
        assert result.resolved_template == ""
    
    @patch('app.services.staged_module_resolver.Module.get_modules_for_stage')
    def test_stage1_simple_module_resolution(self, mock_get_modules):
        """Test Stage 1 resolution with simple modules."""
        # Create mock simple module
        simple_module = Module(
            id=uuid.uuid4(),
            name="greeting",
            type=ModuleType.SIMPLE,
            execution_context=ExecutionContext.IMMEDIATE,
            content="Hello there!",
            is_active=True
        )
        
        mock_get_modules.return_value.all.return_value = [simple_module]
        
        template = "Welcome! @greeting Please enjoy your stay."
        result = self.resolver.resolve_template_stage1_and_stage2(
            template, self.conversation_id, self.persona_id, self.mock_session
        )
        
        assert result.resolved_template == "Welcome! Hello there! Please enjoy your stay."
        assert "greeting" in result.resolved_modules
        assert 1 in result.stages_executed
        assert 2 in result.stages_executed
        assert len(result.warnings) == 0
    
    @patch('app.services.staged_module_resolver.Module.get_modules_for_stage')
    def test_stage2_ai_module_resolution(self, mock_get_modules):
        """Test Stage 2 resolution with AI-powered modules."""
        # Mock stage 1 returns empty, stage 2 returns AI module
        def stage_side_effect(db_session, stage, persona_id=None):
            mock_query = Mock()
            if stage == 1:
                mock_query.all.return_value = []
            elif stage == 2:
                ai_module = Module(
                    id=uuid.uuid4(),
                    name="mood_check",
                    type=ModuleType.ADVANCED,
                    execution_context=ExecutionContext.IMMEDIATE,
                    content="Mood: ${current_mood}",
                    script='current_mood = "happy"',
                    requires_ai_inference=True,
                    is_active=True
                )
                mock_query.all.return_value = [ai_module]
            else:
                mock_query.all.return_value = []
            return mock_query
        
        mock_get_modules.side_effect = stage_side_effect
        
        # Mock script execution
        with patch('app.services.staged_module_resolver.ScriptEngine') as mock_engine:
            mock_result = Mock()
            mock_result.success = True
            mock_result.outputs = {"current_mood": "happy"}
            mock_engine.return_value.execute_script.return_value = mock_result
            
            template = "Current status: @mood_check"
            result = self.resolver.resolve_template_stage1_and_stage2(
                template, self.conversation_id, self.persona_id, self.mock_session
            )
            
            assert result.resolved_template == "Current status: Mood: happy"
            assert "mood_check" in result.resolved_modules
            assert 1 in result.stages_executed
            assert 2 in result.stages_executed
    
    def test_escaped_module_handling(self):
        """Test that escaped modules are preserved."""
        template = "Use \\@greeting for greetings and @welcome for welcomes"
        
        with patch('app.services.staged_module_resolver.Module.get_modules_for_stage') as mock_get_modules:
            # Only return modules for @welcome
            welcome_module = Module(
                id=uuid.uuid4(),
                name="welcome",
                type=ModuleType.SIMPLE,
                content="Welcome!",
                is_active=True
            )
            
            def stage_side_effect(db_session, stage, persona_id=None):
                mock_query = Mock()
                if stage == 1:
                    mock_query.all.return_value = [welcome_module]
                else:
                    mock_query.all.return_value = []
                return mock_query
                
            mock_get_modules.side_effect = stage_side_effect
            
            result = self.resolver.resolve_template_stage1_and_stage2(template)
            
            # @greeting should remain as @greeting (escaped), @welcome should be resolved
            assert "@greeting" in result.resolved_template
            assert "Welcome!" in result.resolved_template
            assert "welcome" in result.resolved_modules
    
    def test_circular_dependency_detection(self):
        """Test circular dependency detection and handling."""
        # This test is complex to set up with the new staged approach
        # We'll test the internal method directly
        self.resolver._resolution_stack = {"module_a"}
        
        warnings = []
        resolved_modules = []
        
        # Try to resolve module_a again (should detect circular dependency)
        module_a = Module(
            id=uuid.uuid4(),
            name="module_a",
            type=ModuleType.SIMPLE,
            content="Content A",
            is_active=True
        )
        
        result = self.resolver._resolve_modules_in_template(
            "@module_a", [module_a], warnings, resolved_modules, 1,
            None, None, None, None, None, None, None
        )
        
        # Should have warning and not resolve the module
        assert len(warnings) == 1
        assert warnings[0].warning_type == "circular_dependency"
        assert "module_a" not in resolved_modules
    
    def test_parse_module_references(self):
        """Test parsing of module references from templates."""
        # Test various patterns
        test_cases = [
            ("No modules here", []),
            ("@simple_module", ["simple_module"]),
            ("@module1 and @module2", ["module1", "module2"]),
            ("\\@escaped_module @real_module", ["real_module"]),  # Escaped should not be included
            ("@module_with_123 and @another_one", ["module_with_123", "another_one"]),
            ("@module @module", ["module"]),  # Duplicates should be removed
        ]
        
        for template, expected in test_cases:
            result = self.resolver._parse_module_references(template)
            assert set(result) == set(expected), f"Failed for template: {template}"
    
    def test_variable_resolution(self):
        """Test ${variable} resolution in module content."""
        content = "Hello ${name}, your score is ${score}!"
        outputs = {"name": "Alice", "score": 95}
        
        result = self.resolver._resolve_variables(content, outputs)
        assert result == "Hello Alice, your score is 95!"
        
        # Test missing variables (should become empty strings)
        partial_outputs = {"name": "Bob"}
        result = self.resolver._resolve_variables(content, partial_outputs)
        assert result == "Hello Bob, your score is !"
    
    def test_post_response_execution_success(self):
        """Test successful POST_RESPONSE module execution."""
        persona_id = str(uuid.uuid4())
        conversation_id = str(uuid.uuid4())
        
        # Mock persona and modules
        mock_persona = Mock()
        mock_persona.template = "@feedback_module"
        
        feedback_module = Module(
            id=uuid.uuid4(),
            name="feedback_module",
            type=ModuleType.ADVANCED,
            execution_context=ExecutionContext.POST_RESPONSE,
            content="Feedback: ${feedback_text}",
            script='feedback_text = "Great conversation!"',
            requires_ai_inference=False,
            is_active=True
        )
        
        with patch('app.models.Persona') as mock_persona_class:
            # Mock persona query
            self.mock_session.query.return_value.filter.return_value.first.return_value = mock_persona
            
            # Mock modules query
            self.mock_session.query.return_value.filter.return_value.all.return_value = [feedback_module]
            
            # Mock script execution
            with patch('app.services.staged_module_resolver.ScriptEngine') as mock_engine:
                mock_result = Mock()
                mock_result.success = True
                mock_result.outputs = {"feedback_text": "Great conversation!"}
                mock_engine.return_value.execute_script.return_value = mock_result
                
                # Mock ConversationState.store_execution_result
                with patch('app.services.staged_module_resolver.ConversationState.store_execution_result') as mock_store:
                    results = self.resolver.execute_post_response_modules(
                        persona_id, conversation_id, self.mock_session
                    )
                    
                    assert len(results) == 1
                    assert results[0].module_name == "feedback_module"
                    assert results[0].stage == 4  # Non-AI POST_RESPONSE
                    assert results[0].success is True
                    assert results[0].variables == {"feedback_text": "Great conversation!"}
                    
                    # Verify state was stored
                    mock_store.assert_called_once()
    
    def test_post_response_execution_with_ai_modules(self):
        """Test POST_RESPONSE execution with both AI and non-AI modules."""
        persona_id = str(uuid.uuid4())
        conversation_id = str(uuid.uuid4())
        
        # Mock persona
        mock_persona = Mock()
        mock_persona.template = "@logger @reflector"
        
        # Create non-AI and AI POST_RESPONSE modules
        logger_module = Module(
            id=uuid.uuid4(),
            name="logger",
            type=ModuleType.ADVANCED,
            execution_context=ExecutionContext.POST_RESPONSE,
            content="Log: ${log_entry}",
            script='log_entry = "Conversation logged"',
            requires_ai_inference=False,
            is_active=True
        )
        
        reflector_module = Module(
            id=uuid.uuid4(),
            name="reflector",
            type=ModuleType.ADVANCED,
            execution_context=ExecutionContext.POST_RESPONSE,
            content="Reflection: ${reflection}",
            script='reflection = ctx.reflect("How did this go?")',
            requires_ai_inference=True,
            is_active=True
        )
        
        with patch('app.models.Persona'):
            # Mock persona query
            self.mock_session.query.return_value.filter.return_value.first.return_value = mock_persona
            
            # Mock modules query
            self.mock_session.query.return_value.filter.return_value.all.return_value = [logger_module, reflector_module]
            
            # Mock script execution for both modules
            with patch('app.services.staged_module_resolver.ScriptEngine') as mock_engine:
                def script_side_effect(script, context):
                    mock_result = Mock()
                    mock_result.success = True
                    if "log_entry" in script:
                        mock_result.outputs = {"log_entry": "Conversation logged"}
                    elif "reflection" in script:
                        mock_result.outputs = {"reflection": "It went well!"}
                    else:
                        mock_result.outputs = {}
                    return mock_result
                
                mock_engine.return_value.execute_script.side_effect = script_side_effect
                
                # Mock ConversationState.store_execution_result
                with patch('app.services.staged_module_resolver.ConversationState.store_execution_result'):
                    results = self.resolver.execute_post_response_modules(
                        persona_id, conversation_id, self.mock_session
                    )
                    
                    assert len(results) == 2
                    
                    # Check that stage 4 (non-AI) executed first
                    stage4_results = [r for r in results if r.stage == 4]
                    stage5_results = [r for r in results if r.stage == 5]
                    
                    assert len(stage4_results) == 1
                    assert len(stage5_results) == 1
                    
                    assert stage4_results[0].module_name == "logger"
                    assert stage5_results[0].module_name == "reflector"
    
    def test_previous_state_resolution(self):
        """Test resolution using previous POST_RESPONSE state."""
        module = Module(
            id=uuid.uuid4(),
            name="state_module",
            type=ModuleType.ADVANCED,
            execution_context=ExecutionContext.POST_RESPONSE,
            content="Previous mood: ${mood}",
            is_active=True
        )
        
        conversation_id = str(uuid.uuid4())
        
        # Mock ConversationState query
        mock_state = Mock()
        mock_state.variables = {"mood": "happy"}
        
        with patch('app.services.staged_module_resolver.ConversationState.get_latest_for_module') as mock_get_state:
            mock_get_state.return_value = mock_state
            
            result = self.resolver._resolve_variables_with_previous_state(
                module.content, module, conversation_id, self.mock_session
            )
            
            assert result == "Previous mood: happy"
            mock_get_state.assert_called_once_with(self.mock_session, conversation_id, str(module.id))
    
    def test_module_name_validation(self):
        """Test module name validation."""
        valid_names = ["module", "module_123", "test_module", "a", "a1b2c3"]
        invalid_names = ["", "Module", "123module", "module-name", "module.name", "a" * 51]
        
        for name in valid_names:
            assert StagedModuleResolver.validate_module_name(name), f"Should be valid: {name}"
        
        for name in invalid_names:
            assert not StagedModuleResolver.validate_module_name(name), f"Should be invalid: {name}"
    
    def test_error_handling(self):
        """Test error handling in various scenarios."""
        # Test template resolution with database error
        with patch('app.services.staged_module_resolver.Module.get_modules_for_stage') as mock_get_modules:
            mock_get_modules.side_effect = Exception("Database error")
            
            result = self.resolver.resolve_template_stage1_and_stage2(
                "@test_module", self.conversation_id, self.persona_id, self.mock_session
            )
            
            # Should return original template (errors are logged but don't create warnings in this implementation)
            assert "@test_module" in result.resolved_template
            assert result.stages_executed == [1, 2]  # Stages still executed despite errors
    
    def test_convenience_function(self):
        """Test the convenience function."""
        template = "Hello world!"
        
        with patch('app.services.staged_module_resolver.get_db') as mock_get_db:
            mock_session = Mock()
            mock_get_db.return_value = iter([mock_session])
            
            with patch('app.services.staged_module_resolver.Module.get_modules_for_stage') as mock_get_modules:
                mock_get_modules.return_value.all.return_value = []
                
                result = resolve_template_for_response(template)
                
                assert isinstance(result, StagedTemplateResolutionResult)
                assert result.resolved_template == template
    
    def test_trigger_pattern_matching(self):
        """Test that trigger patterns are respected."""
        module = Module(
            id=uuid.uuid4(),
            name="triggered_module",
            type=ModuleType.ADVANCED,
            execution_context=ExecutionContext.IMMEDIATE,
            content="Triggered: ${result}",
            script='result = "executed"',
            trigger_pattern="user_message_count > 5",
            is_active=True
        )
        
        # Mock trigger matcher to return False
        with patch('app.services.staged_module_resolver.TriggerMatcher.should_execute') as mock_trigger:
            mock_trigger.return_value = False
            
            result = self.resolver._process_advanced_module(
                module, module.content, 1, self.conversation_id, self.persona_id,
                self.mock_session, {}, [], None, None, None
            )
            
            # Should return content with unresolved variables since trigger didn't match
            assert result == "Triggered: ${result}"
            mock_trigger.assert_called_once_with("user_message_count > 5", {})


class TestExecutionStageEnum:
    """Test the ExecutionStage enum."""
    
    def test_enum_values(self):
        """Test enum values are correct."""
        assert ExecutionStage.STAGE1.value == 1
        assert ExecutionStage.STAGE2.value == 2
        assert ExecutionStage.STAGE4.value == 4
        assert ExecutionStage.STAGE5.value == 5
    
    def test_enum_ordering(self):
        """Test that stages are in correct order."""
        stages = list(ExecutionStage)
        assert len(stages) == 4
        
        # Verify we have all expected stages
        stage_values = [s.value for s in stages]
        assert set(stage_values) == {1, 2, 4, 5}


class TestDataClasses:
    """Test the dataclasses used by StagedModuleResolver."""
    
    def test_module_resolution_warning(self):
        """Test ModuleResolutionWarning dataclass."""
        warning = ModuleResolutionWarning(
            module_name="test_module",
            warning_type="module_not_found",
            message="Module not found in database",
            stage=1
        )
        
        assert warning.module_name == "test_module"
        assert warning.warning_type == "module_not_found"
        assert warning.message == "Module not found in database"
        assert warning.stage == 1
    
    def test_staged_template_resolution_result(self):
        """Test StagedTemplateResolutionResult dataclass."""
        result = StagedTemplateResolutionResult(
            resolved_template="Hello world!",
            warnings=[],
            resolved_modules=["greeting"],
            stages_executed=[1, 2]
        )
        
        assert result.resolved_template == "Hello world!"
        assert result.warnings == []
        assert result.resolved_modules == ["greeting"]
        assert result.stages_executed == [1, 2]
    
    def test_post_response_execution_result(self):
        """Test PostResponseExecutionResult dataclass."""
        result = PostResponseExecutionResult(
            module_name="feedback",
            stage=4,
            variables={"sentiment": "positive"},
            execution_metadata={"success": True},
            success=True
        )
        
        assert result.module_name == "feedback"
        assert result.stage == 4
        assert result.variables == {"sentiment": "positive"}
        assert result.success is True
        assert result.error_message is None


class TestStagedModuleResolverWithSystemPromptState:
    """Test StagedModuleResolver integration with SystemPromptState tracking."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_session = Mock()
        self.resolver = StagedModuleResolver(self.mock_session)
        self.conversation_id = str(uuid.uuid4())
        self.persona_id = str(uuid.uuid4())
        self.original_template = "You are an AI assistant. @greeting @context"
    
    @patch('app.services.staged_module_resolver.SystemPromptState')
    @patch('app.services.staged_module_resolver.PromptStateManager')
    def test_resolver_creates_initial_state(self, mock_manager_class, mock_state_class):
        """Test that resolver creates SystemPromptState for tracking."""
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        
        mock_state = Mock()
        mock_manager.create_initial_state.return_value = mock_state
        
        # Enable state tracking
        self.resolver.enable_state_tracking()
        
        template = "Hello @greeting"
        result = self.resolver.resolve_template_stage1_and_stage2(
            template, self.conversation_id, self.persona_id, self.mock_session
        )
        
        # Verify state manager was created and initial state set up
        mock_manager_class.assert_called_once()
        mock_manager.create_initial_state.assert_called_once_with(
            self.conversation_id, self.persona_id, template
        )
    
    @patch('app.services.staged_module_resolver.SystemPromptState')
    @patch('app.services.staged_module_resolver.PromptStateManager')
    @patch('app.services.staged_module_resolver.Module.get_modules_for_stage')
    def test_stage1_completion_state_update(self, mock_get_modules, mock_manager_class, mock_state_class):
        """Test SystemPromptState update after Stage 1 completion."""
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        
        mock_state = Mock()
        mock_manager.create_initial_state.return_value = mock_state
        mock_manager.update_stage1_completion.return_value = mock_state
        
        # Mock simple module for Stage 1
        simple_module = Module(
            id=uuid.uuid4(),
            name="greeting",
            type=ModuleType.SIMPLE,
            execution_context=ExecutionContext.IMMEDIATE,
            content="Hello there!",
            is_active=True
        )
        
        def stage_side_effect(db_session, stage, persona_id=None):
            mock_query = Mock()
            if stage == 1:
                mock_query.all.return_value = [simple_module]
            else:
                mock_query.all.return_value = []
            return mock_query
        
        mock_get_modules.side_effect = stage_side_effect
        
        # Enable state tracking
        self.resolver.enable_state_tracking()
        
        template = "Welcome @greeting"
        result = self.resolver.resolve_template_stage1_and_stage2(
            template, self.conversation_id, self.persona_id, self.mock_session
        )
        
        # Verify Stage 1 completion was recorded
        mock_manager.update_stage1_completion.assert_called_once()
        args = mock_manager.update_stage1_completion.call_args[0]
        assert args[0] == mock_state  # state
        assert "Welcome Hello there!" in args[1]  # resolved_template
        assert "greeting" in args[2]  # resolved_modules
        # execution_time should be > 0
        assert args[4] > 0
    
    @patch('app.services.staged_module_resolver.SystemPromptState')
    @patch('app.services.staged_module_resolver.PromptStateManager')
    @patch('app.services.staged_module_resolver.ScriptEngine')
    @patch('app.services.staged_module_resolver.Module.get_modules_for_stage')
    def test_stage2_ai_module_with_state_tracking(self, mock_get_modules, mock_engine_class, mock_manager_class, mock_state_class):
        """Test Stage 2 AI module execution with state tracking."""
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        
        mock_state = Mock()
        mock_state.get_prompt_for_stage.return_value = "Stage1 resolved content"
        mock_manager.create_initial_state.return_value = mock_state
        mock_manager.update_stage1_completion.return_value = mock_state
        mock_manager.update_stage2_completion.return_value = mock_state
        mock_manager.finalize_state.return_value = mock_state  # Return same state after finalization
        
        # Mock AI module for Stage 2
        ai_module = Module(
            id=uuid.uuid4(),
            name="context_analyzer",
            type=ModuleType.ADVANCED,
            execution_context=ExecutionContext.IMMEDIATE,
            content="Context: ${analysis}",
            script='analysis = ctx.generate("Analyze context")',
            requires_ai_inference=True,
            is_active=True
        )
        
        def stage_side_effect(db_session, stage, persona_id=None):
            mock_query = Mock()
            if stage == 1:
                mock_query.all.return_value = []
            elif stage == 2:
                mock_query.all.return_value = [ai_module]
            return mock_query
        
        mock_get_modules.side_effect = stage_side_effect
        
        # Mock script engine execution
        mock_engine = Mock()
        mock_engine_class.return_value = mock_engine
        
        # Mock successful script execution result
        mock_result = Mock()
        mock_result.success = True
        mock_result.outputs = {"analysis": "Positive conversation"}
        mock_engine.execute_script.return_value = mock_result
        
        # Enable state tracking
        self.resolver.enable_state_tracking()
        
        template = "Hello @context_analyzer"
        result = self.resolver.resolve_template_stage1_and_stage2(
            template, self.conversation_id, self.persona_id, self.mock_session
        )
        
        # Verify Stage 2 completion was recorded (loose coupling - no state consultation during execution)
        mock_manager.update_stage2_completion.assert_called_once()
        args = mock_manager.update_stage2_completion.call_args[0]
        assert args[0] == mock_state  # state
        assert "Context: Positive conversation" in args[1]  # resolved_template
        assert "context_analyzer" in args[2]  # additional_modules
    
    @patch('app.services.staged_module_resolver.SystemPromptState')  
    @patch('app.services.staged_module_resolver.PromptStateManager')
    @patch('app.services.staged_module_resolver.ScriptEngine')
    def test_post_response_stage4_with_state_tracking(self, mock_engine_class, mock_manager_class, mock_state_class):
        """Test POST_RESPONSE Stage 4 execution with state tracking."""
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        
        mock_state = Mock()
        mock_manager.create_initial_state.return_value = mock_state
        mock_manager.update_stage4_completion.return_value = mock_state
        mock_manager.finalize_state.return_value = mock_state  # Return same state after finalization
        
        # Mock non-AI POST_RESPONSE module
        post_module = Module(
            id=uuid.uuid4(),
            name="message_counter",
            type=ModuleType.ADVANCED,
            execution_context=ExecutionContext.POST_RESPONSE,
            script='count = ctx.get_message_count()',
            requires_ai_inference=False,
            is_active=True
        )
        
        # Mock script engine execution
        mock_engine = Mock()
        mock_engine_class.return_value = mock_engine
        
        # Mock successful script execution result
        mock_result = Mock()
        mock_result.success = True
        mock_result.outputs = {"count": 15}
        mock_engine.execute_script.return_value = mock_result
        
        # Enable state tracking
        self.resolver.enable_state_tracking()
        
        # Execute POST_RESPONSE modules
        results = self.resolver.execute_post_response_modules(
            self.conversation_id, self.persona_id, self.mock_session, [post_module]
        )
        
        # Verify Stage 4 completion was recorded
        mock_manager.update_stage4_completion.assert_called_once()
        args = mock_manager.update_stage4_completion.call_args[0]
        assert args[0] == mock_state  # state
        assert args[1] == {"message_counter": {"count": 15}}  # variables
        assert args[2] > 0  # execution_time
    
    @patch('app.services.staged_module_resolver.SystemPromptState')
    @patch('app.services.staged_module_resolver.PromptStateManager')
    @patch('app.services.staged_module_resolver.ScriptEngine')
    def test_post_response_stage5_with_state_tracking(self, mock_engine_class, mock_manager_class, mock_state_class):
        """Test POST_RESPONSE Stage 5 AI execution with state tracking."""
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        
        mock_state = Mock()
        mock_state.get_prompt_for_stage.return_value = "Main prompt with Stage 4 context"
        mock_manager.create_initial_state.return_value = mock_state
        mock_manager.update_stage4_completion.return_value = mock_state  # Stage 4 returns same state
        mock_manager.update_stage5_completion.return_value = mock_state
        mock_manager.finalize_state.return_value = mock_state  # Return same state after finalization
        
        # Mock AI POST_RESPONSE module
        ai_post_module = Module(
            id=uuid.uuid4(),
            name="response_assessor",
            type=ModuleType.ADVANCED,
            execution_context=ExecutionContext.POST_RESPONSE,
            script='quality = ctx.reflect("Rate this response 1-10")',
            requires_ai_inference=True,
            is_active=True
        )
        
        # Mock script engine execution
        mock_engine = Mock()
        mock_engine_class.return_value = mock_engine
        
        # Mock successful script execution result
        mock_result = Mock()
        mock_result.success = True
        mock_result.outputs = {"quality": "8/10"}
        mock_engine.execute_script.return_value = mock_result
        
        # Enable state tracking
        self.resolver.enable_state_tracking()
        
        # Execute POST_RESPONSE modules
        results = self.resolver.execute_post_response_modules(
            self.conversation_id, self.persona_id, self.mock_session, [ai_post_module]
        )
        
        # Verify Stage 5 completion was recorded (loose coupling - no state consultation during execution)
        mock_manager.update_stage5_completion.assert_called_once()
        args = mock_manager.update_stage5_completion.call_args[0]
        assert args[0] == mock_state  # state
        assert args[1] == {"response_assessor": {"quality": "8/10"}}  # variables
        assert args[2] > 0  # execution_time
    
    @patch('app.services.staged_module_resolver.SystemPromptState')
    @patch('app.services.staged_module_resolver.PromptStateManager')
    def test_state_finalization(self, mock_manager_class, mock_state_class):
        """Test SystemPromptState finalization with total execution time."""
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        
        mock_state = Mock()
        mock_manager.create_initial_state.return_value = mock_state
        mock_manager.update_stage1_completion.return_value = mock_state  # All stage completions return same state
        mock_manager.update_stage2_completion.return_value = mock_state
        mock_manager.finalize_state.return_value = mock_state  # Return same state after finalization
        
        # Enable state tracking
        self.resolver.enable_state_tracking()
        
        template = "Simple template"
        result = self.resolver.resolve_template_stage1_and_stage2(
            template, self.conversation_id, self.persona_id, self.mock_session
        )
        
        # Finalize state should be called at the end
        mock_manager.finalize_state.assert_called_once_with(mock_state)
    
    @patch('app.services.staged_module_resolver.SystemPromptState')
    @patch('app.services.staged_module_resolver.PromptStateManager')
    def test_get_current_state(self, mock_manager_class, mock_state_class):
        """Test getting current SystemPromptState during execution."""
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        
        mock_state = Mock()
        mock_manager.create_initial_state.return_value = mock_state
        mock_manager.finalize_state.return_value = mock_state  # Return same state after finalization
        
        # Enable state tracking
        self.resolver.enable_state_tracking()
        
        # Before any execution, state should be None
        assert self.resolver.get_current_state() is None
        
        # After starting resolution, state should be available
        template = "Hello world"
        result = self.resolver.resolve_template_stage1_and_stage2(
            template, self.conversation_id, self.persona_id, self.mock_session
        )
        
        current_state = self.resolver.get_current_state()
        assert current_state == mock_state
    
    @patch('app.services.staged_module_resolver.SystemPromptState')
    @patch('app.services.staged_module_resolver.PromptStateManager')
    def test_state_tracking_disabled_by_default(self, mock_manager_class, mock_state_class):
        """Test that state tracking is disabled by default."""
        # Don't enable state tracking
        template = "Hello world"
        result = self.resolver.resolve_template_stage1_and_stage2(
            template, self.conversation_id, self.persona_id, self.mock_session
        )
        
        # No state manager should be created
        mock_manager_class.assert_not_called()
        
        # Current state should be None
        assert self.resolver.get_current_state() is None
    
    @patch('app.services.staged_module_resolver.SystemPromptState')
    @patch('app.services.staged_module_resolver.PromptStateManager')
    def test_debug_summary_generation(self, mock_manager_class, mock_state_class):
        """Test generation of debug summary from SystemPromptState."""
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        
        mock_state = Mock()
        mock_manager.create_initial_state.return_value = mock_state
        mock_manager.finalize_state.return_value = mock_state  # Return same state after finalization
        
        debug_summary = {
            "conversation_id": self.conversation_id,
            "persona_id": self.persona_id,
            "prompt_evolution": {"original": "test", "stage1": "test resolved"},
            "performance_metrics": {"total_time": 0.15}
        }
        mock_manager.get_debug_summary.return_value = debug_summary
        
        # Enable state tracking
        self.resolver.enable_state_tracking()
        
        template = "Test template"
        result = self.resolver.resolve_template_stage1_and_stage2(
            template, self.conversation_id, self.persona_id, self.mock_session
        )
        
        # Get debug summary (should use finalized state)
        summary = self.resolver.get_debug_summary()
        assert summary == debug_summary
        # Should be called with the finalized state (after finalize_state is called)
        mock_manager.get_debug_summary.assert_called_once()
    
    @patch('app.services.staged_module_resolver.SystemPromptState')
    @patch('app.services.staged_module_resolver.PromptStateManager')
    def test_performance_summary_generation(self, mock_manager_class, mock_state_class):
        """Test generation of performance summary from SystemPromptState."""
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        
        mock_state = Mock()
        mock_manager.create_initial_state.return_value = mock_state
        mock_manager.finalize_state.return_value = mock_state  # Return same state after finalization
        
        performance_summary = {
            "total_time": 0.25,
            "slowest_stage": 2,
            "fastest_stage": 1,
            "ai_stages_time": 0.20,
            "non_ai_stages_time": 0.05
        }
        mock_state.get_performance_summary.return_value = performance_summary
        
        # Enable state tracking
        self.resolver.enable_state_tracking()
        
        template = "Test template"
        result = self.resolver.resolve_template_stage1_and_stage2(
            template, self.conversation_id, self.persona_id, self.mock_session
        )
        
        # Get performance summary (should work with finalized state)
        summary = self.resolver.get_performance_summary()
        assert summary == performance_summary
        # The finalized state should have get_performance_summary called on it
        # Since finalize_state returns a state, we need to check the return value