"""
System Prompt State Tracking for Project 2501 Cognitive Framework.

Provides complete visibility into how the system prompt evolves through
the 5-stage execution pipeline, enabling debugging, optimization, and
enhanced cognitive capabilities.
"""

import time
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional

# Avoid circular import - define ModuleResolutionWarning locally if needed
from typing import NamedTuple

class ModuleResolutionWarning(NamedTuple):
    """Warning information for module resolution issues."""
    module_name: str
    warning_type: str
    message: str
    stage: int = None


@dataclass
class SystemPromptState:
    """
    Tracks system prompt evolution through staged execution pipeline.
    
    This class provides complete transparency into how the system prompt
    is transformed from the original persona template through each stage
    of the execution pipeline.
    """
    
    # Core identifiers
    conversation_id: str
    persona_id: str
    execution_timestamp: datetime
    original_template: str
    
    # Stage-by-stage evolution
    stage1_resolved: str = ""                    # After simple + immediate non-AI + previous POST_RESPONSE
    stage2_resolved: str = ""                    # After immediate AI modules
    main_response_prompt: str = ""               # Exact prompt sent to main AI (Stage 3)
    stage4_context: Dict[str, Any] = field(default_factory=dict)  # POST_RESPONSE non-AI variables
    stage5_context: Dict[str, Any] = field(default_factory=dict)  # POST_RESPONSE AI analysis results
    
    # Execution metadata
    resolved_modules: List[str] = field(default_factory=list)        # All modules resolved
    warnings: List[ModuleResolutionWarning] = field(default_factory=list)
    execution_stages: List[int] = field(default_factory=list)        # Which stages executed
    variables_by_stage: Dict[int, Dict[str, Any]] = field(default_factory=dict)  # Stage outputs
    
    # Performance tracking
    stage_timings: Dict[int, float] = field(default_factory=dict)    # Execution time per stage
    total_execution_time: float = 0.0
    
    def get_prompt_for_stage(self, stage: int) -> str:
        """
        Get the appropriate system prompt for a specific execution stage.
        
        This method returns the prompt that should be used by modules
        executing in the given stage, following the architectural principle
        of using already-resolved content without re-execution.
        
        Args:
            stage: Execution stage number (1, 2, 4, 5)
            
        Returns:
            Appropriate system prompt for the stage
        """
        if stage == 2:
            # Stage 2 (IMMEDIATE AI): Use Stage 1 resolved prompt
            return self.stage1_resolved
        elif stage == 5:
            # Stage 5 (POST_RESPONSE AI): Use main response prompt + Stage 4 context
            base_prompt = self.main_response_prompt
            if self.variables_by_stage.get(4):
                context_addition = self._format_stage_variables(4)
                return f"{base_prompt}\n\nCurrent context:\n{context_addition}"
            return base_prompt
        else:
            # Fallback to original template for unsupported stages
            return self.original_template
    
    def _format_stage_variables(self, stage: int) -> str:
        """
        Format stage variables for context inclusion.
        
        Args:
            stage: Stage number (4 or 5)
            
        Returns:
            Formatted variables string for context
        """
        stage_vars = self.variables_by_stage.get(stage, {})
        if not stage_vars:
            return ""
        
        formatted_lines = []
        for module_name, variables in stage_vars.items():
            formatted_lines.append(f"{module_name}:")
            if isinstance(variables, dict):
                for var_name, var_value in variables.items():
                    formatted_lines.append(f"  {var_name}: {var_value}")
            else:
                formatted_lines.append(f"  {variables}")
        
        return "\n".join(formatted_lines)
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """
        Get performance analysis summary.
        
        Returns:
            Dictionary with performance metrics
        """
        if not self.stage_timings:
            return {
                "total_time": self.total_execution_time,
                "slowest_stage": None,
                "fastest_stage": None,
                "ai_stages_time": 0.0,
                "non_ai_stages_time": 0.0
            }
        
        # Find slowest and fastest stages
        slowest_stage = max(self.stage_timings.keys(), key=lambda s: self.stage_timings[s])
        fastest_stage = min(self.stage_timings.keys(), key=lambda s: self.stage_timings[s])
        
        # Calculate AI vs non-AI time
        ai_stages = [2, 5]  # Stages that involve AI processing
        ai_time = sum(self.stage_timings.get(stage, 0.0) for stage in ai_stages)
        non_ai_time = self.total_execution_time - ai_time
        
        return {
            "total_time": self.total_execution_time,
            "slowest_stage": slowest_stage,
            "fastest_stage": fastest_stage,
            "ai_stages_time": ai_time,
            "non_ai_stages_time": non_ai_time
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for API responses and serialization.
        
        Returns:
            Dictionary representation of the prompt state
        """
        return {
            "conversation_id": self.conversation_id,
            "persona_id": self.persona_id,
            "execution_timestamp": self.execution_timestamp.isoformat(),
            "original_template": self.original_template,
            "stage1_resolved": self.stage1_resolved,
            "stage2_resolved": self.stage2_resolved,
            "main_response_prompt": self.main_response_prompt,
            "stage4_context": self.stage4_context,
            "stage5_context": self.stage5_context,
            "resolved_modules": self.resolved_modules,
            "warnings": [
                {
                    "module_name": w.module_name,
                    "warning_type": w.warning_type,
                    "message": w.message,
                    "stage": getattr(w, 'stage', None)
                } for w in self.warnings
            ],
            "execution_stages": self.execution_stages,
            "variables_by_stage": self.variables_by_stage,
            "stage_timings": self.stage_timings,
            "total_execution_time": self.total_execution_time
        }


class PromptStateManager:
    """
    Utility class for managing SystemPromptState lifecycle.
    
    Provides methods for creating, updating, and finalizing prompt states
    throughout the staged execution process.
    """
    
    def create_initial_state(
        self, 
        conversation_id: str, 
        persona_id: str, 
        original_template: str
    ) -> SystemPromptState:
        """
        Create initial prompt state for execution tracking.
        
        Args:
            conversation_id: UUID of the conversation
            persona_id: UUID of the persona
            original_template: Original persona template with @module_name references
            
        Returns:
            Initialized SystemPromptState
        """
        return SystemPromptState(
            conversation_id=conversation_id,
            persona_id=persona_id,
            execution_timestamp=datetime.utcnow(),
            original_template=original_template
        )
    
    def update_stage1_completion(
        self,
        state: SystemPromptState,
        resolved_template: str,
        resolved_modules: List[str],
        warnings: List[ModuleResolutionWarning],
        execution_time: float
    ) -> SystemPromptState:
        """
        Update state after Stage 1 completion.
        
        Args:
            state: Current prompt state
            resolved_template: Template after Stage 1 resolution
            resolved_modules: Modules resolved in Stage 1
            warnings: Any warnings generated
            execution_time: Stage 1 execution time in seconds
            
        Returns:
            Updated SystemPromptState
        """
        state.stage1_resolved = resolved_template
        state.resolved_modules.extend(resolved_modules)
        state.warnings.extend(warnings)
        state.execution_stages.append(1)
        state.stage_timings[1] = execution_time
        
        return state
    
    def update_stage2_completion(
        self,
        state: SystemPromptState,
        resolved_template: str,
        additional_modules: List[str],
        warnings: List[ModuleResolutionWarning],
        execution_time: float
    ) -> SystemPromptState:
        """
        Update state after Stage 2 completion.
        
        Args:
            state: Current prompt state
            resolved_template: Template after Stage 2 resolution
            additional_modules: Additional modules resolved in Stage 2
            warnings: Any warnings generated
            execution_time: Stage 2 execution time in seconds
            
        Returns:
            Updated SystemPromptState
        """
        state.stage2_resolved = resolved_template
        state.main_response_prompt = resolved_template  # This goes to main AI
        state.resolved_modules.extend(additional_modules)
        state.warnings.extend(warnings)
        state.execution_stages.append(2)
        state.stage_timings[2] = execution_time
        
        return state
    
    def update_stage4_completion(
        self,
        state: SystemPromptState,
        variables: Dict[str, Any],
        execution_time: float
    ) -> SystemPromptState:
        """
        Update state after Stage 4 (POST_RESPONSE non-AI) completion.
        
        Args:
            state: Current prompt state
            variables: Variables generated by Stage 4 modules
            execution_time: Stage 4 execution time in seconds
            
        Returns:
            Updated SystemPromptState
        """
        state.stage4_context = variables
        state.variables_by_stage[4] = variables
        state.execution_stages.append(4)
        state.stage_timings[4] = execution_time
        
        return state
    
    def update_stage5_completion(
        self,
        state: SystemPromptState,
        variables: Dict[str, Any],
        execution_time: float
    ) -> SystemPromptState:
        """
        Update state after Stage 5 (POST_RESPONSE AI) completion.
        
        Args:
            state: Current prompt state
            variables: Variables generated by Stage 5 modules
            execution_time: Stage 5 execution time in seconds
            
        Returns:
            Updated SystemPromptState
        """
        state.stage5_context = variables
        state.variables_by_stage[5] = variables
        state.execution_stages.append(5)
        state.stage_timings[5] = execution_time
        
        return state
    
    def finalize_state(self, state: SystemPromptState) -> SystemPromptState:
        """
        Finalize prompt state with total execution time.
        
        Args:
            state: Current prompt state
            
        Returns:
            Finalized SystemPromptState with total execution time
        """
        state.total_execution_time = sum(state.stage_timings.values())
        return state
    
    def get_debug_summary(self, state: SystemPromptState) -> Dict[str, Any]:
        """
        Get comprehensive debug summary of prompt state.
        
        Args:
            state: SystemPromptState to analyze
            
        Returns:
            Dictionary with debug information
        """
        return {
            "conversation_id": state.conversation_id,
            "persona_id": state.persona_id,
            "execution_timestamp": state.execution_timestamp.isoformat(),
            
            "prompt_evolution": {
                "original": state.original_template,
                "stage1": state.stage1_resolved,
                "stage2": state.stage2_resolved,
                "main_ai": state.main_response_prompt,
            },
            
            "execution_metadata": {
                "resolved_modules": state.resolved_modules,
                "stages_executed": state.execution_stages,
                "warnings_count": len(state.warnings),
                "warnings": [
                    {"module": w.module_name, "type": w.warning_type, "message": w.message}
                    for w in state.warnings
                ]
            },
            
            "performance_metrics": {
                "total_time": state.total_execution_time,
                "stage_timings": state.stage_timings,
                **state.get_performance_summary()
            },
            
            "context_variables": {
                "stage4_context": state.stage4_context,
                "stage5_context": state.stage5_context,
                "variables_by_stage": state.variables_by_stage
            }
        }