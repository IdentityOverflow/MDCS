"""
Module Resolution Service for the Cognitive Engine.

Handles parsing @module_name references in templates and resolving them
to their actual content with proper error handling and circular dependency detection.
"""

import re
import logging
from typing import List, Dict, Set, Optional
from dataclasses import dataclass
from sqlalchemy.orm import Session

from app.models import Module
from app.database.connection import get_db

logger = logging.getLogger(__name__)

# Configuration constants
MAX_RECURSION_DEPTH = 10
MODULE_NAME_PATTERN = r'(?<!\\)@([a-z][a-z0-9_]{0,49})'  # Negative lookbehind to exclude escaped @
ESCAPED_MODULE_PATTERN = r'\\@([a-z][a-z0-9_]{0,49})'  # Pattern for escaped modules
MODULE_NAME_MAX_LENGTH = 50


@dataclass
class ModuleResolutionWarning:
    """Warning information for module resolution issues."""
    module_name: str
    warning_type: str  # 'module_not_found', 'circular_dependency', 'max_depth_exceeded'
    message: str


@dataclass
class TemplateResolutionResult:
    """Result of template resolution with content and warnings."""
    resolved_template: str
    warnings: List[ModuleResolutionWarning]
    resolved_modules: List[str]  # List of successfully resolved module names


