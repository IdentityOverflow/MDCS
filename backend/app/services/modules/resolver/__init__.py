"""
Resolver package for staged module resolution components.

This package breaks down the monolithic resolver.py into focused components:
- result_models.py: Result dataclasses and utilities  
- session_manager.py: Session tracking and cancellation logic
- state_tracker.py: SystemPromptState tracking
- streaming_handler.py: Streaming pipeline logic
- pipeline_executor.py: Core execution logic
- orchestrator.py: Main facade
"""

from .result_models import (
    ExecutionStage,
    StagedTemplateResolutionResult, 
    PostResponseExecutionResult,
    CompleteResolutionResult,
    validate_module_name
)
from .session_manager import ResolverSessionManager
from .state_tracker import ResolverStateTracker
from .pipeline_executor import PipelineExecutor
from .streaming_handler import StreamingPipelineHandler
from .orchestrator import StagedModuleResolver
from ..stages.base_stage import ModuleResolutionWarning

from .convenience import resolve_template_for_response, _parse_module_references

__all__ = [
    "ExecutionStage",
    "StagedTemplateResolutionResult",
    "PostResponseExecutionResult", 
    "CompleteResolutionResult",
    "validate_module_name",
    "ResolverSessionManager",
    "ResolverStateTracker", 
    "PipelineExecutor",
    "StreamingPipelineHandler",
    "StagedModuleResolver",
    "ModuleResolutionWarning",
    "resolve_template_for_response",
    "_parse_module_references"
]