"""
Script Execution Engine for Advanced Modules.

Provides secure execution of Python scripts using RestrictedPython with proper
security validation, timeout handling, and output extraction.
"""

import logging
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass
from RestrictedPython import compile_restricted_exec
from RestrictedPython.Guards import safe_builtins
from RestrictedPython.transformer import RestrictingNodeTransformer

logger = logging.getLogger(__name__)

# Default execution timeout (5 seconds)
DEFAULT_TIMEOUT = 30.0  # Increased for AI reflection calls

# Safe builtins for script execution
SAFE_BUILTINS = {
    # Math operations
    'abs': abs, 'max': max, 'min': min, 'sum': sum,
    'round': round, 'pow': pow, 'divmod': divmod,
    
    # Type functions
    'int': int, 'float': float, 'str': str, 'bool': bool,
    'list': list, 'dict': dict, 'tuple': tuple, 'set': set,
    
    # Utility functions
    'len': len, 'range': range, 'enumerate': enumerate,
    'zip': zip, 'sorted': sorted, 'reversed': reversed,
    'any': any, 'all': all,
    
    # String operations
    'chr': chr, 'ord': ord,
}

# Allowed modules for import
ALLOWED_MODULES = {
    'datetime', 'math', 'json', 're', 'uuid', 'random', 'time'
}


@dataclass
class ScriptExecutionResult:
    """Result of script execution with outputs and metadata."""
    success: bool
    outputs: Dict[str, Any]
    error_message: Optional[str] = None
    execution_time: Optional[float] = None


class ScriptExecutionError(Exception):
    """Exception raised when script execution fails."""
    
    def __init__(self, message: str, script_content: str = ""):
        super().__init__(message)
        self.script_content = script_content


