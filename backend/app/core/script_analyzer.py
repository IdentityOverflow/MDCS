"""
Script Analysis Utility for Module Classification.

Analyzes Python scripts to detect AI plugin usage, complexity, and other
characteristics needed for staged execution pipeline.
"""

import ast
import re
import logging
from typing import Dict, Any, Set, List, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ScriptAnalysisResult:
    """Result of script analysis with detected capabilities and metadata."""
    requires_ai_inference: bool
    uses_generate: bool
    uses_reflect: bool
    uses_other_plugins: bool
    
    # Function usage details
    detected_functions: List[str]
    ai_function_calls: List[str]
    plugin_function_calls: List[str]
    
    # Complexity metrics
    estimated_complexity: str  # "low", "medium", "high"
    line_count: int
    function_count: int
    has_loops: bool
    has_conditionals: bool
    
    # Error information
    analysis_success: bool
    error_message: Optional[str] = None
    
    # Metadata
    analyzed_at: str = None
    
    def __post_init__(self):
        """Set analysis timestamp."""
        if not self.analyzed_at:
            self.analyzed_at = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage in database."""
        return {
            "requires_ai_inference": self.requires_ai_inference,
            "uses_generate": self.uses_generate,
            "uses_reflect": self.uses_reflect,
            "uses_other_plugins": self.uses_other_plugins,
            "detected_functions": self.detected_functions,
            "ai_function_calls": self.ai_function_calls,
            "plugin_function_calls": self.plugin_function_calls,
            "estimated_complexity": self.estimated_complexity,
            "line_count": self.line_count,
            "function_count": self.function_count,
            "has_loops": self.has_loops,
            "has_conditionals": self.has_conditionals,
            "analysis_success": self.analysis_success,
            "error_message": self.error_message,
            "analyzed_at": self.analyzed_at
        }


class ModuleScriptAnalyzer:
    """
    Analyzer for module Python scripts to detect AI dependencies and characteristics.
    
    This analyzer helps classify modules for the staged execution pipeline by
    detecting which ones need AI inference and what plugins they use.
    """
    
    # Known AI inference functions
    AI_FUNCTIONS = {
        'generate', 'reflect'
    }
    
    # Known plugin function patterns
    PLUGIN_FUNCTION_PATTERNS = [
        r'ctx\.(get_\w+)',
        r'ctx\.(set_\w+)',
        r'ctx\.(calculate_\w+)',
        r'ctx\.(analyze_\w+)',
        r'ctx\.(format_\w+)',
        r'ctx\.(process_\w+)'
    ]
    
    def analyze_script(self, script: str) -> ScriptAnalysisResult:
        """
        Analyze a module script to detect AI dependencies and characteristics.
        
        Args:
            script: Python script content to analyze
            
        Returns:
            ScriptAnalysisResult with detected capabilities and metadata
        """
        if not script or not script.strip():
            return ScriptAnalysisResult(
                requires_ai_inference=False,
                uses_generate=False,
                uses_reflect=False,
                uses_other_plugins=False,
                detected_functions=[],
                ai_function_calls=[],
                plugin_function_calls=[],
                estimated_complexity="low",
                line_count=0,
                function_count=0,
                has_loops=False,
                has_conditionals=False,
                analysis_success=True
            )
        
        try:
            # Parse the script with AST for accurate analysis
            tree = ast.parse(script)
            
            # Extract various metrics using AST visitor
            visitor = ScriptVisitor()
            visitor.visit(tree)
            
            # Also do regex-based analysis for function calls
            regex_results = self._analyze_with_regex(script)
            
            # Combine results
            detected_functions = list(set(visitor.function_calls + regex_results['function_calls']))
            ai_function_calls = [f for f in detected_functions if any(ai_func in f for ai_func in self.AI_FUNCTIONS)]
            
            # Determine AI inference requirement
            uses_generate = any('generate' in call for call in ai_function_calls)
            uses_reflect = any('reflect' in call for call in ai_function_calls)
            requires_ai_inference = uses_generate or uses_reflect
            
            # Determine complexity
            complexity = self._estimate_complexity(
                len(script.split('\n')),
                len(detected_functions),
                visitor.has_loops,
                visitor.has_conditionals
            )
            
            return ScriptAnalysisResult(
                requires_ai_inference=requires_ai_inference,
                uses_generate=uses_generate,
                uses_reflect=uses_reflect,
                uses_other_plugins=len(detected_functions) > len(ai_function_calls),
                detected_functions=detected_functions,
                ai_function_calls=ai_function_calls,
                plugin_function_calls=[f for f in detected_functions if f not in ai_function_calls],
                estimated_complexity=complexity,
                line_count=len([line for line in script.split('\n') if line.strip()]),
                function_count=len(detected_functions),
                has_loops=visitor.has_loops,
                has_conditionals=visitor.has_conditionals,
                analysis_success=True
            )
            
        except SyntaxError as e:
            logger.warning(f"Syntax error in script analysis: {e}")
            # Fall back to regex analysis for scripts with syntax issues
            regex_results = self._analyze_with_regex(script)
            
            ai_calls = [f for f in regex_results['function_calls'] if any(ai_func in f for ai_func in self.AI_FUNCTIONS)]
            uses_generate = any('generate' in call for call in ai_calls)
            uses_reflect = any('reflect' in call for call in ai_calls)
            
            return ScriptAnalysisResult(
                requires_ai_inference=uses_generate or uses_reflect,
                uses_generate=uses_generate,
                uses_reflect=uses_reflect,
                uses_other_plugins=len(regex_results['function_calls']) > len(ai_calls),
                detected_functions=regex_results['function_calls'],
                ai_function_calls=ai_calls,
                plugin_function_calls=[f for f in regex_results['function_calls'] if f not in ai_calls],
                estimated_complexity="unknown",
                line_count=len([line for line in script.split('\n') if line.strip()]),
                function_count=len(regex_results['function_calls']),
                has_loops=False,
                has_conditionals=False,
                analysis_success=False,
                error_message=f"Syntax error: {str(e)}"
            )
            
        except Exception as e:
            logger.error(f"Unexpected error in script analysis: {e}")
            return ScriptAnalysisResult(
                requires_ai_inference=False,
                uses_generate=False,
                uses_reflect=False,
                uses_other_plugins=False,
                detected_functions=[],
                ai_function_calls=[],
                plugin_function_calls=[],
                estimated_complexity="unknown",
                line_count=len([line for line in script.split('\n') if line.strip()]),
                function_count=0,
                has_loops=False,
                has_conditionals=False,
                analysis_success=False,
                error_message=f"Analysis error: {str(e)}"
            )
    
    def _analyze_with_regex(self, script: str) -> Dict[str, Any]:
        """
        Fallback regex-based analysis for when AST parsing fails.
        
        Args:
            script: Python script content
            
        Returns:
            Dictionary with detected function calls
        """
        function_calls = []
        
        # Look for ctx.function_name() patterns
        ctx_pattern = r'ctx\.(\w+)\s*\('
        matches = re.findall(ctx_pattern, script)
        function_calls.extend([f'ctx.{match}' for match in matches])
        
        # Look for specific plugin function patterns
        for pattern in self.PLUGIN_FUNCTION_PATTERNS:
            matches = re.findall(pattern, script)
            function_calls.extend(matches)
        
        return {
            'function_calls': list(set(function_calls))
        }
    
    def _estimate_complexity(self, line_count: int, function_count: int, has_loops: bool, has_conditionals: bool) -> str:
        """
        Estimate script complexity based on various metrics.
        
        Args:
            line_count: Number of non-empty lines
            function_count: Number of function calls
            has_loops: Whether script contains loops
            has_conditionals: Whether script contains conditionals
            
        Returns:
            Complexity estimate: "low", "medium", or "high"
        """
        complexity_score = 0
        
        # Line count contribution
        if line_count > 50:
            complexity_score += 3
        elif line_count > 20:
            complexity_score += 2
        elif line_count > 5:
            complexity_score += 1
        
        # Function count contribution
        if function_count > 10:
            complexity_score += 3
        elif function_count > 5:
            complexity_score += 2
        elif function_count > 2:
            complexity_score += 1
        
        # Control flow contribution
        if has_loops:
            complexity_score += 2
        if has_conditionals:
            complexity_score += 1
        
        # Classify based on total score
        if complexity_score >= 6:
            return "high"
        elif complexity_score >= 3:
            return "medium"
        else:
            return "low"


class ScriptVisitor(ast.NodeVisitor):
    """AST visitor to extract information about Python scripts."""
    
    def __init__(self):
        self.function_calls = []
        self.has_loops = False
        self.has_conditionals = False
    
    def visit_Call(self, node):
        """Visit function call nodes to extract function names."""
        try:
            # Handle ctx.function_name() patterns
            if isinstance(node.func, ast.Attribute):
                if isinstance(node.func.value, ast.Name) and node.func.value.id == 'ctx':
                    self.function_calls.append(f'ctx.{node.func.attr}')
            
            # Handle direct function calls
            elif isinstance(node.func, ast.Name):
                self.function_calls.append(node.func.id)
                
        except AttributeError:
            # Some complex call patterns might not have these attributes
            pass
        
        self.generic_visit(node)
    
    def visit_For(self, node):
        """Visit for loops."""
        self.has_loops = True
        self.generic_visit(node)
    
    def visit_While(self, node):
        """Visit while loops."""
        self.has_loops = True
        self.generic_visit(node)
    
    def visit_If(self, node):
        """Visit if statements."""
        self.has_conditionals = True
        self.generic_visit(node)


# Convenience instance for module usage
script_analyzer = ModuleScriptAnalyzer()


def analyze_module_script(script: str) -> ScriptAnalysisResult:
    """
    Convenience function to analyze a module script.
    
    Args:
        script: Python script content to analyze
        
    Returns:
        ScriptAnalysisResult with detected capabilities
    """
    return script_analyzer.analyze_script(script)