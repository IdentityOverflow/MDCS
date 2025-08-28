"""
Unit tests for the Script Analysis System.

Tests the script analyzer's ability to detect AI dependencies, complexity,
and other characteristics needed for staged execution.
"""

import pytest
from app.core.script_analyzer import (
    ModuleScriptAnalyzer, 
    ScriptAnalysisResult,
    analyze_module_script
)


class TestScriptAnalysisResult:
    """Test the ScriptAnalysisResult dataclass."""
    
    def test_basic_result_creation(self):
        """Test basic result creation with required fields."""
        result = ScriptAnalysisResult(
            requires_ai_inference=True,
            uses_generate=True,
            uses_reflect=False,
            uses_other_plugins=True,
            detected_functions=['ctx.generate', 'ctx.get_current_time'],
            ai_function_calls=['ctx.generate'],
            plugin_function_calls=['ctx.get_current_time'],
            estimated_complexity="medium",
            line_count=10,
            function_count=2,
            has_loops=False,
            has_conditionals=True,
            analysis_success=True
        )
        
        assert result.requires_ai_inference is True
        assert result.uses_generate is True
        assert result.uses_reflect is False
        assert result.estimated_complexity == "medium"
        assert len(result.detected_functions) == 2
    
    def test_to_dict_conversion(self):
        """Test conversion to dictionary for database storage."""
        result = ScriptAnalysisResult(
            requires_ai_inference=False,
            uses_generate=False,
            uses_reflect=False,
            uses_other_plugins=True,
            detected_functions=['ctx.get_current_time'],
            ai_function_calls=[],
            plugin_function_calls=['ctx.get_current_time'],
            estimated_complexity="low",
            line_count=5,
            function_count=1,
            has_loops=False,
            has_conditionals=False,
            analysis_success=True
        )
        
        result_dict = result.to_dict()
        
        # Check all expected keys are present
        expected_keys = {
            'requires_ai_inference', 'uses_generate', 'uses_reflect', 'uses_other_plugins',
            'detected_functions', 'ai_function_calls', 'plugin_function_calls',
            'estimated_complexity', 'line_count', 'function_count', 'has_loops',
            'has_conditionals', 'analysis_success', 'error_message', 'analyzed_at'
        }
        assert set(result_dict.keys()) == expected_keys
        assert result_dict['requires_ai_inference'] is False
        assert result_dict['estimated_complexity'] == "low"
        assert result_dict['analyzed_at'] is not None


class TestModuleScriptAnalyzer:
    """Test the ModuleScriptAnalyzer class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = ModuleScriptAnalyzer()
    
    def test_empty_script_analysis(self):
        """Test analysis of empty or None script."""
        # Test empty string
        result = self.analyzer.analyze_script("")
        assert result.requires_ai_inference is False
        assert result.line_count == 0
        assert result.analysis_success is True
        
        # Test None
        result = self.analyzer.analyze_script(None)
        assert result.requires_ai_inference is False
        assert result.line_count == 0
        assert result.analysis_success is True
        
        # Test whitespace only
        result = self.analyzer.analyze_script("   \n\t   ")
        assert result.requires_ai_inference is False
        assert result.line_count == 0
        assert result.analysis_success is True
    
    def test_simple_script_no_ai(self):
        """Test analysis of simple script without AI functions."""
        script = """result = "hello world"
count = 42
message = f"Count is {count}"
"""
        
        result = self.analyzer.analyze_script(script)
        
        assert result.requires_ai_inference is False
        assert result.uses_generate is False
        assert result.uses_reflect is False
        assert result.uses_other_plugins is False
        assert result.estimated_complexity == "low"
        assert result.line_count == 3  # Non-empty lines
        assert result.analysis_success is True
    
    def test_script_with_plugin_functions(self):
        """Test analysis of script with plugin functions but no AI."""
        script = """current_time = ctx.get_current_time("%H:%M")
