"""
Base stage executor with shared functionality for all stages.
"""

import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Set, Optional, Any
from dataclasses import dataclass
from sqlalchemy.orm import Session

from ....models import Module
from ..template_parser import TemplateParser

logger = logging.getLogger(__name__)


@dataclass
class ModuleResolutionWarning:
    """Warning information for module resolution issues."""
    module_name: str
    warning_type: str  # 'module_not_found', 'circular_dependency', 'max_depth_exceeded'
    message: str
    stage: Optional[int] = None


class BaseStageExecutor(ABC):
    """
    Base class for stage executors with shared functionality.
    
    Provides common module resolution logic while allowing each stage
    to implement its own execution criteria and module filtering.
    """
    
    def __init__(self, db_session: Optional[Session] = None):
        """
        Initialize the stage executor.
        
        Args:
            db_session: Optional database session
        """
        self.db_session = db_session
        self._resolution_stack: Set[str] = set()  # Track circular dependencies
    
    @property
    @abstractmethod
    def STAGE_NUMBER(self) -> int:
        """Stage number for this executor."""
        pass
    
    @property  
    @abstractmethod
    def STAGE_NAME(self) -> str:
        """Human-readable stage name."""
        pass
    
    @abstractmethod
    def execute_stage(
        self,
        template: str,
        warnings: List[ModuleResolutionWarning],
        resolved_modules: List[str],
        **kwargs
    ) -> str:
        """
        Execute the stage-specific module resolution logic.
        
        Args:
            template: Template string with module references
            warnings: List to collect resolution warnings
            resolved_modules: List to track successfully resolved modules
            **kwargs: Additional context parameters
            
        Returns:
            Template with stage modules resolved
        """
        pass
    
    def _resolve_modules_in_template(
        self,
        template: str,
        modules: List[Module],
        warnings: List[ModuleResolutionWarning],
        resolved_modules: List[str],
        conversation_id: Optional[str] = None,
        persona_id: Optional[str] = None,
        db_session: Optional[Session] = None,
        trigger_context: Optional[Dict[str, Any]] = None,
        current_provider: Optional[str] = None,
        current_provider_settings: Optional[Dict[str, Any]] = None,
        current_chat_controls: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> str:
        """
        Resolve specific modules in a template.
        
        Args:
            template: Template string to process
            modules: List of modules to resolve
            warnings: List to collect warnings
            resolved_modules: List to track resolved modules
            conversation_id: Optional conversation context
            persona_id: Optional persona context  
            db_session: Optional database session
            trigger_context: Optional trigger context
            current_provider: Current provider for context
            current_provider_settings: Provider settings for context
            current_chat_controls: Chat controls for context
            
        Returns:
            Template with specified modules resolved
        """
        if not modules:
            return template
        
        # Create lookup by module name
        modules_by_name = {module.name: module for module in modules}
        
        # Find module references in template
        module_names = TemplateParser.parse_module_references(template)
        
        # Filter to only modules we have and should execute in this stage
        stage_module_names = [
            name for name in module_names 
            if name in modules_by_name and self._should_execute_module(modules_by_name[name])
        ]
        
        if not stage_module_names:
            return template
        
        logger.debug(f"Stage {self.STAGE_NUMBER}: Resolving {len(stage_module_names)} modules: {stage_module_names}")
        
        resolved_template = template
        
        for module_name in stage_module_names:
            module_ref = f"@{module_name}"
            module = modules_by_name[module_name]
            
            # Check for circular dependency
            if module_name in self._resolution_stack:
                warnings.append(ModuleResolutionWarning(
                    module_name=module_name,
                    warning_type="circular_dependency", 
                    message=f"Circular dependency detected with module '{module_name}'",
                    stage=self.STAGE_NUMBER
                ))
                continue
            
            # Add to resolution stack
            self._resolution_stack.add(module_name)
            
            try:
                module_content = self._process_module(
                    module=module,
                    conversation_id=conversation_id,
                    persona_id=persona_id,
                    db_session=db_session,
                    trigger_context=trigger_context,
                    warnings=warnings,
                    current_provider=current_provider,
                    current_provider_settings=current_provider_settings,
                    current_chat_controls=current_chat_controls,
                    session_id=session_id
                )
                
                # Replace module reference with resolved content
                resolved_template = resolved_template.replace(module_ref, module_content)
                
                # Track successfully resolved module
                if module_name not in resolved_modules:
                    resolved_modules.append(module_name)
                    
            except Exception as e:
                logger.error(f"Error processing module '{module_name}' in stage {self.STAGE_NUMBER}: {e}")
                warnings.append(ModuleResolutionWarning(
                    module_name=module_name,
                    warning_type="processing_error",
                    message=f"Error processing module: {str(e)}",
                    stage=self.STAGE_NUMBER
                ))
            finally:
                # Remove from resolution stack
                self._resolution_stack.discard(module_name)
        
        return resolved_template
    
    def _should_execute_module(self, module: Module) -> bool:
        """
        Determine if a module should execute in this stage.
        
        This is stage-specific and should be overridden by each stage executor.
        
        Args:
            module: Module to check
            
        Returns:
            True if module should execute in this stage
        """
        return True  # Default implementation - override in subclasses
    
    def _process_module(
        self,
        module: Module,
        conversation_id: Optional[str] = None,
        persona_id: Optional[str] = None,
        db_session: Optional[Session] = None,
        trigger_context: Optional[Dict[str, Any]] = None,
        warnings: Optional[List[ModuleResolutionWarning]] = None,
        current_provider: Optional[str] = None,
        current_provider_settings: Optional[Dict[str, Any]] = None,
        current_chat_controls: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> str:
        """
        Process a single module and return its resolved content.
        
        This will delegate to the appropriate execution engine based on module type.
        
        Args:
            module: Module to process
            conversation_id: Optional conversation context
            persona_id: Optional persona context
            db_session: Optional database session
            trigger_context: Optional trigger context
            warnings: Optional warnings list
            current_provider: Current provider for context
            current_provider_settings: Provider settings for context
            current_chat_controls: Chat controls for context
            
        Returns:
            Resolved module content as string
        """
        from ....models import ModuleType
        from ..execution import SimpleExecutor, ScriptExecutor
        
        try:
            if module.type == ModuleType.SIMPLE:
                # Simple text module
                executor = SimpleExecutor()
                return executor.execute(module, {})
            
            elif module.type == ModuleType.ADVANCED:
                # Advanced script module
                executor = ScriptExecutor()
                context = {
                    'conversation_id': conversation_id,
                    'persona_id': persona_id,
                    'db_session': db_session,
                    'trigger_context': trigger_context or {},
                    'current_provider': current_provider,
                    'current_provider_settings': current_provider_settings or {},
                    'current_chat_controls': current_chat_controls or {},
                    'session_id': session_id
                }
                return executor.execute(module, context)
            
            else:
                logger.warning(f"Unknown module type: {module.type}")
                return f"[Unknown module type: {module.type}]"
                
        except Exception as e:
            logger.error(f"Error executing module '{module.name}': {e}")
            if warnings is not None:
                warnings.append(ModuleResolutionWarning(
                    module_name=module.name,
                    warning_type="execution_error",
                    message=f"Module execution failed: {str(e)}",
                    stage=self.STAGE_NUMBER
                ))
            return f"[Error in module {module.name}: {str(e)}]"