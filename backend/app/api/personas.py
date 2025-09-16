"""
Personas API endpoints for Project 2501.
Provides full CRUD operations for AI personas.
"""

import logging
from typing import List, Optional
from uuid import UUID
import uuid
import shutil
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File
from pydantic import BaseModel, Field, ConfigDict, field_validator
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.database.connection import get_db
from app.models import Persona

logger = logging.getLogger(__name__)

router = APIRouter()


# Pydantic models for request/response validation

class PersonaCreateRequest(BaseModel):
    """Request model for creating a new persona."""
    name: str = Field(..., min_length=1, max_length=255, description="Persona name")
    description: Optional[str] = Field(None, description="Persona description")
    template: str = Field(..., min_length=1, description="Persona template with module placeholders")
    mode: str = Field(..., description="Operating mode: reactive or autonomous")
    loop_frequency: Optional[str] = Field(None, description="Loop frequency for autonomous mode")
    first_message: Optional[str] = Field(None, description="Optional first message")
    image_path: Optional[str] = Field(None, description="Path to persona image")
    
    model_config = ConfigDict(use_enum_values=True)
    
    @field_validator('mode')
    def validate_mode(cls, v):
        if v not in ['reactive', 'autonomous']:
            raise ValueError('Mode must be either "reactive" or "autonomous"')
        return v
    
    @field_validator('loop_frequency')
    def validate_loop_frequency(cls, v):
        if v is not None:
            try:
                float(v)
            except (ValueError, TypeError):
                raise ValueError('Loop frequency must be a valid number')
        return v


class PersonaUpdateRequest(BaseModel):
    """Request model for updating an existing persona."""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Persona name")
    description: Optional[str] = Field(None, description="Persona description")
    template: Optional[str] = Field(None, min_length=1, description="Persona template")
    mode: Optional[str] = Field(None, description="Operating mode: reactive or autonomous")
    loop_frequency: Optional[str] = Field(None, description="Loop frequency for autonomous mode")
    first_message: Optional[str] = Field(None, description="Optional first message")
    image_path: Optional[str] = Field(None, description="Path to persona image")
    
    model_config = ConfigDict(use_enum_values=True)
    
    @field_validator('mode')
    def validate_mode(cls, v):
        if v is not None and v not in ['reactive', 'autonomous']:
            raise ValueError('Mode must be either "reactive" or "autonomous"')
        return v
    
    @field_validator('loop_frequency')
    def validate_loop_frequency(cls, v):
        if v is not None:
            try:
                float(v)
            except (ValueError, TypeError):
                raise ValueError('Loop frequency must be a valid number')
        return v


class PersonaResponse(BaseModel):
    """Response model for persona data."""
    id: str
    name: str
    description: Optional[str]
    template: str
    mode: str
    loop_frequency: Optional[str]
    first_message: Optional[str]
    image_path: Optional[str]
    is_active: bool
    created_at: str
    updated_at: str
    
    model_config = ConfigDict(from_attributes=True)
        
    @classmethod
    def from_persona(cls, persona: Persona) -> 'PersonaResponse':
        """Create response model from Persona database object."""
        return cls(
            id=str(persona.id),
            name=persona.name,
            description=persona.description,
            template=persona.template,
            mode=persona.mode,
            loop_frequency=persona.loop_frequency,
            first_message=persona.first_message,
            image_path=persona.image_path,
            is_active=persona.is_active,
            created_at=persona.created_at.isoformat(),
            updated_at=persona.updated_at.isoformat()
        )


# CRUD endpoints

@router.post("/personas", response_model=PersonaResponse, status_code=201)
def create_persona(
    persona_data: PersonaCreateRequest,
    db: Session = Depends(get_db)
) -> PersonaResponse:
    """
    Create a new persona.
    
    Args:
        persona_data: Persona data from request
        db: Database session
        
    Returns:
        Created persona data
        
    Raises:
        HTTPException: If creation fails
    """
    logger.info(f"Creating new persona: {persona_data.name}")
    
    try:
        # Create new persona instance
        new_persona = Persona(
            name=persona_data.name,
            description=persona_data.description,
            template=persona_data.template,
            mode=persona_data.mode,
            loop_frequency=persona_data.loop_frequency,
            first_message=persona_data.first_message,
            image_path=persona_data.image_path
        )
        
        # Save to database
        db.add(new_persona)
        db.commit()
        db.refresh(new_persona)
        
        logger.info(f"Created persona with ID: {new_persona.id}")
        return PersonaResponse.from_persona(new_persona)
        
    except SQLAlchemyError as e:
        logger.error(f"Database error creating persona: {e}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create persona: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error creating persona: {e}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )


@router.get("/personas", response_model=List[PersonaResponse])
def list_personas(
    mode: Optional[str] = Query(None, description="Filter by persona mode"),
    active_only: bool = Query(True, description="Only return active personas"),
    db: Session = Depends(get_db)
) -> List[PersonaResponse]:
    """
    List all personas with optional filtering.
    
    Args:
        mode: Optional filter by persona mode (reactive/autonomous)
        active_only: Only return active personas
        db: Database session
        
    Returns:
        List of personas
    """
    logger.debug(f"Listing personas with filters: mode={mode}, active_only={active_only}")
    
    try:
        query = db.query(Persona)
        
        if active_only:
            query = query.filter(Persona.is_active == True)
        
        if mode:
            query = query.filter(Persona.mode == mode)
        
        # Order by creation date, newest first
        personas = query.order_by(Persona.created_at.desc()).all()
        
        logger.debug(f"Found {len(personas)} personas")
        return [PersonaResponse.from_persona(persona) for persona in personas]
        
    except SQLAlchemyError as e:
        logger.error(f"Database error listing personas: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list personas: {str(e)}"
        )


@router.get("/personas/{persona_id}", response_model=PersonaResponse)
def get_persona(
    persona_id: UUID,
    db: Session = Depends(get_db)
) -> PersonaResponse:
    """
    Get a specific persona by ID.
    
    Args:
        persona_id: Persona UUID
        db: Database session
        
    Returns:
        Persona data
        
    Raises:
        HTTPException: If persona not found
    """
    logger.debug(f"Getting persona: {persona_id}")
    
    try:
        persona = db.query(Persona).filter(Persona.id == persona_id).first()
        
        if not persona:
            logger.warning(f"Persona not found: {persona_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Persona with ID {persona_id} not found"
            )
        
        return PersonaResponse.from_persona(persona)
        
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error getting persona: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get persona: {str(e)}"
        )


