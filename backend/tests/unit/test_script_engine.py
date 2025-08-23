"""
Unit tests for the Script Execution Engine.

Tests the core logic for executing Python scripts in a secure RestrictedPython
sandbox with proper security validation and output extraction.
"""

import pytest
from unittest.mock import Mock, patch
from app.core.script_engine import ScriptEngine, ScriptExecutionResult, ScriptExecutionError


class TestScriptEngine:
    """Test cases for the ScriptEngine service."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.engine = ScriptEngine()

    def test_execute_simple_script_success(self):
        """Test successful execution of a simple script with result variable."""
        script = """
result = "Hello, World!"
"""
        context = {}
        
        result = self.engine.execute_script(script, context)
        
        assert result.success is True
        assert result.outputs == {"result": "Hello, World!"}
        assert result.error_message is None

    def test_execute_multiple_outputs(self):
        """Test script execution with multiple named outputs."""
        script = """
result = "AVA"
role = "AI Assistant"
mood = "helpful"
count = 42
"""
        context = {}
        
        result = self.engine.execute_script(script, context)
        
        assert result.success is True
        assert result.outputs["result"] == "AVA"
        assert result.outputs["role"] == "AI Assistant"
        assert result.outputs["mood"] == "helpful"
        assert result.outputs["count"] == 42

    def test_execute_script_with_context_access(self):
        """Test script execution with access to provided context."""
        script = """
# Access context data
name = ctx.conversation_id
count = ctx.message_count

result = f"Conversation {name} has {count} messages"
"""
        mock_context = Mock()
        mock_context.conversation_id = "test-123"
        mock_context.message_count = 5
        
        result = self.engine.execute_script(script, {"ctx": mock_context})
        
        assert result.success is True
        assert result.outputs["result"] == "Conversation test-123 has 5 messages"

    def test_execute_script_with_imports_allowed(self):
        """Test that allowed imports work correctly."""
        script = """
from datetime import datetime
import math

now = datetime.now().strftime("%Y-%m-%d")
pi_rounded = math.floor(math.pi)

result = f"Today is {now}, pi is approximately {pi_rounded}"
"""
        context = {}
        
        result = self.engine.execute_script(script, context)
        
        assert result.success is True
        assert "Today is" in result.outputs["result"]
        assert "pi is approximately 3" in result.outputs["result"]

    def test_execute_script_security_violation_import(self):
        """Test that dangerous imports are blocked."""
        script = """
import os
result = os.listdir('/')
"""
        context = {}
        
        result = self.engine.execute_script(script, context)
        
        assert result.success is False
        assert "import" in result.error_message.lower() or "restricted" in result.error_message.lower()
        assert result.outputs == {}

    def test_execute_script_security_violation_builtin(self):
        """Test that dangerous builtin functions are blocked."""
        script = """
result = eval("1 + 1")
"""
        context = {}
        
        result = self.engine.execute_script(script, context)
        
        assert result.success is False
        assert result.outputs == {}

    def test_execute_script_syntax_error(self):
        """Test handling of syntax errors in scripts."""
        script = """
result = "unclosed string
"""
        context = {}
        
        result = self.engine.execute_script(script, context)
        
        assert result.success is False
        assert "syntax" in result.error_message.lower() or "unterminated" in result.error_message.lower()
        assert result.outputs == {}

    def test_execute_script_runtime_error(self):
        """Test handling of runtime errors in scripts."""
        script = """
result = 1 / 0
"""
        context = {}
        
        result = self.engine.execute_script(script, context)
        
        assert result.success is False
        assert "division" in result.error_message.lower() or "zerodivision" in result.error_message.lower()
        assert result.outputs == {}

    def test_execute_script_timeout(self):
        """Test that script execution respects timeout limits."""
        script = """
import time
time.sleep(10)  # This should timeout
result = "Should not reach here"
"""
        context = {}
        
        # This should timeout quickly (engine should have default timeout)
        result = self.engine.execute_script(script, context, timeout=1)
        
        assert result.success is False
        assert "timeout" in result.error_message.lower()
        assert result.outputs == {}

    def test_execute_script_no_outputs(self):
        """Test script execution that doesn't set any output variables."""
        script = """
# This script doesn't set any output-named variables  
temp_var = 1 + 1
internal_calc = temp_var * 2
"""
        context = {}
        
        result = self.engine.execute_script(script, context)
        
        assert result.success is True
        # Should not capture temporary variables (only result, output, etc.)
        assert result.outputs == {}
        assert result.error_message is None

    def test_execute_script_complex_computation(self):
        """Test script with more complex computation logic."""
        script = """
# Complex logic for testing
numbers = [1, 2, 3, 4, 5]
total = sum(numbers)
average = total / len(numbers)

if average > 3:
    status = "above average"
elif average < 3:
    status = "below average"
else:
    status = "exactly average"

result = f"Sum: {total}, Average: {average}, Status: {status}"
count = len(numbers)
"""
        context = {}
        
        result = self.engine.execute_script(script, context)
        
        assert result.success is True
        assert result.outputs["result"] == "Sum: 15, Average: 3.0, Status: exactly average"
        assert result.outputs["count"] == 5

    def test_execute_empty_script(self):
        """Test execution of empty script."""
        script = ""
        context = {}
        
        result = self.engine.execute_script(script, context)
        
        assert result.success is True
        assert result.outputs == {}
        assert result.error_message is None

    def test_execute_whitespace_only_script(self):
        """Test execution of script with only whitespace."""
        script = "   \n  \t  \n  "
        context = {}
        
        result = self.engine.execute_script(script, context)
        
        assert result.success is True
        assert result.outputs == {}
        assert result.error_message is None


class TestScriptExecutionResult:
    """Test cases for the ScriptExecutionResult data class."""

    def test_success_result_creation(self):
        """Test creation of successful execution result."""
        outputs = {"result": "test", "count": 5}
        result = ScriptExecutionResult(
            success=True,
            outputs=outputs,
            error_message=None,
            execution_time=0.1
        )
        
        assert result.success is True
        assert result.outputs == outputs
        assert result.error_message is None
        assert result.execution_time == 0.1

    def test_failure_result_creation(self):
        """Test creation of failed execution result."""
        result = ScriptExecutionResult(
            success=False,
            outputs={},
            error_message="Test error",
            execution_time=0.05
        )
        
        assert result.success is False
        assert result.outputs == {}
        assert result.error_message == "Test error"
        assert result.execution_time == 0.05


class TestScriptExecutionError:
    """Test cases for the ScriptExecutionError exception."""

    def test_script_execution_error_creation(self):
        """Test creation of script execution error."""
        error = ScriptExecutionError("Test execution error", "test_script")
        
        assert str(error) == "Test execution error"
        assert error.script_content == "test_script"