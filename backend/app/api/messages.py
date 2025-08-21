"""
Message API endpoints for managing individual messages in conversations.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models.conversation import Conversation, Message, MessageRole
from pydantic import BaseModel, Field
import uuid


router = APIRouter(prefix="/api/messages", tags=["messages"])


# Pydantic models for request/response
class MessageCreate(BaseModel):
    """Request model for creating a message."""
    conversation_id: str = Field(..., description="ID of the conversation this message belongs to")
    role: str = Field(..., description="Message role: user, assistant, or system")
    content: str = Field(..., min_length=1, description="Message content")
    thinking: Optional[str] = Field(None, description="AI reasoning/thinking content")
    extra_data: Optional[dict] = Field(None, description="Additional metadata")
    input_tokens: Optional[int] = Field(None, ge=0, description="Number of input tokens")
    output_tokens: Optional[int] = Field(None, ge=0, description="Number of output tokens")


class MessageUpdate(BaseModel):
    """Request model for updating a message."""
    content: Optional[str] = Field(None, min_length=1, description="Updated message content")
    thinking: Optional[str] = Field(None, description="Updated thinking content")
    extra_data: Optional[dict] = Field(None, description="Updated metadata")
    input_tokens: Optional[int] = Field(None, ge=0, description="Updated input token count")
    output_tokens: Optional[int] = Field(None, ge=0, description="Updated output token count")


class MessageResponse(BaseModel):
    """Response model for messages."""
    id: str
    conversation_id: str
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
            conversation_id=str(message.conversation_id),
            role=message.role.value,
            content=message.content,
            thinking=message.thinking,
            extra_data=message.extra_data,
            input_tokens=message.input_tokens,
            output_tokens=message.output_tokens,
            created_at=message.created_at.isoformat(),
            updated_at=message.updated_at.isoformat()
        )


@router.post("", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def create_message(
    message_data: MessageCreate,
    db: Session = Depends(get_db)
) -> MessageResponse:
    """Create a new message in a conversation."""
    
    # Validate conversation exists
    try:
        conv_uuid = uuid.UUID(message_data.conversation_id)
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
    
    # Validate role
    try:
        role = MessageRole(message_data.role)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid role. Must be one of: {', '.join([r.value for r in MessageRole])}"
        )
    
    # Create message
    message = Message(
        conversation_id=conv_uuid,
        role=role,
        content=message_data.content,
        thinking=message_data.thinking,
        extra_data=message_data.extra_data,
        input_tokens=message_data.input_tokens,
        output_tokens=message_data.output_tokens
    )
    
    db.add(message)
    db.commit()
    db.refresh(message)
    
    return MessageResponse.from_message(message)


@router.get("/{message_id}", response_model=MessageResponse)
def get_message(
    message_id: str,
    db: Session = Depends(get_db)
) -> MessageResponse:
    """Get a message by ID."""
    
    try:
        msg_uuid = uuid.UUID(message_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid message ID format"
        )
    
    message = db.query(Message).filter(Message.id == msg_uuid).first()
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    
    return MessageResponse.from_message(message)


@router.get("/by-conversation/{conversation_id}", response_model=List[MessageResponse])
def list_messages_by_conversation(
    conversation_id: str,
    db: Session = Depends(get_db)
) -> List[MessageResponse]:
    """List all messages in a conversation, ordered by creation time."""
    
    try:
        conv_uuid = uuid.UUID(conversation_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid conversation ID format"
        )
    
    # Verify conversation exists
    conversation = db.query(Conversation).filter(Conversation.id == conv_uuid).first()
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    # Get all messages for this conversation
    messages = db.query(Message).filter(
        Message.conversation_id == conv_uuid
    ).order_by(Message.created_at).all()
    
    return [MessageResponse.from_message(msg) for msg in messages]


@router.put("/{message_id}", response_model=MessageResponse)
def update_message(
    message_id: str,
    update_data: MessageUpdate,
    db: Session = Depends(get_db)
) -> MessageResponse:
    """Update a message."""
    
    try:
        msg_uuid = uuid.UUID(message_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid message ID format"
        )
    
    message = db.query(Message).filter(Message.id == msg_uuid).first()
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    
    # Update fields if provided
    update_dict = update_data.model_dump(exclude_unset=True)
    
    for field, value in update_dict.items():
        setattr(message, field, value)
    
    db.commit()
    db.refresh(message)
    
    return MessageResponse.from_message(message)


@router.delete("/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_message(
    message_id: str,
    db: Session = Depends(get_db)
):
    """Delete a message."""
    
    try:
        msg_uuid = uuid.UUID(message_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid message ID format"
        )
    
    message = db.query(Message).filter(Message.id == msg_uuid).first()
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    
    # Delete message
    db.delete(message)
    db.commit()
    
    return None