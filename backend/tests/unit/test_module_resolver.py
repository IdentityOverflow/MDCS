"""
Unit tests for the Module Resolution Service.

Tests the core logic for parsing @module_name references in templates 
and resolving them to their content with proper error handling.
"""

import pytest
from unittest.mock import Mock, patch
from app.services.module_resolver import ModuleResolver, TemplateResolutionResult, ModuleResolutionWarning
from app.models import Module, ModuleType


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
        expected_content = "AI assistant. Hello! "
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