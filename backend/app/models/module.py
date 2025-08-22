"""
Module database model for storing cognitive system modules.
"""

from sqlalchemy import Column, String, Text, JSON, Boolean, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum

from .base import Base


class ModuleType(str, enum.Enum):
    """Enumeration of module types."""
    SIMPLE = "simple"
    ADVANCED = "advanced"


class ExecutionTiming(str, enum.Enum):
    """Enumeration of module execution timing options."""
    BEFORE = "before"
    AFTER = "after"
    CUSTOM = "custom"


class Module(Base):
    """
    Module model representing a cognitive system module.
    """
    __tablename__ = "modules"
    
    # Use UUID for module IDs
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Basic module information
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Module content
    content = Column(Text, nullable=True)  # Static text for simple modules, Python code for advanced
    
    # Module type and behavior
    type = Column(SQLEnum(ModuleType), nullable=False, default=ModuleType.SIMPLE)
    
    # Advanced module configuration (only for advanced modules)
    trigger_pattern = Column(String(500), nullable=True)  # Regex or keyword pattern for activation
    script = Column(Text, nullable=True)  # Python script content for advanced modules
    timing = Column(SQLEnum(ExecutionTiming), nullable=True, default=ExecutionTiming.CUSTOM)  # Default: "custom" (on demand)
    
    # Additional metadata and configuration (renamed to avoid SQLAlchemy reserved keyword)
    extra_data = Column(JSON, nullable=True)  # For storing additional module data
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    def __repr__(self) -> str:
        return f"<Module(id={self.id}, name='{self.name}', type='{self.type}')>"