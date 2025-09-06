"""
Execution utilities for timing and error handling in the pipeline executor.

Provides shared utilities for stage timing, error handling, and execution monitoring.
"""

import logging
import time
from contextlib import contextmanager
from typing import List, Optional
from dataclasses import dataclass

from ..stages.base_stage import ModuleResolutionWarning

logger = logging.getLogger(__name__)


@dataclass 
class StageTimer:
    """Context manager for timing stage execution."""
    stage: int
    start_time: Optional[float] = None
    elapsed: Optional[float] = None
    
    def __enter__(self):
        """Start timing."""
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop timing and calculate elapsed time."""
        if self.start_time:
            self.elapsed = time.time() - self.start_time


class ExecutionTimer:
    """Utility class for timing stage execution."""
    
    @contextmanager
    def time_stage(self, stage: int):
        """
        Context manager for timing a stage execution.
        
        Args:
            stage: Stage number to time
            
        Yields:
            StageTimer: Timer object with elapsed time after completion
        """
        timer = StageTimer(stage)
        try:
            timer.__enter__()
            yield timer
        finally:
            timer.__exit__(None, None, None)


class StageErrorHandler:
    """Utility class for handling stage execution errors."""
    
    def handle_stage_error(
        self, 
        stage: int, 
        error: Exception, 
        warnings: List[ModuleResolutionWarning]
    ) -> None:
        """
        Handle a stage execution error by logging and adding to warnings.
        
        Args:
            stage: Stage number where error occurred
            error: Exception that occurred
            warnings: List to add warning to
        """
        error_message = f"Stage {stage} execution failed: {str(error)}"
        logger.error(error_message)
        
        warnings.append(ModuleResolutionWarning(
            module_name=f"stage{stage}_execution",
            warning_type="stage_execution_error",
            message=error_message,
            stage=stage
        ))
    
    def handle_cancellation_error(
        self,
        stage: int,
        warnings: List[ModuleResolutionWarning]
    ) -> None:
        """
        Handle a cancellation error during stage execution.
        
        Args:
            stage: Stage number where cancellation occurred
            warnings: List to add warning to
        """
        warning_message = f"Stage {stage} execution was cancelled"
        logger.info(warning_message)
        
        warnings.append(ModuleResolutionWarning(
            module_name=f"stage{stage}_execution",
            warning_type="stage_cancellation",
            message=warning_message,
            stage=stage
        ))