@router.put("/personas/{persona_id}", response_model=PersonaResponse)
def update_persona(
    persona_id: UUID,
    update_data: PersonaUpdateRequest,
    db: Session = Depends(get_db)
) -> PersonaResponse:
    """
    Update an existing persona.
    
    Args:
        persona_id: Persona UUID
        update_data: Updated persona data
        db: Database session
        
    Returns:
        Updated persona data
        
    Raises:
        HTTPException: If persona not found or update fails
    """
    logger.info(f"Updating persona: {persona_id}")
    
    try:
        # Find existing persona
        persona = db.query(Persona).filter(Persona.id == persona_id).first()
        
        if not persona:
            logger.warning(f"Persona not found for update: {persona_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Persona with ID {persona_id} not found"
            )
        
        # Update fields that were provided
        update_dict = update_data.model_dump(exclude_unset=True)
        
        for field, value in update_dict.items():
            setattr(persona, field, value)
        
        # Save changes
        db.commit()
        db.refresh(persona)
        
        logger.info(f"Updated persona: {persona_id}")
        return PersonaResponse.from_persona(persona)
        
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error updating persona: {e}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update persona: {str(e)}"
        )


@router.delete("/personas/{persona_id}", status_code=204)
def delete_persona(
    persona_id: UUID,
    db: Session = Depends(get_db)
) -> None:
    """
    Delete a persona.
    
    Args:
        persona_id: Persona UUID
        db: Database session
        
    Raises:
        HTTPException: If persona not found or deletion fails
    """
    logger.info(f"Deleting persona: {persona_id}")
    
    try:
        # Find existing persona
        persona = db.query(Persona).filter(Persona.id == persona_id).first()
        
        if not persona:
            logger.warning(f"Persona not found for deletion: {persona_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Persona with ID {persona_id} not found"
            )
        
        # Store image path for cleanup before deletion
        image_path = persona.image_path
        
        # Delete persona from database
        db.delete(persona)
        db.commit()
        
        # Clean up image file if it exists
        if image_path and image_path.startswith('/static/'):
            try:
                file_path = Path(__file__).parent.parent.parent / image_path.lstrip('/')
                if file_path.exists():
                    file_path.unlink()
                    logger.info(f"Deleted image file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to delete image file {image_path}: {e}")
                # Don't fail the entire operation if file deletion fails
        
        logger.info(f"Deleted persona: {persona_id}")
        
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error deleting persona: {e}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete persona: {str(e)}"
        )


@router.post("/personas/upload-image")
def upload_persona_image(
    file: UploadFile = File(...)
) -> dict:
    """
    Upload an image for a persona.
    
    Args:
        file: Uploaded image file
        
    Returns:
        Dictionary with image_path for storing in persona
        
    Raises:
        HTTPException: If upload fails or invalid file
    """
    logger.info(f"Uploading persona image: {file.filename}")
    
    # Validate file type
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(
            status_code=400,
            detail="File must be an image"
        )
    
    # Validate file size (5MB limit)
    if hasattr(file, 'size') and file.size and file.size > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="File size must be less than 5MB"
        )
    
    try:
        # Generate unique filename using UUID
        file_uuid = str(uuid.uuid4())
        file_extension = Path(file.filename or "image.png").suffix
        unique_filename = f"{file_uuid}{file_extension}"
        
        # Create upload directory path
        upload_dir = Path(__file__).parent.parent.parent / "static" / "images" / "personas"
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Save file
        file_path = upload_dir / unique_filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Return web-accessible path
        web_path = f"/static/images/personas/{unique_filename}"
        
        logger.info(f"Successfully uploaded image to: {web_path}")
        return {"image_path": web_path}
        
    except Exception as e:
        logger.error(f"Error uploading persona image: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload image: {str(e)}"
        )