"""
Modules API endpoints for Project 2501.
Provides full CRUD operations for cognitive system modules.
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.database.connection import get_db
from app.models import Module, ModuleType, ExecutionTiming

logger = logging.getLogger(__name__)

router = APIRouter()


# Pydantic models for request/response validation

class ModuleCreateRequest(BaseModel):
    """Request model for creating a new module."""
    name: str = Field(..., min_length=1, max_length=255, description="Module name")
    description: Optional[str] = Field(None, description="Module description")
    content: Optional[str] = Field(None, description="Module content")
    type: ModuleType = Field(..., description="Module type (simple or advanced)")
    
    # Advanced module fields (optional)
    trigger_pattern: Optional[str] = Field(None, max_length=500, description="Trigger pattern for advanced modules")
    script: Optional[str] = Field(None, description="Python script for advanced modules")
    timing: Optional[ExecutionTiming] = Field(None, description="Execution timing for advanced modules")
    
    model_config = ConfigDict(use_enum_values=True)


class ModuleUpdateRequest(BaseModel):
    """Request model for updating an existing module."""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Module name")
    description: Optional[str] = Field(None, description="Module description")
    content: Optional[str] = Field(None, description="Module content")
    type: Optional[ModuleType] = Field(None, description="Module type (simple or advanced)")
    
    # Advanced module fields
    trigger_pattern: Optional[str] = Field(None, max_length=500, description="Trigger pattern for advanced modules")
    script: Optional[str] = Field(None, description="Python script for advanced modules")
    timing: Optional[ExecutionTiming] = Field(None, description="Execution timing for advanced modules")
    
    model_config = ConfigDict(use_enum_values=True)


class ModuleResponse(BaseModel):
    """Response model for module data."""
    id: str
    name: str
    description: Optional[str]
    content: Optional[str]
    type: str
    trigger_pattern: Optional[str]
    script: Optional[str]
    timing: Optional[str]
    is_active: bool
    created_at: str
    updated_at: str
    
    model_config = ConfigDict(from_attributes=True)
        
    @classmethod
    def from_module(cls, module: Module) -> 'ModuleResponse':
        """Create response model from Module database object."""
        return cls(
            id=str(module.id),
            name=module.name,
            description=module.description,
            content=module.content,
            type=module.type.value,
            trigger_pattern=module.trigger_pattern,
            script=module.script,
            timing=module.timing.value if module.timing else None,
            is_active=module.is_active,
            created_at=module.created_at.isoformat(),
            updated_at=module.updated_at.isoformat()
        )


# CRUD endpoints

@router.post("/modules", response_model=ModuleResponse, status_code=201)
def create_module(
    module_data: ModuleCreateRequest,
    db: Session = Depends(get_db)
) -> ModuleResponse:
    """
    Create a new module.
    
    Args:
        module_data: Module data from request
        db: Database session
        
    Returns:
        Created module data
        
    Raises:
        HTTPException: If creation fails
    """
    logger.info(f"Creating new module: {module_data.name}")
    
    try:
        # Create new module instance
        new_module = Module(
            name=module_data.name,
            description=module_data.description,
            content=module_data.content,
            type=module_data.type,
            trigger_pattern=module_data.trigger_pattern,
            script=module_data.script,
            timing=module_data.timing
        )
        
        # Save to database
        db.add(new_module)
        db.commit()
        db.refresh(new_module)
        
        logger.info(f"Created module with ID: {new_module.id}")
        return ModuleResponse.from_module(new_module)
        
    except SQLAlchemyError as e:
        logger.error(f"Database error creating module: {e}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create module: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error creating module: {e}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )


@router.get("/modules", response_model=List[ModuleResponse])
def list_modules(
    type: Optional[ModuleType] = Query(None, description="Filter by module type"),
    active_only: bool = Query(True, description="Only return active modules"),
    db: Session = Depends(get_db)
) -> List[ModuleResponse]:
    """
    List all modules with optional filtering.
    
    Args:
        type: Optional filter by module type
        active_only: Only return active modules
        db: Database session
        
    Returns:
        List of modules
    """
    logger.info(f"Listing modules with filters: type={type}, active_only={active_only}")
    
    try:
        query = db.query(Module)
        
        if active_only:
            query = query.filter(Module.is_active == True)
        
        if type:
            query = query.filter(Module.type == type)
        
        # Order by creation date, newest first
        modules = query.order_by(Module.created_at.desc()).all()
        
        logger.info(f"Found {len(modules)} modules")
        return [ModuleResponse.from_module(module) for module in modules]
        
    except SQLAlchemyError as e:
        logger.error(f"Database error listing modules: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list modules: {str(e)}"
        )


@router.get("/modules/{module_id}", response_model=ModuleResponse)
def get_module(
    module_id: UUID,
    db: Session = Depends(get_db)
) -> ModuleResponse:
    """
    Get a specific module by ID.
    
    Args:
        module_id: Module UUID
        db: Database session
        
    Returns:
        Module data
        
    Raises:
        HTTPException: If module not found
    """
    logger.info(f"Getting module: {module_id}")
    
    try:
        module = db.query(Module).filter(Module.id == module_id).first()
        
        if not module:
            logger.warning(f"Module not found: {module_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Module with ID {module_id} not found"
            )
        
        return ModuleResponse.from_module(module)
        
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error getting module: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get module: {str(e)}"
        )


@router.put("/modules/{module_id}", response_model=ModuleResponse)
def update_module(
    module_id: UUID,
    update_data: ModuleUpdateRequest,
    db: Session = Depends(get_db)
) -> ModuleResponse:
    """
    Update an existing module.
    
    Args:
        module_id: Module UUID
        update_data: Updated module data
        db: Database session
        
    Returns:
        Updated module data
        
    Raises:
        HTTPException: If module not found or update fails
    """
    logger.info(f"Updating module: {module_id}")
    
    try:
        # Find existing module
        module = db.query(Module).filter(Module.id == module_id).first()
        
        if not module:
            logger.warning(f"Module not found for update: {module_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Module with ID {module_id} not found"
            )
        
        # Update fields that were provided
        update_dict = update_data.model_dump(exclude_unset=True)
        
        for field, value in update_dict.items():
            setattr(module, field, value)
        
        # Save changes
        db.commit()
        db.refresh(module)
        
        logger.info(f"Updated module: {module_id}")
        return ModuleResponse.from_module(module)
        
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error updating module: {e}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update module: {str(e)}"
        )


@router.delete("/modules/{module_id}", status_code=204)
def delete_module(
    module_id: UUID,
    db: Session = Depends(get_db)
) -> None:
    """
    Delete a module.
    
    Args:
        module_id: Module UUID
        db: Database session
        
    Raises:
        HTTPException: If module not found or deletion fails
    """
    logger.info(f"Deleting module: {module_id}")
    
    try:
        # Find existing module
        module = db.query(Module).filter(Module.id == module_id).first()
        
        if not module:
            logger.warning(f"Module not found for deletion: {module_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Module with ID {module_id} not found"
            )
        
        # Delete module
        db.delete(module)
        db.commit()
        
        logger.info(f"Deleted module: {module_id}")
        
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error deleting module: {e}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete module: {str(e)}"
        )