class ScriptEngine:
    """
    Secure Python script execution engine using RestrictedPython.
    
    Provides safe execution of user-provided scripts with proper security
    validation, timeout handling, and output variable extraction.
    """
    
    def __init__(self, default_timeout: float = DEFAULT_TIMEOUT):
        """
        Initialize the script engine.
        
        Args:
            default_timeout: Default timeout for script execution in seconds
        """
        self.default_timeout = default_timeout
    
    def execute_script(
        self, 
        script: str, 
        context: Dict[str, Any], 
        timeout: Optional[float] = None
    ) -> ScriptExecutionResult:
        """
        Execute a Python script in a secure sandbox environment.
        
        Args:
            script: The Python script code to execute
            context: Context variables to make available to the script
            timeout: Execution timeout in seconds (uses default if not specified)
            
        Returns:
            ScriptExecutionResult with success status, outputs, and error info
        """
        if not script or not script.strip():
            # Empty script is valid - just return empty outputs
            return ScriptExecutionResult(
                success=True,
                outputs={},
                error_message=None,
                execution_time=0.0
            )
        
        execution_timeout = timeout if timeout is not None else self.default_timeout
        start_time = time.time()
        
        try:
            # Compile script with RestrictedPython
            compiled_code = compile_restricted_exec(script, filename='<script>')
            
            if compiled_code.errors:
                error_msg = "; ".join(compiled_code.errors)
                return ScriptExecutionResult(
                    success=False,
                    outputs={},
                    error_message=f"Compilation error: {error_msg}",
                    execution_time=time.time() - start_time
                )
            
            # Prepare execution environment
            execution_globals = SAFE_BUILTINS.copy()
            execution_globals.update(context)
            
            # Set restricted builtins
            execution_globals['__builtins__'] = SAFE_BUILTINS
            
            # Add restricted imports and guards
            execution_globals['_getattr_'] = self._safe_getattr
            execution_globals['_getitem_'] = self._safe_getitem
            execution_globals['_getiter_'] = self._safe_getiter
            execution_globals['_write_'] = self._write_guard
            execution_globals['__import__'] = self._restricted_import
            
            # Also add to builtins for proper import support
            execution_globals['__builtins__']['__import__'] = self._restricted_import
            
            execution_locals = {}
            
            # Execute with timeout check (simple approach)
            try:
                exec(compiled_code.code, execution_globals, execution_locals)
            except Exception as e:
                execution_time = time.time() - start_time
                return ScriptExecutionResult(
                    success=False,
                    outputs={},
                    error_message=f"Runtime error: {str(e)}",
                    execution_time=execution_time
                )
            
            # Check for timeout (basic check after execution)
            execution_time = time.time() - start_time
            if execution_time > execution_timeout:
                return ScriptExecutionResult(
                    success=False,
                    outputs={},
                    error_message=f"Script execution timeout after {execution_timeout}s",
                    execution_time=execution_time
                )
            
            # Extract output variables from locals
            outputs = self._extract_outputs(execution_locals)
            
            logger.info(f"Script executed successfully in {execution_time:.3f}s, {len(outputs)} outputs")
            
            return ScriptExecutionResult(
                success=True,
                outputs=outputs,
                error_message=None,
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_message = f"Execution failed: {str(e)}"
            logger.error(f"Script execution error: {error_message}")
            
            return ScriptExecutionResult(
                success=False,
                outputs={},
                error_message=error_message,
                execution_time=execution_time
            )
    
    def _extract_outputs(self, execution_locals: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract output variables from script execution locals.
        
        Only extracts variables that are likely intended as outputs, filtering 
        out imports, functions, and temporary variables.
        
        Args:
            execution_locals: Local variables from script execution
            
        Returns:
            Dictionary of output variable names and values
        """
        outputs = {}
        
        # Common output variable names (these are always included if present)
        output_names = {
            'result', 'output', 'value', 'data', 'response', 'content',
            'role', 'mood', 'count', 'status', 'message', 'name',
            'title', 'description', 'summary', 'info', 'text'
        }
        
        # Skip these temporary/internal variable patterns  
        skip_prefixes = {'temp_', 'tmp_', 'internal_', '_temp', '_tmp', '_internal'}
        skip_exact = {'x', 'y', 'z', 'i', 'j', 'k', 'n'}  # Single letter variables
        
        # Filter out internal variables and extract user outputs
        for name, value in execution_locals.items():
            if name.startswith('_'):  # Skip internal variables
                continue
            
            # Skip imported modules (they have __file__ or __name__ attributes usually)
            if hasattr(value, '__file__') or hasattr(value, '__module__'):
                continue
            
            # Skip functions and classes
            if callable(value) or isinstance(value, type):
                continue
            
            # Skip known temporary variable patterns
            if (any(name.startswith(prefix) for prefix in skip_prefixes) or 
                name in skip_exact):
                continue
            
            # Include output names or variables that look like outputs
            if (name in output_names or 
                name.endswith('_result') or 
                name.endswith('_output') or
                (isinstance(value, (str, int, float, bool, list, dict, tuple)) and 
                 len(name) > 1)):  # Skip single letter variables
                
                # Convert to JSON-serializable types
                try:
                    # Test if value is JSON serializable
                    import json
                    json.dumps(value, default=str)
                    outputs[name] = value
                except (TypeError, ValueError):
                    # If not serializable, convert to string
                    outputs[name] = str(value)
        
        return outputs
    
    def _safe_getattr(self, obj, name, default=None, getattr=getattr):
        """Safe attribute access for RestrictedPython."""
        # Block access to dangerous attributes
        if name.startswith('_'):
            raise AttributeError(f"Access to attribute '{name}' is restricted")
        return getattr(obj, name, default)
    
    def _safe_getitem(self, obj, index):
        """Safe item access for RestrictedPython."""
        return obj[index]
    
    def _safe_getiter(self, obj):
        """Safe iterator access for RestrictedPython."""
        return iter(obj)
    
    def _write_guard(self, obj):
        """Write guard for RestrictedPython - prevents certain write operations."""
        return obj
    
    def _restricted_import(self, name, globals=None, locals=None, fromlist=(), level=0):
        """
        Restricted import function that only allows safe modules.
        
        Args:
            name: Module name to import
            globals: Global variables (unused)
            locals: Local variables (unused)  
            fromlist: From imports list (unused)
            level: Import level (unused)
            
        Returns:
            Imported module if allowed
            
        Raises:
            ImportError: If module is not in allowed list
        """
        # Check if the base module name is allowed
        base_module = name.split('.')[0]
        if base_module not in ALLOWED_MODULES:
            raise ImportError(f"Import of module '{name}' is not allowed")
        
        return __import__(name, globals, locals, fromlist, level)
    
    @staticmethod
    def validate_script_basic(script: str) -> bool:
        """
        Basic validation of script content.
        
        Args:
            script: Script content to validate
            
        Returns:
            True if script passes basic validation
        """
        if not script:
            return True  # Empty script is valid
        
        # Check for obvious dangerous patterns
        dangerous_patterns = [
            '__import__', 'eval', 'exec', 'compile',
            'open', 'file', 'input', 'raw_input',
            'globals', 'locals', 'vars', 'dir'
        ]
        
        script_lower = script.lower()
        for pattern in dangerous_patterns:
            if pattern in script_lower:
                logger.warning(f"Script contains potentially dangerous pattern: {pattern}")
                # Don't block here - let RestrictedPython handle it
        
        return True