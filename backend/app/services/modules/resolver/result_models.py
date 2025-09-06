"""
Result dataclasses and utilities for the staged module resolver.

Contains all result types and validation utilities used across the resolver components.
"""

import re
from typing import List, Dict, Set, Optional, Any
from dataclasses import dataclass
from enum import Enum

from ..stages.base_stage import ModuleResolutionWarning


class ExecutionStage(Enum):
    """Enumeration of template resolution stages."""
    STAGE1 = 1  # Simple + IMMEDIATE Non-AI + Previous POST_RESPONSE
    STAGE2 = 2  # IMMEDIATE AI-powered
    STAGE4 = 4  # POST_RESPONSE Non-AI
    STAGE5 = 5  # POST_RESPONSE AI-powered


@dataclass
class StagedTemplateResolutionResult:
    """Result of staged template resolution with content and warnings."""
    resolved_template: str
    warnings: List[ModuleResolutionWarning]
    resolved_modules: List[str]  # List of successfully resolved module names
    stages_executed: List[int]  # List of stages that were executed


@dataclass
class PostResponseExecutionResult:
    """Result of POST_RESPONSE module execution."""
    module_name: str
    stage: int  # 4 or 5
    variables: Dict[str, Any]
    execution_metadata: Dict[str, Any]
    success: bool
    error_message: Optional[str] = None


@dataclass
class CompleteResolutionResult:
    """Result of complete 5-stage resolution including AI response."""
    template_resolution: StagedTemplateResolutionResult
    ai_response: Optional[str]
    ai_response_metadata: Dict[str, Any]
    post_response_results: List[PostResponseExecutionResult]
    total_execution_time: float
    stage_timings: Dict[int, float]


def validate_module_name(name: str) -> bool:
    """
    Validate module name format.
    
    Args:
        name: Module name to validate
        
    Returns:
        True if valid, False otherwise
    """
    # Module names should be lowercase alphanumeric with underscores, starting with a letter
    pattern = r'^[a-z][a-z0-9_]*$'
    return bool(re.match(pattern, name)) and len(name) <= 50