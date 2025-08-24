"""
Modules API endpoints for Project 2501.
Provides full CRUD operations for cognitive system modules.
"""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.database.connection import get_db
from app.models import Module, ModuleType, ExecutionTiming
from app.core.script_engine import ScriptEngine
from app.core.script_context import ScriptExecutionContext
from app.core.script_plugins import plugin_registry
import inspect

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


class ScriptTestRequest(BaseModel):
    """Request model for testing a script."""
    script: str = Field(..., description="Python script to test")
    content: Optional[str] = Field("", description="Module content template")
    
    model_config = ConfigDict(use_enum_values=True)


class ScriptTestResponse(BaseModel):
    """Response model for script test results."""
    success: bool = Field(..., description="Whether the script executed successfully")
    resolved_content: Optional[str] = Field(None, description="Resolved module content if successful")
    outputs: Optional[dict] = Field(None, description="Script output variables")
    error: Optional[str] = Field(None, description="Error message if failed")
    traceback: Optional[str] = Field(None, description="Full traceback if failed")


class PluginFunctionInfo(BaseModel):
    """Information about a plugin function."""
    name: str = Field(..., description="Function name")
    signature: str = Field(..., description="Function signature")
    docstring: Optional[str] = Field(None, description="Function documentation")
    category: str = Field(..., description="Function category (time, conversation, utility)")
    parameters: List[Dict[str, Any]] = Field(default_factory=list, description="Parameter information")


class PluginFunctionsResponse(BaseModel):
    """Response model for plugin functions list."""
    functions: List[PluginFunctionInfo] = Field(..., description="List of available plugin functions")
    total_count: int = Field(..., description="Total number of functions")


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


@router.get("/modules/plugin-functions", response_model=PluginFunctionsResponse)
def get_plugin_functions() -> PluginFunctionsResponse:
    """
    Get information about all available plugin functions for scripting.
    
    Returns:
        Information about all plugin functions including signatures and documentation
    """
    logger.info("Getting plugin functions information")
    
    try:
        # Get all registered plugin functions
        plugin_functions = plugin_registry.get_context()
        functions_info = []
        
        for func_name, func in plugin_functions.items():
            try:
                # Get function signature
                sig = inspect.signature(func)
                signature_str = f"ctx.{func_name}{sig}"
                
                # Get docstring
                docstring = func.__doc__ or "No description available"
                
                # Get parameter information
                parameters = []
                for param_name, param in sig.parameters.items():
                    # Skip db_session as it's auto-injected
                    if param_name == 'db_session':
                        continue
                        
                    param_info = {
                        "name": param_name,
                        "type": str(param.annotation) if param.annotation != inspect.Parameter.empty else "Any",
                        "default": str(param.default) if param.default != inspect.Parameter.empty else None,
                        "required": param.default == inspect.Parameter.empty
                    }
                    parameters.append(param_info)
                
                # Categorize functions based on name patterns
                category = "utility"  # default
                if any(keyword in func_name.lower() for keyword in ['time', 'date', 'hour', 'business']):
                    category = "time"
                elif any(keyword in func_name.lower() for keyword in ['message', 'conversation', 'persona']):
                    category = "conversation"
                
                function_info = PluginFunctionInfo(
                    name=func_name,
                    signature=signature_str,
                    docstring=docstring,
                    category=category,
                    parameters=parameters
                )
                functions_info.append(function_info)
                
            except Exception as e:
                logger.warning(f"Error processing function {func_name}: {e}")
                # Add basic info even if signature processing fails
                function_info = PluginFunctionInfo(
                    name=func_name,
                    signature=f"ctx.{func_name}(...)",
                    docstring=getattr(func, '__doc__', None) or "No description available",
                    category="utility",
                    parameters=[]
                )
                functions_info.append(function_info)
        
        # Sort functions by category then name
        functions_info.sort(key=lambda f: (f.category, f.name))
        
        return PluginFunctionsResponse(
            functions=functions_info,
            total_count=len(functions_info)
        )
        
    except Exception as e:
        logger.error(f"Error getting plugin functions: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get plugin functions: {str(e)}"
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


@router.post("/modules/test-script", response_model=ScriptTestResponse)
def test_script(
    test_request: ScriptTestRequest,
    db: Session = Depends(get_db)
) -> ScriptTestResponse:
    """
    Test a Python script for advanced modules.
    
    Args:
        test_request: Script and content to test
        db: Database session
        
    Returns:
        Test results including success status, resolved content, or error details
    """
    logger.info("Testing advanced module script")
    
    try:
        # Create script engine
        script_engine = ScriptEngine()
        
        # Create execution context object
        ctx_obj = ScriptExecutionContext(
            conversation_id="test-conversation",
            persona_id="test-persona", 
            db_session=db,
            trigger_data={"test_mode": True}
        )
        
        # Create context dictionary for script execution
        context = {
            'ctx': ctx_obj,
            '__builtins__': {}  # Required for RestrictedPython
        }
        
        # Execute the script
        result = script_engine.execute_script(
            script=test_request.script,
            context=context
        )
        
        # If script executed successfully, try to resolve the content template
        resolved_content = None
        if result.success and test_request.content:
            # Simple variable substitution for testing
            resolved_content = test_request.content
            if result.outputs:
                for var_name, var_value in result.outputs.items():
                    placeholder = f"${{{var_name}}}"
                    if placeholder in resolved_content:
                        resolved_content = resolved_content.replace(placeholder, str(var_value))
        
        return ScriptTestResponse(
            success=result.success,
            resolved_content=resolved_content or test_request.content,
            outputs=result.outputs,
            error=result.error_message,
            traceback=None  # ScriptExecutionResult doesn't include traceback
        )
        
    except Exception as e:
        logger.error(f"Unexpected error testing script: {e}")
        return ScriptTestResponse(
            success=False,
            resolved_content=None,
            outputs=None,
            error=f"Unexpected error: {str(e)}",
            traceback=None
        )