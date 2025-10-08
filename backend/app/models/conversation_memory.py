"""
ConversationMemory database model for storing compressed long-term memories.

Stores AI-compressed conversation segments in a fixed buffer window (messages 25-35)
to provide long-term contextual memory for AI personas.
"""

from typing import List
from sqlalchemy import Column, String, DateTime, Integer, Text, UniqueConstraint, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from .base import Base


class ConversationMemory(Base):
    """
    Model for storing compressed long-term conversation memories.
    
    This table stores AI-compressed summaries of conversation segments
    from a fixed buffer window (messages 25-35) to provide long-term
    contextual memory that complements short-term recent message memory.
    """
    __tablename__ = "conversation_memories"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Foreign keys and identifiers
    conversation_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    memory_sequence = Column(Integer, nullable=False)  # Sequential numbering: 1, 2, 3...
    
    # Memory content and metadata
    compressed_content = Column(Text, nullable=False)  # AI-generated memory summary
    original_message_range = Column(String(20), nullable=False)  # "25-35"
    message_count_at_compression = Column(Integer, nullable=False)  # Total messages when compressed
    first_message_id = Column(String(100), nullable=True)  # ID of first message in compressed range
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Constraints
    __table_args__ = (
        # Only one memory per conversation per sequence number
        UniqueConstraint('conversation_id', 'memory_sequence', 
                        name='unique_conversation_memory_sequence'),
    )
    
    def __repr__(self) -> str:
        return (f"<ConversationMemory("
                f"conversation_id={self.conversation_id}, "
                f"sequence={self.memory_sequence}, "
                f"range={self.original_message_range}, "
                f"content_length={len(self.compressed_content)})>")
    
    @classmethod
    def get_for_conversation(cls, db_session, conversation_id: str):
        """
        Get all memories for a specific conversation, ordered by sequence.
        
        Args:
            db_session: Database session
            conversation_id: UUID string of the conversation
            
        Returns:
            Query object for ConversationMemory entries
        """
        return db_session.query(cls).filter(
            cls.conversation_id == conversation_id
        ).order_by(cls.memory_sequence.asc())
    
    @classmethod
    def get_recent_memories(cls, db_session, conversation_id: str, limit: int = 10):
        """
        Get the most recent memories for a conversation.
        
        Args:
            db_session: Database session
            conversation_id: UUID string of the conversation
            limit: Maximum number of memories to retrieve
            
        Returns:
            List of ConversationMemory objects (most recent first)
        """
        return db_session.query(cls).filter(
            cls.conversation_id == conversation_id
        ).order_by(cls.memory_sequence.desc()).limit(limit).all()
    
    @classmethod
    def get_next_sequence_number(cls, db_session, conversation_id: str) -> int:
        """
        Get the next sequence number for a conversation.
        
        Args:
            db_session: Database session
            conversation_id: UUID string of the conversation
            
        Returns:
            Next sequence number (starts at 1)
        """
        max_sequence = db_session.query(cls.memory_sequence).filter(
            cls.conversation_id == conversation_id
        ).order_by(cls.memory_sequence.desc()).first()
        
        return (max_sequence[0] + 1) if max_sequence else 1
    
    @classmethod
    def should_compress_now(cls, db_session, conversation_id: str, total_message_count: int, min_messages_required: int = 36) -> bool:
        """
        Check if buffer should be compressed based on message count and compression history.
        
        Args:
            db_session: Database session
            conversation_id: UUID string of the conversation
            total_message_count: Current total message count in conversation
            min_messages_required: Minimum messages needed to trigger compression (configurable)
            
        Returns:
            True if buffer should be compressed, False otherwise
        """
        # Need at least the specified minimum messages
        if total_message_count < min_messages_required:
            return False
        
        # No existing memories - compress if we have enough messages  
        return True
    
    @classmethod
    def has_compressed_message_range(cls, db_session, conversation_id: str, buffer_message_ids: List[str]) -> bool:
        """
        Check if any of the current buffer messages have already been compressed.
        
        Args:
            db_session: Database session
            conversation_id: UUID string of the conversation
            buffer_message_ids: List of message IDs in the current buffer
            
        Returns:
            True if any of these messages have been compressed before, False otherwise
        """
        if not buffer_message_ids:
            return False
        
        # Check if any existing memory contains messages from our current buffer
        existing_memories = db_session.query(cls).filter(
            cls.conversation_id == conversation_id,
            cls.first_message_id.in_(buffer_message_ids)
        ).all()
        
        return len(existing_memories) > 0
    
    @classmethod
    def store_compressed_memory(
        cls,
        db_session,
        conversation_id: str,
        compressed_content: str,
        message_range: str,
        total_messages: int,
        first_message_id: str = None
    ):
        """
        Store a new compressed memory.
        
        Args:
            db_session: Database session
            conversation_id: UUID string of the conversation
            compressed_content: AI-generated memory summary
            message_range: Range of messages compressed (e.g., "25-35")
            total_messages: Total message count when compression occurred
            first_message_id: ID of first message in compressed range (for overlap detection)
            
        Returns:
            ConversationMemory object
        """
        sequence_number = cls.get_next_sequence_number(db_session, conversation_id)
        
        new_memory = cls(
            conversation_id=conversation_id,
            memory_sequence=sequence_number,
            compressed_content=compressed_content,
            original_message_range=message_range,
            message_count_at_compression=total_messages,
            first_message_id=first_message_id,
            created_at=datetime.utcnow()
        )
        
        db_session.add(new_memory)
        db_session.flush()
        return new_memory
    
    @classmethod
    def clear_all_memories(cls, db_session, conversation_id: str) -> int:
        """
        Delete all memories for a conversation.
        
        Args:
            db_session: Database session
            conversation_id: UUID string of the conversation
            
        Returns:
            Number of memories deleted
        """
        deleted_count = db_session.query(cls).filter(
            cls.conversation_id == conversation_id
        ).delete()
        
        db_session.flush()
        return deleted_count
    
    def to_dict(self) -> dict:
        """
        Convert to dictionary for API responses and plugin usage.
        
        Returns:
            Dictionary representation of the conversation memory
        """
        return {
            "id": str(self.id),
            "conversation_id": str(self.conversation_id),
            "memory_sequence": self.memory_sequence,
            "compressed_content": self.compressed_content,
            "original_message_range": self.original_message_range,
            "message_count_at_compression": self.message_count_at_compression,
            "first_message_id": self.first_message_id,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }