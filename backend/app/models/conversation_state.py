"""
ConversationState database model for storing module execution state.

Replaces the Module.extra_data approach with a dedicated table for better
scalability, querying, and data integrity.
"""

from sqlalchemy import Column, String, DateTime, UniqueConstraint, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from .base import Base


class ExecutionStage(str, enum.Enum):
    """Enumeration of execution stages that store conversation state."""
    STAGE4 = "stage4"  # POST_RESPONSE Non-AI modules
    STAGE5 = "stage5"  # POST_RESPONSE AI-powered modules


class ConversationState(Base):
    """
    Model for storing module execution state across conversations.
    
    This table stores the output variables from POST_RESPONSE modules
    so they can be used in the next conversation's template resolution.
    """
    __tablename__ = "conversation_states"
    
    # Override Base's automatic id with UUID
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Foreign keys and identifiers
    conversation_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    module_id = Column(UUID(as_uuid=True), ForeignKey("modules.id", ondelete="CASCADE"), nullable=False)
    execution_stage = Column(String(20), nullable=False)  # "stage4" or "stage5"
    
    # State data
    variables = Column(JSONB, nullable=False, default=dict)  # Module script output variables
    execution_metadata = Column(JSONB, nullable=True, default=dict)  # Execution success, timing, errors, etc.
    executed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    module = relationship("Module", backref="conversation_states")
    
    # Constraints
    __table_args__ = (
        # Only one state entry per conversation/module/stage combination
        UniqueConstraint('conversation_id', 'module_id', 'execution_stage', 
                        name='unique_conversation_module_stage'),
        
        # Ensure execution_stage is valid
        CheckConstraint("execution_stage IN ('stage4', 'stage5')", 
                       name='valid_execution_stage'),
    )
    
    def __repr__(self) -> str:
        return (f"<ConversationState("
                f"conversation_id={self.conversation_id}, "
                f"module_id={self.module_id}, "
                f"stage={self.execution_stage}, "
                f"variables={len(self.variables)} vars)>")
    
    @classmethod
    def get_for_conversation(cls, db_session, conversation_id: str):
        """
        Get all conversation states for a specific conversation.
        
        Args:
            db_session: Database session
            conversation_id: UUID string of the conversation
            
        Returns:
            Query object for ConversationState entries
        """
        return db_session.query(cls).filter(
            cls.conversation_id == conversation_id
        ).order_by(cls.executed_at.desc())
    
    @classmethod
    def get_latest_for_module(cls, db_session, conversation_id: str, module_id: str):
        """
        Get the latest state for a specific module in a conversation.
        
        Args:
            db_session: Database session
            conversation_id: UUID string of the conversation
            module_id: UUID string of the module
            
        Returns:
            ConversationState object or None
        """
        return db_session.query(cls).filter(
            cls.conversation_id == conversation_id,
            cls.module_id == module_id
        ).order_by(cls.executed_at.desc()).first()
    
    @classmethod
    def store_execution_result(
        cls, 
        db_session, 
        conversation_id: str, 
        module_id: str, 
        execution_stage: str,
        variables: dict, 
        execution_metadata: dict = None
    ):
        """
        Store or update execution result for a module.
        
        Args:
            db_session: Database session
            conversation_id: UUID string of the conversation
            module_id: UUID string of the module
            execution_stage: "stage4" or "stage5"
            variables: Dictionary of output variables from script
            execution_metadata: Optional metadata about execution
            
        Returns:
            ConversationState object
        """
        # Check if state already exists
        existing_state = db_session.query(cls).filter(
            cls.conversation_id == conversation_id,
            cls.module_id == module_id,
            cls.execution_stage == execution_stage
        ).first()
        
        if existing_state:
            # Update existing state
            existing_state.variables = variables
            existing_state.execution_metadata = execution_metadata or {}
            existing_state.executed_at = datetime.utcnow()
            db_session.flush()
            return existing_state
        else:
            # Create new state
            new_state = cls(
                conversation_id=conversation_id,
                module_id=module_id,
                execution_stage=execution_stage,
                variables=variables,
                execution_metadata=execution_metadata or {},
                executed_at=datetime.utcnow()
            )
            db_session.add(new_state)
            db_session.flush()
            return new_state
    
    def to_dict(self) -> dict:
        """
        Convert to dictionary for API responses.
        
        Returns:
            Dictionary representation of the conversation state
        """
        return {
            "id": str(self.id),
            "conversation_id": str(self.conversation_id),
            "module_id": str(self.module_id),
            "execution_stage": self.execution_stage,
            "variables": self.variables,
            "execution_metadata": self.execution_metadata,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "module_name": self.module.name if self.module else None
        }