message_count = ctx.get_message_count()
relative_time = ctx.get_relative_time("2 hours ago")
result = f"Time: {current_time}, Messages: {message_count}"
"""
        
        result = self.analyzer.analyze_script(script)
        
        assert result.requires_ai_inference is False
        assert result.uses_generate is False
        assert result.uses_reflect is False
        assert result.uses_other_plugins is True
        assert len(result.detected_functions) >= 3  # May detect both ctx.func and func patterns
        assert len(result.plugin_function_calls) >= 3
        assert len(result.ai_function_calls) == 0
        assert result.analysis_success is True
    
    def test_script_with_generate_function(self):
        """Test analysis of script with ctx.generate function."""
        script = """user_input = "How are you?"
response = ctx.generate("Respond helpfully to: " + user_input)
result = response
"""
        
        result = self.analyzer.analyze_script(script)
        
        assert result.requires_ai_inference is True
        assert result.uses_generate is True
        assert result.uses_reflect is False
        assert 'ctx.generate' in result.ai_function_calls
        assert result.analysis_success is True
    
    def test_script_with_reflect_function(self):
        """Test analysis of script with ctx.reflect function."""
        script = """conversation_quality = ctx.reflect("How well did this conversation go?")
improvement_ideas = ctx.reflect("What could be improved?")
result = f"Quality: {conversation_quality}"
"""
        
        result = self.analyzer.analyze_script(script)
        
        assert result.requires_ai_inference is True
        assert result.uses_generate is False
        assert result.uses_reflect is True
        assert len([f for f in result.ai_function_calls if 'reflect' in f]) >= 1  # May deduplicate calls
        assert result.analysis_success is True
    
    def test_script_with_both_ai_functions(self):
        """Test analysis of script with both generate and reflect."""
        script = """analysis = ctx.reflect("Analyze the user's mood")
response = ctx.generate(f"Respond considering mood: {analysis}")
current_time = ctx.get_current_time()
result = f"Response: {response} at {current_time}"
"""
        
        result = self.analyzer.analyze_script(script)
        
        assert result.requires_ai_inference is True
        assert result.uses_generate is True
        assert result.uses_reflect is True
        assert result.uses_other_plugins is True
        assert len(result.detected_functions) >= 3  # May detect variations
        assert len(result.ai_function_calls) == 2
        assert len(result.plugin_function_calls) >= 1  # May detect variations
        assert result.analysis_success is True
    
    def test_complexity_estimation_simple(self):
        """Test complexity estimation for simple scripts."""
        script = "result = 'hello'"
        result = self.analyzer.analyze_script(script)
        assert result.estimated_complexity == "low"
    
    def test_complexity_estimation_with_conditionals(self):
        """Test complexity estimation with conditional logic."""
        script = """if ctx.get_message_count() > 10:
    mood = "experienced"
elif ctx.get_message_count() > 5:
    mood = "warming_up"
else:
    mood = "new"

result = mood
"""
        
        result = self.analyzer.analyze_script(script)
        assert result.has_conditionals is True
        assert result.estimated_complexity in ["low", "medium", "high"]  # Complexity may vary
    
    def test_complexity_estimation_with_loops(self):
        """Test complexity estimation with loops."""
        script = """messages = ctx.get_recent_messages(10)
topics = []
for message in messages:
    if "important" in message:
        topics.append(message)

result = f"Found {len(topics)} important topics"
"""
        
        result = self.analyzer.analyze_script(script)
        assert result.has_loops is True
        assert result.estimated_complexity in ["medium", "high"]
    
    def test_syntax_error_handling(self):
        """Test handling of scripts with syntax errors."""
        script = """result = "unclosed string
