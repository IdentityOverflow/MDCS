"""
Template Resolution API endpoints for the Cognitive Engine.

Provides endpoints for resolving @module_name references in templates
with comprehensive error handling and validation.
"""

import logging
from typing import Optional, List, Dict, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.services.module_resolver import ModuleResolver, TemplateResolutionResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/templates", tags=["templates"])


class TemplateResolveRequest(BaseModel):
    """Request model for template resolution."""
    template: str = Field(..., description="Template string to resolve")
    persona_id: Optional[str] = Field(None, description="Optional persona ID for context")


class ModuleWarning(BaseModel):
    """Warning information for module resolution issues."""
    module_name: str = Field(..., description="Name of the module that caused the warning")
    warning_type: str = Field(..., description="Type of warning (module_not_found, circular_dependency, etc.)")
    message: str = Field(..., description="Human-readable warning message")


class TemplateResolveResponse(BaseModel):
    """Response model for template resolution."""
    resolved_template: str = Field(..., description="Template with all module references resolved")
    warnings: List[ModuleWarning] = Field(..., description="List of warnings encountered during resolution")
    resolved_modules: List[str] = Field(..., description="List of module names that were successfully resolved")


@router.post("/resolve", response_model=TemplateResolveResponse, status_code=200)
def resolve_template(
    request: TemplateResolveRequest,
    db: Session = Depends(get_db)
) -> TemplateResolveResponse:
    """
    Resolve @module_name references in a template.
    
    This endpoint takes a template string containing @module_name references
    and resolves them to their actual content from the database.
    
    Args:
        request: Template resolution request with template string and optional persona_id
        db: Database session
        
    Returns:
        TemplateResolveResponse with resolved template and any warnings
        
    Raises:
        HTTPException: For various error conditions
    """
    logger.info(f"Resolving template with {len(request.template)} characters")
    
    try:
        # Create module resolver with database session
        resolver = ModuleResolver(db_session=db)
        
        # Resolve the template with optional context for advanced modules
        result: TemplateResolutionResult = resolver.resolve_template(
            request.template,
            conversation_id="api-template-resolution",  # Placeholder for API usage
            persona_id=request.persona_id,
            db_session=db,
            trigger_context={}  # No trigger context for template API
        )
        
        # Convert warnings to response format
        warnings = [
            ModuleWarning(
                module_name=warning.module_name,
                warning_type=warning.warning_type,
                message=warning.message
            )
            for warning in result.warnings
        ]
        
        # Log warnings for monitoring
        if warnings:
            logger.warning(f"Template resolution generated {len(warnings)} warnings")
            for warning in warnings:
                logger.warning(f"  {warning.warning_type}: {warning.message}")
        
        logger.info(f"Template resolved successfully. Resolved {len(result.resolved_modules)} modules")
        
        return TemplateResolveResponse(
            resolved_template=result.resolved_template,
            warnings=warnings,
            resolved_modules=result.resolved_modules
        )
        
    except Exception as e:
        logger.error(f"Unexpected error during template resolution: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resolve template: {str(e)}"
        )


@router.get("/modules/available", response_model=List[Dict[str, Any]], status_code=200)
def list_available_modules(
    active_only: bool = True,
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    List available modules for template reference.
    
    This endpoint provides a list of modules that can be referenced in templates
    using @module_name syntax. Useful for autocomplete and validation.
    
    Args:
        active_only: Whether to only return active modules (default: True)
        db: Database session
        
    Returns:
        List of module information for template reference
        
    Raises:
        HTTPException: For database errors
    """
    logger.info(f"Listing available modules (active_only={active_only})")
    
    try:
        from app.models import Module
        
        # Query modules
        query = db.query(Module)
        if active_only:
            query = query.filter(Module.is_active == True)
        
        modules = query.order_by(Module.name).all()
        
        # Format for frontend consumption
        module_list = []
        for module in modules:
            module_info = {
                "id": str(module.id),
                "name": module.name,
                "description": module.description,
                "type": module.type.value,
                "reference": f"@{module.name}",  # How to reference in templates
                "content_preview": (module.content or "")[:100] + ("..." if (module.content or "") and len(module.content) > 100 else ""),
                "is_active": module.is_active,
                "created_at": module.created_at.isoformat(),
                "updated_at": module.updated_at.isoformat()
            }
            module_list.append(module_info)
        
        logger.info(f"Returning {len(module_list)} available modules")
        return module_list
        
    except Exception as e:
        logger.error(f"Error listing available modules: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list modules: {str(e)}"
        )


@router.post("/validate", response_model=Dict[str, Any], status_code=200)
def validate_template(
    request: TemplateResolveRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Validate a template without fully resolving it.
    
    This endpoint checks for syntax issues, missing modules, and potential
    circular dependencies without performing full resolution. Useful for
    real-time validation in template editors.
    
    Args:
        request: Template validation request
        db: Database session
        
    Returns:
        Validation result with issues found
        
    Raises:
        HTTPException: For validation errors
    """
    logger.info("Validating template")
    
    try:
        from app.services.module_resolver import ModuleResolver
        from app.models import Module
        
        resolver = ModuleResolver(db_session=db)
        
        # Parse module references
        module_names = resolver._parse_module_references(request.template)
        
        # Check which modules exist
        if module_names:
            existing_modules = db.query(Module).filter(
                Module.name.in_(module_names),
                Module.is_active == True
            ).all()
            existing_names = {module.name for module in existing_modules}
            missing_modules = set(module_names) - existing_names
        else:
            missing_modules = set()
            existing_names = set()
        
        # Validate module name format
        invalid_names = [name for name in module_names if not resolver.validate_module_name(name)]
        
        validation_result = {
            "is_valid": len(missing_modules) == 0 and len(invalid_names) == 0,
            "module_references": module_names,
            "missing_modules": list(missing_modules),
            "invalid_module_names": invalid_names,
            "existing_modules": list(existing_names),
            "total_modules_found": len(module_names)
        }
        
        logger.info(f"Template validation complete. Valid: {validation_result['is_valid']}")
        return validation_result
        
    except Exception as e:
        logger.error(f"Error validating template: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate template: {str(e)}"
        )