class ModuleResolver:
    """
    Service for resolving @module_name references in templates.
    
    Handles recursive resolution, circular dependency detection,
    and provides comprehensive error reporting.
    """
    
    def __init__(self, db_session: Optional[Session] = None):
        """
        Initialize the module resolver.
        
        Args:
            db_session: Optional database session. If not provided, will get one from connection pool.
        """
        self.db_session = db_session
        self._resolution_stack: Set[str] = set()  # Track modules being resolved to detect cycles
    
    def resolve_template(self, template: str) -> TemplateResolutionResult:
        """
        Resolve all @module_name references in a template.
        
        Args:
            template: The template string containing @module_name references
            
        Returns:
            TemplateResolutionResult with resolved content and any warnings
        """
        if not template:
            return TemplateResolutionResult(
                resolved_template="",
                warnings=[],
                resolved_modules=[]
            )
        
        warnings: List[ModuleResolutionWarning] = []
        resolved_modules: List[str] = []
        
        # Reset resolution stack for new template
        self._resolution_stack = set()
        
        try:
            # First, handle escaped modules by temporarily replacing them
            escaped_placeholders = {}
            escaped_counter = 0
            
            def escape_replacement(match):
                nonlocal escaped_counter
                placeholder = f"__ESCAPED_MODULE_{escaped_counter}__"
                escaped_placeholders[placeholder] = f"@{match.group(1)}"
                escaped_counter += 1
                return placeholder
            
            # Replace escaped modules with placeholders
            template_with_placeholders = re.sub(ESCAPED_MODULE_PATTERN, escape_replacement, template)
            
            # Resolve normal modules
            resolved_content = self._resolve_recursive(
                template_with_placeholders, 
                warnings, 
                resolved_modules, 
                depth=0
            )
            
            # Restore escaped modules (remove backslash)
            for placeholder, original in escaped_placeholders.items():
                resolved_content = resolved_content.replace(placeholder, original)
            
            return TemplateResolutionResult(
                resolved_template=resolved_content,
                warnings=warnings,
                resolved_modules=list(set(resolved_modules))  # Remove duplicates
            )
            
        except Exception as e:
            logger.error(f"Unexpected error during template resolution: {e}")
            warnings.append(ModuleResolutionWarning(
                module_name="",
                warning_type="resolution_error",
                message=f"Unexpected error during resolution: {str(e)}"
            ))
            
            return TemplateResolutionResult(
                resolved_template=template,  # Return original on error
                warnings=warnings,
                resolved_modules=resolved_modules
            )
    
    def _resolve_recursive(
        self, 
        template: str, 
        warnings: List[ModuleResolutionWarning], 
        resolved_modules: List[str], 
        depth: int
    ) -> str:
        """
        Recursively resolve module references in template.
        
        Args:
            template: Template to resolve
            warnings: List to collect warnings
            resolved_modules: List to collect successfully resolved module names
            depth: Current recursion depth
            
        Returns:
            Template with module references resolved
        """
        # Check maximum recursion depth
        if depth > MAX_RECURSION_DEPTH:
            warnings.append(ModuleResolutionWarning(
                module_name="",
                warning_type="max_depth_exceeded",
                message=f"Maximum recursion depth ({MAX_RECURSION_DEPTH}) exceeded"
            ))
            return template
        
        # Parse module references in current template
        module_names = self._parse_module_references(template)
        
        if not module_names:
            return template  # No modules to resolve
        
        # Get modules from database
        modules = self._get_modules_by_names(module_names)
        modules_by_name = {module.name: module for module in modules}
        
        # Track missing modules
        found_module_names = set(modules_by_name.keys())
        missing_modules = set(module_names) - found_module_names
        
        for missing_module in missing_modules:
            warnings.append(ModuleResolutionWarning(
                module_name=missing_module,
                warning_type="module_not_found",
                message=f"Module '{missing_module}' not found"
            ))
        
        # Resolve each module reference
        resolved_template = template
        
        for module_name in module_names:
            module_ref = f"@{module_name}"
            
            if module_name in missing_modules:
                # Keep missing module as-is (don't replace with empty string)
                continue
            
            # Check for circular dependency
            if module_name in self._resolution_stack:
                warnings.append(ModuleResolutionWarning(
                    module_name=module_name,
                    warning_type="circular_dependency",
                    message=f"Circular dependency detected with module '{module_name}'"
                ))
                # Keep circular dependency module as-is (don't replace with empty string)
                continue
            
            # Add to resolution stack
            self._resolution_stack.add(module_name)
            
            try:
                module = modules_by_name[module_name]
                module_content = module.content or ""  # Handle None content
                
                # Recursively resolve the module content
                resolved_content = self._resolve_recursive(
                    module_content, 
                    warnings, 
                    resolved_modules, 
                    depth + 1
                )
                
                # Replace module reference with resolved content
                resolved_template = resolved_template.replace(module_ref, resolved_content)
                
                # Track successfully resolved module
                if module_name not in resolved_modules:
                    resolved_modules.append(module_name)
                
            finally:
                # Remove from resolution stack
                self._resolution_stack.discard(module_name)
        
        return resolved_template
    
    def _parse_module_references(self, template: str) -> List[str]:
        """
        Parse @module_name references from template.
        
        Args:
            template: Template string to parse
            
        Returns:
            List of unique module names found (without @ prefix)
        """
        if not template:
            return []
        
        # Find all @module_name patterns
        matches = re.findall(MODULE_NAME_PATTERN, template)
        
        # Return unique module names
        return list(set(matches))
    
    def _get_modules_by_names(self, module_names: List[str]) -> List[Module]:
        """
        Retrieve modules from database by their names.
        
        Args:
            module_names: List of module names to retrieve
            
        Returns:
            List of Module objects found in database
        """
        if not module_names:
            return []
        
        # Get database session
        db = self.db_session
        if db is None:
            db = next(get_db())
        
        try:
            # Query modules by name (only active modules)
            modules = db.query(Module).filter(
                Module.name.in_(module_names),
                Module.is_active == True
            ).all()
            
            return modules
            
        except Exception as e:
            logger.error(f"Database error retrieving modules: {e}")
            return []
    
    @staticmethod
    def validate_module_name(name: str) -> bool:
        """
        Validate that a module name follows the required format.
        
        Rules:
        - Only lowercase letters, numbers, and underscores
        - Must start with a letter
        - Max length 50 characters
        
        Args:
            name: Module name to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not name:
            return False
        
        if len(name) > MODULE_NAME_MAX_LENGTH:
            return False
        
        # Check pattern: starts with letter, contains only a-z, 0-9, _
        pattern = r'^[a-z][a-z0-9_]*$'
        return bool(re.match(pattern, name))


# Convenience function for standalone usage
def resolve_template(template: str, db_session: Optional[Session] = None) -> TemplateResolutionResult:
    """
    Convenience function to resolve a template.
    
    Args:
        template: Template string to resolve
        db_session: Optional database session
        
    Returns:
        TemplateResolutionResult with resolved content and warnings
    """
    resolver = ModuleResolver(db_session)
    return resolver.resolve_template(template)