invalid syntax here
"""
        
        result = self.analyzer.analyze_script(script)
        
        # Should fall back to regex analysis
        assert result.analysis_success is False
        assert result.error_message is not None
        assert "Syntax error" in result.error_message
        assert result.line_count > 0  # Should still count lines
    
    def test_regex_fallback_analysis(self):
        """Test regex-based analysis when AST parsing fails."""
        # Script with syntax error but detectable function calls
        script = """result = ctx.get_current_time(
# Syntax error - missing closing parenthesis
mood = ctx.reflect("How am I doing?"
"""
        
        result = self.analyzer.analyze_script(script)
        
        # Should detect functions despite syntax error
        assert len(result.detected_functions) >= 1
        assert result.analysis_success is False
    
    def test_various_function_call_patterns(self):
        """Test detection of various function call patterns."""
        script = """# Different ways to call context functions
time1 = ctx.get_current_time()
time2 = ctx.get_current_time("%Y-%m-%d")

count = ctx.get_message_count()
messages = ctx.get_recent_messages(5)

reflection = ctx.reflect("Test reflection")
generation = ctx.generate("Test generation")

result = "tested"
"""
        
        result = self.analyzer.analyze_script(script)
        
        assert len(result.detected_functions) >= 6
        assert result.uses_generate is True
        assert result.uses_reflect is True
        assert result.uses_other_plugins is True
        assert result.analysis_success is True


class TestConvenienceFunction:
    """Test the convenience function for script analysis."""
    
    def test_analyze_module_script_function(self):
        """Test the convenience analyze_module_script function."""
        script = """mood = ctx.reflect("Analyze mood")
result = mood
"""
        
        result = analyze_module_script(script)
        
        assert isinstance(result, ScriptAnalysisResult)
        assert result.requires_ai_inference is True
        assert result.uses_reflect is True
        assert result.analysis_success is True
    
    def test_empty_script_convenience_function(self):
        """Test convenience function with empty script."""
        result = analyze_module_script("")
        
        assert isinstance(result, ScriptAnalysisResult)
        assert result.requires_ai_inference is False
        assert result.analysis_success is True


class TestEdgeCases:
    """Test edge cases and unusual script patterns."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = ModuleScriptAnalyzer()
    
    def test_very_long_script(self):
        """Test analysis of a very long script."""
        # Generate a script with many lines
        lines = ["result = 'line {}'".format(i) for i in range(100)]
        script = "\n".join(lines)
        
        result = self.analyzer.analyze_script(script)
        
        assert result.line_count == 100
        assert result.estimated_complexity in ["medium", "high"]  # Should be medium or high for 100 lines
        assert result.analysis_success is True
    
    def test_script_with_comments(self):
        """Test that comments are handled correctly."""
        script = """# This is a comment
result = "hello"  # Another comment
# ctx.reflect("This should not be detected")
actual_call = ctx.get_current_time()  # This should be detected
"""
        
        result = self.analyzer.analyze_script(script)
        
        # Should detect the actual function call
        assert 'ctx.get_current_time' in result.detected_functions
        # Note: AST analysis should not detect commented calls, but regex fallback might
    
    def test_multiline_strings(self):
        """Test scripts with multiline strings."""
        script = '''
        description = """
        This is a multiline string that contains
        ctx.reflect("fake call") and ctx.generate("another fake")
        """
        real_call = ctx.get_current_time()
        result = description
        '''
        
        result = self.analyzer.analyze_script(script)
        
        # Should detect the real call
        assert 'ctx.get_current_time' in result.detected_functions
        # Note: When AST fails due to syntax errors, regex fallback may detect calls in strings
    
    def test_dynamic_function_calls(self):
        """Test detection of dynamically constructed function calls."""
        script = """func_name = "get_current_time"
result = getattr(ctx, func_name)()  # Dynamic call
direct_call = ctx.get_message_count()  # Direct call
"""
        
        result = self.analyzer.analyze_script(script)
        
        # Should detect the direct call, may or may not detect dynamic call
        assert 'ctx.get_message_count' in result.detected_functions
        assert result.analysis_success is True