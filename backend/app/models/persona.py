"""
Persona database model for storing AI personas.
"""

from sqlalchemy import Column, String, Text, JSON, Boolean
from sqlalchemy.dialects.postgresql import UUID
import uuid

from .base import Base


class Persona(Base):
    """
    Persona model representing an AI persona configuration.
    """
    __tablename__ = "personas"
    
    # Use UUID for persona IDs
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Basic persona information
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # AI model configuration
    model = Column(String(100), nullable=False)  # e.g., "gpt-4", "llama3:8b"
    
    # Template and configuration
    template = Column(Text, nullable=False)  # The persona template with module placeholders
    
    # Operating mode
    mode = Column(String(20), nullable=False, default="reactive")  # "reactive" or "autonomous"
    loop_frequency = Column(String(10), nullable=True)  # For autonomous mode, e.g., "5.0"
    
    # Optional first message
    first_message = Column(Text, nullable=True)
    
    # Image/avatar information
    image_path = Column(String(500), nullable=True)  # Path to persona image
    
    # Additional metadata and configuration (renamed to avoid SQLAlchemy reserved keyword)
    extra_data = Column(JSON, nullable=True)  # For storing additional persona data
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    def __repr__(self) -> str:
        return f"<Persona(id={self.id}, name='{self.name}', model='{self.model}')>"