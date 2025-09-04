"""
Template parsing and processing logic extracted from staged_module_resolver_base.py.

Handles:
- @module_name pattern matching
- Template variable resolution
- Module name validation
- Database module retrieval
"""

import re
import logging
from typing import List, Dict, Set, Optional
from sqlalchemy.orm import Session

from ...models import Module

logger = logging.getLogger(__name__)

# Configuration constants from original resolver
MODULE_NAME_PATTERN = r'(?<!\\)@([a-z][a-z0-9_]{0,49})'  # Negative lookbehind to exclude escaped @
ESCAPED_MODULE_PATTERN = r'\\@([a-z][a-z0-9_]{0,49})'  # Pattern for escaped modules
VARIABLE_PATTERN = r'\$\{([a-zA-Z_][a-zA-Z0-9_]*)\}'  # Pattern for ${variable_name}
MODULE_NAME_MAX_LENGTH = 50


class TemplateParser:
    """
    Handles template parsing and module reference extraction.
    
    Extracted from StagedModuleResolver to provide focused template processing
    capabilities without the complexity of stage orchestration.
    """
    
    @staticmethod
    def parse_module_references(template: str) -> List[str]:
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
        
        # Return unique module names preserving order
        unique_names = []
        seen = set()
        for name in matches:
            if name not in seen:
                unique_names.append(name)
                seen.add(name)
        
        return unique_names
    
    @staticmethod
    def parse_variable_references(template: str) -> List[str]:
        """
        Parse ${variable_name} references from template.
        
        Args:
            template: Template string to parse
            
        Returns:
            List of unique variable names found (without ${} wrapper)
        """
        if not template:
            return []
        
        # Find all ${variable_name} patterns
        matches = re.findall(VARIABLE_PATTERN, template)
        
        # Return unique variable names
        return list(set(matches))
    
    @staticmethod
    def has_module_references(template: str) -> bool:
        """
        Quick check if template contains any @module_name references.
        
        Args:
            template: Template string to check
            
        Returns:
            True if template contains module references
        """
        if not template:
            return False
        
        return bool(re.search(MODULE_NAME_PATTERN, template))
    
    @staticmethod
    def validate_module_name(name: str) -> bool:
        """
        Validate that a module name follows the required format.
        
        Args:
            name: Module name to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not name or not isinstance(name, str):
            return False
        
        if len(name) > MODULE_NAME_MAX_LENGTH:
            return False
        
        # Check against the pattern without the @ prefix
        pattern = r'^[a-z][a-z0-9_]{0,49}$'
        return bool(re.match(pattern, name))
    
    @staticmethod
    def substitute_variables(template: str, variables: Dict[str, str]) -> str:
        """
        Substitute ${variable_name} references with actual values.
        
        Args:
            template: Template string with variable references
            variables: Dictionary mapping variable names to values
            
        Returns:
            Template with variables substituted
        """
        if not template or not variables:
            return template
        
        result = template
        for var_name, value in variables.items():
            var_pattern = f"${{{var_name}}}"
            result = result.replace(var_pattern, str(value))
        
        return result
    
    @staticmethod
    def get_modules_by_names(module_names: List[str], db_session: Session) -> List[Module]:
        """
        Retrieve modules from database by their names.
        
        Args:
            module_names: List of module names to retrieve
            db_session: Database session
            
        Returns:
            List of Module objects found in database
        """
        if not module_names:
            return []
        
        try:
            # Query modules by name (only active modules)
            modules = db_session.query(Module).filter(
                Module.name.in_(module_names),
                Module.is_active == True
            ).all()
            
            return modules
            
        except Exception as e:
            logger.error(f"Database error retrieving modules: {e}")
            return []
    
    @staticmethod
    def find_missing_modules(template: str, available_modules: List[Module]) -> List[str]:
        """
        Find module references in template that don't have corresponding Module objects.
        
        Args:
            template: Template string to analyze
            available_modules: List of available Module objects
            
        Returns:
            List of module names that are referenced but not available
        """
        referenced_modules = TemplateParser.parse_module_references(template)
        available_names = {module.name for module in available_modules}
        
        return [name for name in referenced_modules if name not in available_names]
    
    @staticmethod
    def replace_module_references(template: str, module_substitutions: Dict[str, str]) -> str:
        """
        Replace @module_name references with provided content.
        
        Args:
            template: Template string with module references
            module_substitutions: Dict mapping module names to their resolved content
            
        Returns:
            Template with module references replaced
        """
        if not template or not module_substitutions:
            return template
        
        result = template
        for module_name, content in module_substitutions.items():
            module_ref = f"@{module_name}"
            result = result.replace(module_ref, content)
        
        return result
    
    @staticmethod  
    def unescape_module_references(template: str) -> str:
        """
        Convert escaped module references (\\@module) back to literal @module.
        
        Args:
            template: Template string that may contain escaped references
            
        Returns:
            Template with escaped references converted to literal @
        """
        if not template:
            return template
        
        # Replace \\@module_name with @module_name
        return re.sub(ESCAPED_MODULE_PATTERN, r'@\1', template)