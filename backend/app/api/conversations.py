"""
Conversation API endpoints for managing chat conversations.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models.conversation import Conversation, Message
from app.models.persona import Persona
from pydantic import BaseModel, Field
import uuid


router = APIRouter(prefix="/api/conversations", tags=["conversations"])


# Pydantic models for request/response
class ConversationCreate(BaseModel):
    """Request model for creating a conversation."""
    title: str = Field(..., min_length=1, max_length=255)
    persona_id: Optional[str] = None
    provider_type: Optional[str] = None
    provider_config: Optional[dict] = None


class ConversationUpdate(BaseModel):
    """Request model for updating a conversation."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)


class MessageResponse(BaseModel):
    """Response model for messages."""
    id: str
    role: str
    content: str
    thinking: Optional[str] = None
    extra_data: Optional[dict] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}
    
    @classmethod
    def from_message(cls, message: Message) -> 'MessageResponse':
        """Create response model from Message database object."""
        return cls(
            id=str(message.id),
            role=message.role.value,
            content=message.content,
            thinking=message.thinking,
            extra_data=message.extra_data,
            input_tokens=message.input_tokens,
            output_tokens=message.output_tokens,
            created_at=message.created_at.isoformat(),
            updated_at=message.updated_at.isoformat()
        )


class ConversationResponse(BaseModel):
    """Response model for conversations."""
    id: str
    title: str
    persona_id: Optional[str] = None
    provider_type: Optional[str] = None
    provider_config: Optional[dict] = None
    messages: List[MessageResponse] = []
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}
    
    @classmethod
    def from_conversation(cls, conversation: Conversation) -> 'ConversationResponse':
        """Create response model from Conversation database object."""
        return cls(
            id=str(conversation.id),
            title=conversation.title,
            persona_id=str(conversation.persona_id) if conversation.persona_id else None,
            provider_type=conversation.provider_type,
            provider_config=conversation.provider_config,
            messages=[MessageResponse.from_message(msg) for msg in conversation.messages],
            created_at=conversation.created_at.isoformat(),
            updated_at=conversation.updated_at.isoformat()
        )


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
def create_conversation(
    conversation_data: ConversationCreate,
    db: Session = Depends(get_db)
) -> ConversationResponse:
    """Create a new conversation."""
    
    # Validate persona exists if provided
    if conversation_data.persona_id:
        try:
            persona_uuid = uuid.UUID(conversation_data.persona_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid persona ID format"
            )
        
        persona = db.query(Persona).filter(Persona.id == persona_uuid).first()
        if not persona:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Persona not found"
            )
    
    # Create conversation
    conversation = Conversation(
        title=conversation_data.title,
        persona_id=uuid.UUID(conversation_data.persona_id) if conversation_data.persona_id else None,
        provider_type=conversation_data.provider_type,
        provider_config=conversation_data.provider_config
    )
    
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    
    return ConversationResponse.from_conversation(conversation)


@router.get("/by-persona/{persona_id}", response_model=ConversationResponse)
def get_conversation_by_persona(
    persona_id: str,
    db: Session = Depends(get_db)
) -> ConversationResponse:
    """Get the active conversation for a specific persona."""
    
    try:
        persona_uuid = uuid.UUID(persona_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid persona ID format"
        )
    
    conversation = db.query(Conversation).filter(
        Conversation.persona_id == persona_uuid
    ).first()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found for this persona"
        )
    
    return ConversationResponse.from_conversation(conversation)


@router.get("/{conversation_id}", response_model=ConversationResponse)
def get_conversation(
    conversation_id: str,
    db: Session = Depends(get_db)
) -> ConversationResponse:
    """Get a conversation by ID."""
    
    try:
        conv_uuid = uuid.UUID(conversation_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid conversation ID format"
        )
    
    conversation = db.query(Conversation).filter(Conversation.id == conv_uuid).first()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    return ConversationResponse.from_conversation(conversation)


@router.put("/{conversation_id}", response_model=ConversationResponse)
def update_conversation(
    conversation_id: str,
    update_data: ConversationUpdate,
    db: Session = Depends(get_db)
) -> ConversationResponse:
    """Update a conversation."""
    
    try:
        conv_uuid = uuid.UUID(conversation_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid conversation ID format"
        )
    
    conversation = db.query(Conversation).filter(Conversation.id == conv_uuid).first()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    # Update fields if provided
    if update_data.title is not None:
        conversation.title = update_data.title
    
    db.commit()
    db.refresh(conversation)
    
    return ConversationResponse.from_conversation(conversation)


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conversation_id: str,
    db: Session = Depends(get_db)
):
    """Delete a conversation and all its messages."""
    
    try:
        conv_uuid = uuid.UUID(conversation_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid conversation ID format"
        )
    
    conversation = db.query(Conversation).filter(Conversation.id == conv_uuid).first()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    # Delete conversation (messages will be cascade deleted)
    db.delete(conversation)
    db.commit()
    
    return None