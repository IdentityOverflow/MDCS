"""
Debugging and inspection utilities for SystemPromptState tracking.

Provides tools for developers and AI modules to inspect, debug, and understand
the system prompt evolution through the 5-stage execution pipeline.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Union
from app.services.system_prompt_state import SystemPromptState, PromptStateManager
from app.core.script_plugins import plugin_registry

logger = logging.getLogger(__name__)


class SystemPromptInspector:
    """Utility class for inspecting and debugging SystemPromptState."""
    
    def __init__(self):
        """Initialize the inspector."""
        self.state_manager = PromptStateManager()
    
    def format_state_summary(self, state: SystemPromptState) -> str:
        """
        Format a human-readable summary of the SystemPromptState.
        
        Args:
            state: SystemPromptState to summarize
            
        Returns:
            Formatted summary string
        """
        summary_parts = [
            f"🔍 System Prompt State Summary",
            f"═══════════════════════════════",
            f"Conversation: {state.conversation_id}",
            f"Persona: {state.persona_id}",
            f"Execution Time: {state.execution_timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Total Duration: {state.total_execution_time:.3f}s",
            "",
            f"📝 Prompt Evolution:",
            f"├─ Original: {self._truncate_text(state.original_template, 60)}",
            f"├─ Stage 1: {self._truncate_text(state.stage1_resolved, 60) if state.stage1_resolved else 'Not executed'}",
            f"├─ Stage 2: {self._truncate_text(state.stage2_resolved, 60) if state.stage2_resolved else 'Not executed'}",
            f"└─ Main AI: {self._truncate_text(state.main_response_prompt, 60) if state.main_response_prompt else 'Not set'}",
            "",
            f"⚙️  Execution Info:",
            f"├─ Stages Executed: {state.execution_stages}",
            f"├─ Modules Resolved: {len(state.resolved_modules)} ({', '.join(state.resolved_modules[:3])}{'...' if len(state.resolved_modules) > 3 else ''})",
            f"├─ Warnings: {len(state.warnings)} issues",
            f"└─ Performance: {self._format_performance_summary(state)}",
        ]
        
        if state.stage4_context or state.stage5_context:
            summary_parts.extend([
                "",
                f"💾 POST_RESPONSE Context:",
                f"├─ Stage 4 Variables: {len(state.stage4_context)} items",
                f"└─ Stage 5 Variables: {len(state.stage5_context)} items"
            ])
        
        return "\n".join(summary_parts)
    
    def format_detailed_inspection(self, state: SystemPromptState) -> str:
        """
        Format a detailed inspection report of the SystemPromptState.
        
        Args:
            state: SystemPromptState to inspect
            
        Returns:
            Detailed inspection report
        """
        report_parts = [
            f"📊 Detailed SystemPromptState Inspection",
            f"════════════════════════════════════════",
            f"Timestamp: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
            "",
            f"🎯 Conversation Context:",
            f"  Conversation ID: {state.conversation_id}",
            f"  Persona ID: {state.persona_id}",
            f"  Execution Started: {state.execution_timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            f"  Total Execution Time: {state.total_execution_time:.6f} seconds",
            "",
            f"📜 Full Prompt Evolution:",
            self._format_prompt_evolution(state),
            "",
            f"🔧 Execution Metadata:",
            self._format_execution_metadata(state),
            "",
            f"📈 Performance Analysis:",
            self._format_detailed_performance(state),
        ]
        
        if state.warnings:
            report_parts.extend([
                "",
                f"⚠️  Warnings and Issues:",
                self._format_warnings(state.warnings)
            ])
        
        if state.stage4_context or state.stage5_context:
            report_parts.extend([
                "",
                f"🗂️  POST_RESPONSE Variables:",
                self._format_post_response_context(state)
            ])
        
        return "\n".join(report_parts)
    
    def compare_states(self, state1: SystemPromptState, state2: SystemPromptState) -> str:
        """
        Compare two SystemPromptState instances for differences.
        
        Args:
            state1: First state to compare
            state2: Second state to compare
            
        Returns:
            Comparison report
        """
        comparison_parts = [
            f"🔄 SystemPromptState Comparison",
            f"═══════════════════════════════",
            f"State 1: {state1.conversation_id} @ {state1.execution_timestamp.strftime('%H:%M:%S')}",
            f"State 2: {state2.conversation_id} @ {state2.execution_timestamp.strftime('%H:%M:%S')}",
            "",
        ]
        
        # Compare execution stages
        if state1.execution_stages != state2.execution_stages:
            comparison_parts.extend([
                f"📋 Execution Stages:",
                f"  State 1: {state1.execution_stages}",
                f"  State 2: {state2.execution_stages}",
                ""
            ])
        
        # Compare resolved modules
        if set(state1.resolved_modules) != set(state2.resolved_modules):
            comparison_parts.extend([
                f"🧩 Resolved Modules:",
                f"  State 1: {state1.resolved_modules}",
                f"  State 2: {state2.resolved_modules}",
                f"  Added: {list(set(state2.resolved_modules) - set(state1.resolved_modules))}",
                f"  Removed: {list(set(state1.resolved_modules) - set(state2.resolved_modules))}",
                ""
            ])
        
        # Compare performance
        perf1 = state1.get_performance_summary()
        perf2 = state2.get_performance_summary()
        if perf1["total_time"] != perf2["total_time"]:
            comparison_parts.extend([
                f"⏱️  Performance:",
                f"  State 1 Total: {perf1['total_time']:.3f}s",
                f"  State 2 Total: {perf2['total_time']:.3f}s",
                f"  Difference: {perf2['total_time'] - perf1['total_time']:.3f}s",
                ""
            ])
        
        return "\n".join(comparison_parts)
    
    def extract_debug_data(self, state: SystemPromptState) -> Dict[str, Any]:
        """
        Extract debug data from SystemPromptState for external tools.
        
        Args:
            state: SystemPromptState to extract data from
            
        Returns:
            Dictionary with debug information
        """
        return {
            "conversation_id": state.conversation_id,
            "persona_id": state.persona_id,
            "execution_timestamp": state.execution_timestamp.isoformat(),
            "total_execution_time": state.total_execution_time,
            "prompt_evolution": {
                "original": state.original_template,
                "stage1": state.stage1_resolved,
                "stage2": state.stage2_resolved,
                "main_ai": state.main_response_prompt,
            },
            "execution_metadata": {
                "stages_executed": state.execution_stages,
                "resolved_modules": state.resolved_modules,
                "stage_timings": dict(state.stage_timings),
                "warning_count": len(state.warnings),
            },
            "performance_metrics": state.get_performance_summary(),
            "post_response_context": {
                "stage4_variables": len(state.stage4_context),
                "stage5_variables": len(state.stage5_context),
                "has_accumulated_context": bool(state.variables_by_stage),
            },
            "warnings": [
                {
                    "module_name": w.module_name,
                    "warning_type": w.warning_type,
                    "message": w.message,
                    "stage": w.stage
                } for w in state.warnings
            ]
        }
    
    def _truncate_text(self, text: str, max_length: int) -> str:
        """Truncate text to specified length with ellipsis."""
        if not text:
            return "(empty)"
        if len(text) <= max_length:
            return text
        return text[:max_length-3] + "..."
    
    def _format_performance_summary(self, state: SystemPromptState) -> str:
        """Format a brief performance summary."""
        if not state.stage_timings:
            return "No timing data"
        
        perf = state.get_performance_summary()
        return f"Slowest: Stage {perf['slowest_stage']} ({state.stage_timings.get(perf['slowest_stage'], 0):.3f}s)"
    
    def _format_prompt_evolution(self, state: SystemPromptState) -> str:
        """Format detailed prompt evolution section."""
        evolution_parts = [
            f"  📄 Original Template:",
            f"    {self._indent_text(state.original_template)}",
            "",
        ]
        
        if state.stage1_resolved:
            evolution_parts.extend([
                f"  🔧 After Stage 1 (Simple + IMMEDIATE Non-AI):",
                f"    {self._indent_text(state.stage1_resolved)}",
                "",
            ])
        
        if state.stage2_resolved:
            evolution_parts.extend([
                f"  🤖 After Stage 2 (IMMEDIATE AI):",
                f"    {self._indent_text(state.stage2_resolved)}",
                "",
            ])
        
        if state.main_response_prompt:
            evolution_parts.extend([
                f"  ✨ Main AI Response Prompt:",
                f"    {self._indent_text(state.main_response_prompt)}",
                "",
            ])
        
        return "\n".join(evolution_parts).rstrip()
    
    def _format_execution_metadata(self, state: SystemPromptState) -> str:
        """Format execution metadata section."""
        metadata_parts = [
            f"  🎬 Stages Executed: {state.execution_stages}",
            f"  🧩 Modules Resolved: {state.resolved_modules}",
        ]
        
        if state.stage_timings:
            metadata_parts.append(f"  ⏱️  Stage Timings:")
            for stage, timing in sorted(state.stage_timings.items()):
                stage_name = {
                    1: "Stage 1 (Simple + IMMEDIATE Non-AI)",
                    2: "Stage 2 (IMMEDIATE AI)", 
                    4: "Stage 4 (POST_RESPONSE Non-AI)",
                    5: "Stage 5 (POST_RESPONSE AI)"
                }.get(stage, f"Stage {stage}")
                metadata_parts.append(f"    - {stage_name}: {timing:.3f}s")
        
        return "\n".join(metadata_parts)
    
    def _format_detailed_performance(self, state: SystemPromptState) -> str:
        """Format detailed performance analysis."""
        if not state.stage_timings:
            return "  No performance data available"
        
        perf = state.get_performance_summary()
        performance_parts = [
            f"  📊 Overall:",
            f"    Total Time: {perf['total_time']:.3f}s",
            f"    AI Processing: {perf['ai_stages_time']:.3f}s ({perf['ai_stages_time']/perf['total_time']*100:.1f}%)",
            f"    Non-AI Processing: {perf['non_ai_stages_time']:.3f}s ({perf['non_ai_stages_time']/perf['total_time']*100:.1f}%)",
            "",
            f"  ⚡ Stage Performance:",
            f"    Fastest: Stage {perf['fastest_stage']} ({state.stage_timings.get(perf['fastest_stage'], 0):.3f}s)",
            f"    Slowest: Stage {perf['slowest_stage']} ({state.stage_timings.get(perf['slowest_stage'], 0):.3f}s)",
        ]
        
        return "\n".join(performance_parts)
    
    def _format_warnings(self, warnings: List) -> str:
        """Format warnings section."""
        if not warnings:
            return "  No warnings"
        
        warning_parts = []
        for warning in warnings:
            warning_parts.extend([
                f"  ⚠️  {warning.warning_type.upper()}:",
                f"    Module: {warning.module_name}",
                f"    Stage: {warning.stage}",
                f"    Message: {warning.message}",
                ""
            ])
        
        return "\n".join(warning_parts).rstrip()
    
    def _format_post_response_context(self, state: SystemPromptState) -> str:
        """Format POST_RESPONSE context section."""
        context_parts = []
        
        if state.stage4_context:
            context_parts.extend([
                f"  🔧 Stage 4 (Non-AI POST_RESPONSE):",
                self._format_context_dict(state.stage4_context, indent="    "),
                ""
            ])
        
        if state.stage5_context:
            context_parts.extend([
                f"  🤖 Stage 5 (AI POST_RESPONSE):",
                self._format_context_dict(state.stage5_context, indent="    "),
                ""
            ])
        
        if state.variables_by_stage:
            context_parts.extend([
                f"  📂 Variables by Stage:",
                self._format_variables_by_stage(state.variables_by_stage),
                ""
            ])
        
        return "\n".join(context_parts).rstrip()
    
    def _format_context_dict(self, context: Dict[str, Any], indent: str = "  ") -> str:
        """Format a context dictionary."""
        if not context:
            return f"{indent}(empty)"
        
        context_lines = []
        for key, value in context.items():
            if isinstance(value, dict):
                context_lines.append(f"{indent}{key}:")
                for subkey, subvalue in value.items():
                    context_lines.append(f"{indent}  {subkey}: {subvalue}")
            else:
                context_lines.append(f"{indent}{key}: {value}")
        
        return "\n".join(context_lines)
    
    def _format_variables_by_stage(self, variables_by_stage: Dict[int, Dict[str, Any]]) -> str:
        """Format variables organized by stage."""
        stage_lines = []
        for stage, variables in sorted(variables_by_stage.items()):
            stage_name = {
                4: "Stage 4 (POST_RESPONSE Non-AI)",
                5: "Stage 5 (POST_RESPONSE AI)"
            }.get(stage, f"Stage {stage}")
            
            stage_lines.append(f"    {stage_name}:")
            if variables:
                stage_lines.append(self._format_context_dict(variables, indent="      "))
            else:
                stage_lines.append("      (no variables)")
        
        return "\n".join(stage_lines)
    
    def _indent_text(self, text: str, indent: str = "    ") -> str:
        """Indent all lines of text."""
        if not text:
            return f"{indent}(empty)"
        # Handle non-string types gracefully
        text_str = str(text) if text is not None else "(none)"
        return "\n".join(f"{indent}{line}" for line in text_str.split("\n"))


# Convenience functions for easy access

def inspect_state(state: SystemPromptState, detailed: bool = False) -> str:
    """
    Inspect a SystemPromptState and return formatted output.
    
    Args:
        state: SystemPromptState to inspect
        detailed: Whether to return detailed inspection
        
    Returns:
        Formatted inspection output
    """
    inspector = SystemPromptInspector()
    if detailed:
        return inspector.format_detailed_inspection(state)
    else:
        return inspector.format_state_summary(state)


def compare_states(state1: SystemPromptState, state2: SystemPromptState) -> str:
    """
    Compare two SystemPromptState instances.
    
    Args:
        state1: First state to compare
        state2: Second state to compare
        
    Returns:
        Comparison report
    """
    inspector = SystemPromptInspector()
    return inspector.compare_states(state1, state2)


def extract_debug_json(state: SystemPromptState) -> str:
    """
    Extract SystemPromptState debug data as JSON.
    
    Args:
        state: SystemPromptState to extract
        
    Returns:
        JSON string with debug data
    """
    inspector = SystemPromptInspector()
    debug_data = inspector.extract_debug_data(state)
    return json.dumps(debug_data, indent=2, default=str)


# Plugin function for use in advanced modules

@plugin_registry.register("debug_prompt_state")
def debug_prompt_state(detailed: bool = False, _script_context=None) -> str:
    """
    Debug plugin function for inspecting current SystemPromptState.
    
    Args:
        detailed: Whether to return detailed inspection
        _script_context: Script execution context (auto-injected)
        
    Returns:
        Formatted debug output or error message
        
    Examples:
        # Basic state summary
        summary = ctx.debug_prompt_state()
        
        # Detailed inspection
        details = ctx.debug_prompt_state(detailed=True)
    """
    try:
        if not _script_context:
            return "Error: debug_prompt_state requires script context"
        
        # Check if context has state-aware methods
        if not hasattr(_script_context, 'get_system_prompt_state'):
            return "Debug: SystemPromptState tracking not available in current context"
        
        # Get current state
        current_state = _script_context.get_system_prompt_state()
        if not current_state:
            return "Debug: No SystemPromptState currently tracked"
        
        # Return formatted inspection
        return inspect_state(current_state, detailed=detailed)
        
    except Exception as e:
        logger.error(f"Error in debug_prompt_state: {e}")
        return f"Error inspecting SystemPromptState: {repr(e)}"