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
from app.services.staged_module_resolver import StagedModuleResolver, ModuleResolutionWarning

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
        # Create staged module resolver with database session
        resolver = StagedModuleResolver(db_session=db)
        
        # For template API compatibility, we need to handle persona_id more flexibly
        # and generate warnings for missing modules like the old ModuleResolver
        import re
        from app.models import Module
        
        # Parse all @module_name references from template
        template_modules = re.findall(r'@([a-z][a-z0-9_]*)', request.template)
        
        # Get all active modules from database
        all_modules = db.query(Module).filter(Module.is_active == True).all()
        available_module_names = {m.name for m in all_modules}
        
        # Prepare warnings for missing/inactive modules
        additional_warnings = []
        for module_name in template_modules:
            if module_name not in available_module_names:
                additional_warnings.append(ModuleResolutionWarning(
                    module_name=module_name,
                    warning_type="module_not_found",
                    message=f"Module '{module_name}' not found or inactive"
                ))
        
        # Resolve the template using Stage 1 and Stage 2 (preparation stages)
        # Use None for persona_id if invalid UUID to avoid database errors
        safe_persona_id = None
        if request.persona_id:
            try:
                import uuid
                uuid.UUID(request.persona_id)
                safe_persona_id = request.persona_id
            except ValueError:
                # Invalid UUID format, use None
                pass
                
        result = resolver.resolve_template_stage1_and_stage2(
            request.template,
            conversation_id="api-template-resolution",  # Placeholder for API usage
            persona_id=safe_persona_id,
            db_session=db,
            trigger_context={}  # No trigger context for template API
        )
        
        # Post-process to track ALL resolved modules (including recursive ones) for API compatibility
        # The StagedModuleResolver only tracks direct resolutions, but we need comprehensive tracking
        
        def find_all_resolved_modules(original_template: str, resolved_template: str, db_session) -> List[str]:
            """Find all modules that were resolved by comparing templates before and after."""
            # Get all active modules (handle None content gracefully)
            all_modules_dict = {m.name: (m.content or '') for m in db_session.query(Module).filter(Module.is_active == True).all()}
            resolved_modules = set()
            
            # Simple approach: find all module references that were successfully replaced
            import re
            original_refs = set(re.findall(r'@([a-z][a-z0-9_]*)', original_template))
            final_refs = set(re.findall(r'@([a-z][a-z0-9_]*)', resolved_template))
            
            # Any reference that was in original but not in final was successfully resolved
            directly_resolved = original_refs - final_refs
            resolved_modules.update(directly_resolved)
            
            # For recursive tracking, we need to check if any resolved module content contained other modules
            # This is complex, so let's use a simpler approach: check what the resolver actually processed
            for module_name in directly_resolved:
                if module_name in all_modules_dict:
                    module_content = all_modules_dict[module_name] or ''  # Handle None content
                    # Find any @references in this module's content
                    nested_refs = re.findall(r'@([a-z][a-z0-9_]*)', module_content)
                    for nested_ref in nested_refs:
                        # If this nested reference is not in the final result, it was also resolved
                        if f'@{nested_ref}' not in resolved_template and nested_ref in all_modules_dict:
                            resolved_modules.add(nested_ref)
            
            return sorted(list(resolved_modules))
        
        # Get comprehensive resolved modules list
        complete_resolved_modules = find_all_resolved_modules(request.template, result.resolved_template, db)
        result.resolved_modules = complete_resolved_modules
        
        # Convert warnings to response format and add our additional warnings
        warnings = [
            ModuleWarning(
                module_name=warning.module_name,
                warning_type=warning.warning_type,
                message=warning.message
            )
            for warning in result.warnings + additional_warnings
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
            resolved_modules=result.resolved_modules  # Now contains all recursively resolved modules
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