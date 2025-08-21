"""
Conversation and message database models.
"""

from datetime import datetime
from typing import List

from sqlalchemy import Column, Integer, String, Text, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum

from .base import Base


class MessageRole(str, enum.Enum):
    """Enumeration of message roles."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Conversation(Base):
    """
    Conversation model representing a chat session.
    """
    __tablename__ = "conversations"
    
    # Use UUID for conversation IDs for better privacy/security
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    title = Column(String(255), nullable=False, index=True)
    
    # Association with persona (one conversation per persona)
    persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True, index=True)
    
    # Provider information (which AI provider was used)
    provider_type = Column(String(50), nullable=True)  # "openai", "ollama", etc.
    provider_config = Column(JSON, nullable=True)  # Snapshot of provider config used
    
    # Relationship to messages
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at")
    
    # Relationship to persona
    persona = relationship("Persona", back_populates="conversations")
    
    def __repr__(self) -> str:
        return f"<Conversation(id={self.id}, title='{self.title}', persona_id={self.persona_id})>"


class Message(Base):
    """
    Message model representing individual messages in a conversation.
    """
    __tablename__ = "messages"
    
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(SQLEnum(MessageRole), nullable=False)
    content = Column(Text, nullable=False)
    
    # Thinking content (for AI reasoning models)
    thinking = Column(Text, nullable=True)
    
    # Optional metadata (renamed to avoid SQLAlchemy reserved keyword)
    extra_data = Column(JSON, nullable=True)  # For storing additional message data
    
    # Token usage information (if available)
    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    
    # Relationship back to conversation
    conversation = relationship("Conversation", back_populates="messages")
    
    def __repr__(self) -> str:
        content_preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"<Message(id={self.id}, role={self.role}, content='{content_preview}')>"