"""
Modular module resolution system.

This package replaces the monolithic staged_module_resolver_base.py (1,073 lines)
with a clean, focused, domain-driven architecture.
"""

# Core resolver orchestration
from .resolver import StagedModuleResolver

# Template parsing and processing
from .template_parser import TemplateParser

# Stage implementations
from .stages import Stage1Executor, Stage2Executor, Stage3Executor, Stage4Executor, Stage5Executor

# Execution engines
from .execution import SimpleExecutor, ScriptExecutor, AIExecutor

__all__ = [
    'StagedModuleResolver',
    'TemplateParser', 
    'Stage1Executor',
    'Stage2Executor',
    'Stage3Executor',
    'Stage4Executor',
    'Stage5Executor',
    'SimpleExecutor',
    'ScriptExecutor',
    'AIExecutor'
]