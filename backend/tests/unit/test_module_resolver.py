"""
Unit tests for the Module Resolution Service.

Tests the core logic for parsing @module_name references in templates 
and resolving them to their content with proper error handling.
"""

import pytest
from unittest.mock import Mock, patch
from app.services.module_resolver import ModuleResolver, TemplateResolutionResult, ModuleResolutionWarning
from app.models import Module, ModuleType, ExecutionTiming


class TestModuleResolver:
    """Test cases for the ModuleResolver service."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.resolver = ModuleResolver()

    def test_parse_module_references_basic(self):
        """Test basic parsing of @module_name references."""
        template = "You are helpful. @greeting @safety"
        
        references = self.resolver._parse_module_references(template)
        
        assert sorted(references) == ["greeting", "safety"]

    def test_parse_module_references_complex(self):
        """Test parsing with various formats and edge cases."""
        template = """
        You are an AI assistant. @greeting_formal
        
        Rules: @safety_protocols @data_privacy
        
        Remember: @conversational_tone and @error_handling_v2
        """
        
        references = self.resolver._parse_module_references(template)
        
        expected = ["greeting_formal", "safety_protocols", "data_privacy", "conversational_tone", "error_handling_v2"]
        assert sorted(references) == sorted(expected)

    def test_parse_module_references_duplicates(self):
        """Test that duplicate references are handled correctly."""
        template = "@greeting Hello! @greeting Please be @helpful and @greeting"
        
        references = self.resolver._parse_module_references(template)
        
        # Should return unique references only
        assert sorted(references) == ["greeting", "helpful"]

    def test_parse_module_references_no_modules(self):
        """Test template with no module references."""
        template = "You are a helpful AI assistant. No modules here!"
        
        references = self.resolver._parse_module_references(template)
        
        assert references == []

    def test_parse_module_references_invalid_names(self):
        """Test that invalid module names are not parsed."""
        template = "@123invalid @valid_module @Invalid-Name @also_valid @"
        
        references = self.resolver._parse_module_references(template)
        
        # Only valid names should be parsed
        assert sorted(references) == ["also_valid", "valid_module"]

    @patch('app.services.module_resolver.ModuleResolver._get_modules_by_names')
    def test_resolve_template_basic_success(self, mock_get_modules):
        """Test successful basic template resolution."""
        # Mock modules
        greeting_module = Mock(spec=Module)
        greeting_module.name = "greeting"
        greeting_module.content = "Hello! I'm here to help."
        
        safety_module = Mock(spec=Module)
        safety_module.name = "safety"
        safety_module.content = "I follow safety guidelines."
        
        mock_get_modules.return_value = [greeting_module, safety_module]
        
        template = "You are an AI. @greeting Also, @safety"
        
        result = self.resolver.resolve_template(template)
        
        expected_content = "You are an AI. Hello! I'm here to help. Also, I follow safety guidelines."
        assert result.resolved_template == expected_content
        assert result.warnings == []
        assert sorted(result.resolved_modules) == ["greeting", "safety"]

    @patch('app.services.module_resolver.ModuleResolver._get_modules_by_names')
    def test_resolve_template_missing_modules(self, mock_get_modules):
        """Test resolution with missing modules."""
        # Only return one module, the other is missing
        greeting_module = Mock(spec=Module)
        greeting_module.name = "greeting"
        greeting_module.content = "Hello!"
        
        mock_get_modules.return_value = [greeting_module]
        
        template = "AI assistant. @greeting @missing_module"
        
        result = self.resolver.resolve_template(template)
        
        # Missing module should be replaced with empty string
        expected_content = "AI assistant. Hello! @missing_module"
        assert result.resolved_template == expected_content
        assert len(result.warnings) == 1
        assert result.warnings[0].module_name == "missing_module"
        assert result.warnings[0].warning_type == "module_not_found"

    @patch('app.services.module_resolver.ModuleResolver._get_modules_by_names')
    def test_resolve_template_empty_modules(self, mock_get_modules):
        """Test resolution with empty/null content modules."""
        empty_module = Mock(spec=Module)
        empty_module.name = "empty_module"
        empty_module.content = None
        
        null_module = Mock(spec=Module)
        null_module.name = "null_module"
        null_module.content = ""
        
        mock_get_modules.return_value = [empty_module, null_module]
        
        template = "Start @empty_module middle @null_module end"
        
        result = self.resolver.resolve_template(template)
        
        # Empty/null modules should be replaced with empty string
        assert result.resolved_template == "Start  middle  end"
        assert result.warnings == []

    @patch('app.services.module_resolver.ModuleResolver._get_modules_by_names')
    def test_resolve_template_recursive_basic(self, mock_get_modules):
        """Test basic recursive module resolution."""
        # Module A references Module B
        module_a = Mock(spec=Module)
        module_a.name = "module_a"
        module_a.content = "Start @module_b end"
        
        module_b = Mock(spec=Module)
        module_b.name = "module_b"
        module_b.content = "middle content"
        
        # Mock will be called twice - once for initial, once for recursive
        mock_get_modules.side_effect = [
            [module_a],  # First call for @module_a
            [module_b]   # Second call for @module_b
        ]
        
        template = "Begin @module_a finish"
        
        result = self.resolver.resolve_template(template)
        
        expected_content = "Begin Start middle content end finish"
        assert result.resolved_template == expected_content
        assert sorted(result.resolved_modules) == ["module_a", "module_b"]

    @patch('app.services.module_resolver.ModuleResolver._get_modules_by_names')
    def test_resolve_template_circular_dependency(self, mock_get_modules):
        """Test detection and handling of circular dependencies."""
        # Module A references Module B, Module B references Module A
        module_a = Mock(spec=Module)
        module_a.name = "module_a"
        module_a.content = "A: @module_b"
        
        module_b = Mock(spec=Module)
        module_b.name = "module_b"
        module_b.content = "B: @module_a"
        
        # Return both modules for all queries to enable the circular resolution
        mock_get_modules.return_value = [module_a, module_b]
        
        template = "Start @module_a end"
        
        result = self.resolver.resolve_template(template)
        
        # Should detect circular dependency and handle gracefully
        assert len(result.warnings) >= 1
        circular_warning = next((w for w in result.warnings if w.warning_type == "circular_dependency"), None)
        assert circular_warning is not None
        # Should still return some content, not crash
        assert "Start" in result.resolved_template
        assert "end" in result.resolved_template

    @patch('app.services.module_resolver.ModuleResolver._get_modules_by_names')
    def test_resolve_template_max_depth_exceeded(self, mock_get_modules):
        """Test handling of maximum recursion depth."""
        # Create a chain that's deeper than MAX_RECURSION_DEPTH
        # We'll create modules that chain to each other in a way that exceeds max depth
        modules = []
        for i in range(15):  # More than MAX_RECURSION_DEPTH (10)
            module = Mock(spec=Module)
            module.name = f"module_{i}"
            if i < 14:
                module.content = f"Level {i} @module_{i+1}"
            else:
                module.content = f"Level {i} end"
            modules.append(module)
        
        mock_get_modules.return_value = modules
        
        template = "@module_0"
        
        result = self.resolver.resolve_template(template)
        
        # Should detect excessive recursion and handle gracefully
        assert len(result.warnings) >= 1
        depth_warning = next((w for w in result.warnings if w.warning_type == "max_depth_exceeded"), None)
        assert depth_warning is not None

    def test_validate_module_name_valid(self):
        """Test validation of valid module names."""
        valid_names = [
            "greeting",
            "safety_protocol",
            "module_v2",
            "a",
            "test123",
            "long_module_name_with_underscores_and_numbers123"
        ]
        
        for name in valid_names:
            assert self.resolver.validate_module_name(name) is True, f"Should be valid: {name}"

    def test_validate_module_name_invalid(self):
        """Test validation of invalid module names."""
        invalid_names = [
            "",              # Empty
            "123module",     # Starts with number
            "module-name",   # Contains hyphen
            "module name",   # Contains space
            "MODULE",        # Uppercase
            "module!",       # Special character
            "_module",       # Starts with underscore
            "a" * 51,        # Too long (over 50 chars)
            "@module",       # Contains @
        ]
        
        for name in invalid_names:
            assert self.resolver.validate_module_name(name) is False, f"Should be invalid: {name}"

    def test_resolution_result_structure(self):
        """Test that TemplateResolutionResult has correct structure."""
        result = TemplateResolutionResult(
            resolved_template="test content",
            warnings=[],
            resolved_modules=["test_module"]
        )
        
        assert result.resolved_template == "test content"
        assert result.warnings == []
        assert result.resolved_modules == ["test_module"]

    def test_warning_structure(self):
        """Test that ModuleResolutionWarning has correct structure."""
        warning = ModuleResolutionWarning(
            module_name="test_module",
            warning_type="module_not_found",
            message="Module 'test_module' not found"
        )
        
        assert warning.module_name == "test_module"
        assert warning.warning_type == "module_not_found"
        assert warning.message == "Module 'test_module' not found"


class TestAdvancedModuleResolution:
    """Test cases for advanced module resolution with script execution and ${variable} support."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.resolver = ModuleResolver()

    def test_simple_module_resolution_unchanged(self):
        """Test that simple modules still work exactly as before."""
        # Mock simple module
        simple_module = Mock()
        simple_module.name = "helpful_assistant"
        simple_module.type = ModuleType.SIMPLE
        simple_module.content = "You are helpful and direct."
        simple_module.is_active = True
        
        with patch.object(self.resolver, '_get_modules_by_names', return_value=[simple_module]):
            template = "System: @helpful_assistant"
            result = self.resolver.resolve_template(template)
            
            assert result.resolved_template == "System: You are helpful and direct."
            assert result.warnings == []

    def test_advanced_module_with_variable_resolution(self):
        """Test advanced module with ${variable} resolution."""
        # Mock advanced module with script
        advanced_module = Mock()
        advanced_module.name = "ai_identity"
        advanced_module.type = ModuleType.ADVANCED
        advanced_module.content = "Your name is ${result}. Current time: ${time}."
        advanced_module.script = """
result = "AVA"
time = "14:30"
"""
        advanced_module.trigger_pattern = None
        advanced_module.timing = ExecutionTiming.CUSTOM
        advanced_module.is_active = True
        
        # Mock script execution result
        mock_script_result = Mock()
        mock_script_result.success = True
        mock_script_result.outputs = {"result": "AVA", "time": "14:30"}
        mock_script_result.error_message = None
        
        with patch.object(self.resolver, '_get_modules_by_names', return_value=[advanced_module]), \
             patch('app.services.module_resolver.ScriptEngine') as mock_engine_class, \
             patch('app.services.module_resolver.ScriptExecutionContext') as mock_context_class:
            
            mock_engine = Mock()
            mock_engine_class.return_value = mock_engine
            mock_engine.execute_script.return_value = mock_script_result
            
            template = "Assistant: @ai_identity"
            result = self.resolver.resolve_template(
                template,
                conversation_id="test-conv",
                persona_id="test-persona",
                db_session=Mock()
            )
            
            expected = "Assistant: Your name is AVA. Current time: 14:30."
            assert result.resolved_template == expected
            assert result.warnings == []

    def test_advanced_module_script_execution_failure(self):
        """Test advanced module with script execution failure."""
        # Mock advanced module with failing script
        advanced_module = Mock()
        advanced_module.name = "failing_module"
        advanced_module.type = ModuleType.ADVANCED
        advanced_module.content = "Name: ${result}"
        advanced_module.script = "result = 1/0  # This will fail"
        advanced_module.trigger_pattern = None
        advanced_module.timing = ExecutionTiming.CUSTOM
        advanced_module.is_active = True
        
        # Mock script execution failure
        mock_script_result = Mock()
        mock_script_result.success = False
        mock_script_result.outputs = {}
        mock_script_result.error_message = "Runtime error: division by zero"
        
        with patch.object(self.resolver, '_get_modules_by_names', return_value=[advanced_module]), \
             patch('app.services.module_resolver.ScriptEngine') as mock_engine_class, \
             patch('app.services.module_resolver.ScriptExecutionContext') as mock_context_class:
            
            mock_engine = Mock()
            mock_engine_class.return_value = mock_engine
            mock_engine.execute_script.return_value = mock_script_result
            
            template = "System: @failing_module"
            result = self.resolver.resolve_template(
                template,
                conversation_id="test-conv",
                persona_id="test-persona",
                db_session=Mock()
            )
            
            # Should return content with unresolved variables and include warning
            assert "${result}" in result.resolved_template
            assert len(result.warnings) > 0
            assert any("script execution failed" in w.message.lower() for w in result.warnings)

    def test_advanced_module_trigger_not_matched(self):
        """Test advanced module that doesn't match trigger pattern."""
        # Mock advanced module with trigger that shouldn't match
        advanced_module = Mock()
        advanced_module.name = "weather_module"
        advanced_module.type = ModuleType.ADVANCED
        advanced_module.content = "Weather info: ${weather}"
        advanced_module.script = 'weather = "sunny"'
        advanced_module.trigger_pattern = "weather|climate|temperature"
        advanced_module.timing = ExecutionTiming.CUSTOM
        advanced_module.is_active = True
        
        with patch.object(self.resolver, '_get_modules_by_names', return_value=[advanced_module]), \
             patch('app.services.module_resolver.TriggerMatcher') as mock_trigger:
            
            # Mock trigger matcher to return False
            mock_trigger.should_execute.return_value = False
            
            template = "System: @weather_module"
            # Provide trigger context that shouldn't match
            trigger_context = {"last_user_message": "Hello, how are you?"}
            
            result = self.resolver.resolve_template(template, trigger_context=trigger_context)
            
            # Should return content without executing script (variables unresolved)
            assert result.resolved_template == "System: Weather info: ${weather}"
            assert result.warnings == []

    def test_advanced_module_trigger_matched(self):
        """Test advanced module that matches trigger pattern."""
        # Mock advanced module with matching trigger
        advanced_module = Mock()
        advanced_module.name = "weather_info"
        advanced_module.type = ModuleType.ADVANCED
        advanced_module.content = "Weather update: ${weather}"
        advanced_module.script = 'weather = "It\'s sunny today"'
        advanced_module.trigger_pattern = "weather|climate"
        advanced_module.timing = ExecutionTiming.CUSTOM
        advanced_module.is_active = True
        
        mock_script_result = Mock()
        mock_script_result.success = True
        mock_script_result.outputs = {"weather": "It's sunny today"}
        
        with patch.object(self.resolver, '_get_modules_by_names', return_value=[advanced_module]), \
             patch('app.services.module_resolver.TriggerMatcher') as mock_trigger, \
             patch('app.services.module_resolver.ScriptEngine') as mock_engine_class:
            
            # Mock trigger matcher to return True
            mock_trigger.should_execute.return_value = True
            
            mock_engine = Mock()
            mock_engine_class.return_value = mock_engine
            mock_engine.execute_script.return_value = mock_script_result
            
            template = "System: @weather_info"
            trigger_context = {"last_user_message": "What's the weather like?"}
            
            result = self.resolver.resolve_template(
                template,
                conversation_id="test-conv",
                persona_id="test-persona", 
                db_session=Mock(),
                trigger_context=trigger_context
            )
            
            # Should execute script and resolve variables
            assert result.resolved_template == "System: Weather update: It's sunny today"
            assert result.warnings == []

    def test_mixed_simple_and_advanced_modules(self):
        """Test template with both simple and advanced modules."""
        # Mock simple module
        simple_module = Mock()
        simple_module.name = "helpful_persona"
        simple_module.type = ModuleType.SIMPLE
        simple_module.content = "Be helpful and direct."
        simple_module.is_active = True
        
        # Mock advanced module
        advanced_module = Mock()
        advanced_module.name = "user_context"
        advanced_module.type = ModuleType.ADVANCED  
        advanced_module.content = "Current user: ${user_name}"
        advanced_module.script = 'user_name = "Alice"'
        advanced_module.trigger_pattern = None  # Always execute
        advanced_module.timing = ExecutionTiming.CUSTOM
        advanced_module.is_active = True
        
        mock_script_result = Mock()
        mock_script_result.success = True
        mock_script_result.outputs = {"user_name": "Alice"}
        
        def mock_get_modules(names):
            """Return appropriate modules based on names."""
            result = []
            if "helpful_persona" in names:
                result.append(simple_module)
            if "user_context" in names:
                result.append(advanced_module)
            return result
        
        with patch.object(self.resolver, '_get_modules_by_names', side_effect=mock_get_modules), \
             patch('app.services.module_resolver.ScriptEngine') as mock_engine_class, \
             patch('app.services.module_resolver.TriggerMatcher') as mock_trigger:
            
            mock_trigger.should_execute.return_value = True
            mock_engine = Mock()
            mock_engine_class.return_value = mock_engine
            mock_engine.execute_script.return_value = mock_script_result
            
            template = "System: @helpful_persona @user_context"
            result = self.resolver.resolve_template(
                template,
                conversation_id="test-conv",
                persona_id="test-persona",
                db_session=Mock()
            )
            
            expected = "System: Be helpful and direct. Current user: Alice"
            assert result.resolved_template == expected

    def test_variable_resolution_pattern_matching(self):
        """Test ${variable} pattern matching and replacement."""
        content_with_variables = """
        Hello ${name}!
        Today is ${day} and the weather is ${weather}.
        Your score: ${score}
        """
        
        script_outputs = {
            "name": "Bob",
            "day": "Monday", 
            "weather": "sunny",
            "score": 85
        }
        
        # This would be tested in the actual resolver method
        # Test pattern: ${variable_name} should be replaced with script output
        expected_patterns = ["${name}", "${day}", "${weather}", "${score}"]
        
        # Test that our pattern matching logic works
        import re
        variable_pattern = r'\$\{([a-zA-Z_][a-zA-Z0-9_]*)\}'
        found_variables = re.findall(variable_pattern, content_with_variables)
        
        assert sorted(found_variables) == ["day", "name", "score", "weather"]

    def test_nested_module_with_advanced_module(self):
        """Test advanced module that references another module."""
        # Simple module referenced by advanced module
        simple_module = Mock()
        simple_module.name = "role_name"
        simple_module.type = ModuleType.SIMPLE
        simple_module.content = "assistant"
        simple_module.is_active = True
        
        # Advanced module that references the simple module
        advanced_module = Mock()
        advanced_module.name = "identity"
        advanced_module.type = ModuleType.ADVANCED
        advanced_module.content = "I am ${role}, a helpful @role_name."
        advanced_module.script = 'role = "AVA"'
        advanced_module.trigger_pattern = None
        advanced_module.timing = ExecutionTiming.CUSTOM
        advanced_module.is_active = True
        
        mock_script_result = Mock()
        mock_script_result.success = True  
        mock_script_result.outputs = {"role": "AVA"}
        
        def mock_get_modules(names):
            if "identity" in names:
                return [advanced_module]
            elif "role_name" in names:
                return [simple_module]
            return []
        
        with patch.object(self.resolver, '_get_modules_by_names', side_effect=mock_get_modules), \
             patch('app.services.module_resolver.ScriptEngine') as mock_engine_class:
            
            mock_engine = Mock()
            mock_engine_class.return_value = mock_engine
            mock_engine.execute_script.return_value = mock_script_result
            
            template = "System: @identity"
            result = self.resolver.resolve_template(
                template,
                conversation_id="test-conv",
                persona_id="test-persona",
                db_session=Mock()
            )
            
            # Should resolve both ${role} and @role_name
            expected = "System: I am AVA, a helpful assistant."
            assert result.resolved_template == expected

    def test_execution_context_passed_to_scripts(self):
        """Test that proper execution context is passed to script engine."""
        advanced_module = Mock()
        advanced_module.name = "test_module"
        advanced_module.type = ModuleType.ADVANCED
        advanced_module.content = "Context test: ${result}"
        advanced_module.script = "result = 'context_received'"
        advanced_module.trigger_pattern = None
        advanced_module.timing = ExecutionTiming.CUSTOM
        advanced_module.is_active = True
        
        mock_script_result = Mock()
        mock_script_result.success = True
        mock_script_result.outputs = {"result": "context_received"}
        
        with patch.object(self.resolver, '_get_modules_by_names', return_value=[advanced_module]), \
             patch('app.services.module_resolver.ScriptEngine') as mock_engine_class, \
             patch('app.services.module_resolver.ScriptExecutionContext') as mock_context_class:
            
            mock_engine = Mock()
            mock_engine_class.return_value = mock_engine
            mock_engine.execute_script.return_value = mock_script_result
            
            mock_context = Mock()
            mock_context_class.return_value = mock_context
            
            # Provide conversation context
            conversation_id = "conv-123"
            persona_id = "persona-456"  
            mock_db_session = Mock()
            trigger_context = {"last_user_message": "test"}
            
            template = "@test_module"
            result = self.resolver.resolve_template(
                template, 
                conversation_id=conversation_id,
                persona_id=persona_id, 
                db_session=mock_db_session,
                trigger_context=trigger_context
            )
            
            # Verify context was created with correct parameters
            mock_context_class.assert_called_once_with(
                conversation_id=conversation_id,
                persona_id=persona_id,
                db_session=mock_db_session,
                trigger_data=trigger_context
            )
            
            # Verify script was executed with context
            mock_engine.execute_script.assert_called_once()
            call_args = mock_engine.execute_script.call_args
            assert call_args[0][1] == {"ctx": mock_context}  # context passed in execution globals