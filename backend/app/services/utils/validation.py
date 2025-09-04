"""
Shared validation utilities for provider settings and requests.
"""

from typing import Dict, Any, List, Optional


class SettingsValidator:
    """Shared validation logic for provider settings."""
    
    @staticmethod
    def validate_required_fields(settings: Dict[str, Any], required_fields: List[str]) -> bool:
        """
        Validate that all required fields are present and non-empty.
        
        Args:
            settings: The settings dictionary to validate
            required_fields: List of field names that must be present
            
        Returns:
            True if all required fields are present and non-empty, False otherwise
        """
        return all(
            field in settings and 
            settings[field] is not None and 
            str(settings[field]).strip() != ""
            for field in required_fields
        )
    
    @staticmethod
    def validate_optional_field(settings: Dict[str, Any], field_name: str, allowed_values: List[str]) -> bool:
        """
        Validate optional field values against allowed options.
        
        Args:
            settings: The settings dictionary to validate
            field_name: Name of the field to validate
            allowed_values: List of allowed values for the field
            
        Returns:
            True if field is not present or has an allowed value, False otherwise
        """
        if field_name not in settings:
            return True
        return settings[field_name] in allowed_values
    
    @staticmethod
    def validate_url_format(url: str) -> bool:
        """
        Basic URL format validation.
        
        Args:
            url: URL string to validate
            
        Returns:
            True if URL has basic valid format, False otherwise
        """
        if not url:
            return False
        url = url.strip()
        return url.startswith(('http://', 'https://')) and len(url) > 8
    
    @staticmethod
    def normalize_url(url: str) -> str:
        """
        Normalize URL by removing trailing slashes.
        
        Args:
            url: URL string to normalize
            
        Returns:
            Normalized URL string
        """
        if not url:
            return url
        return url.rstrip('/')