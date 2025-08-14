"""
Base database model with common fields and functionality.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import Column, Integer, DateTime, String
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.sql import func


class BaseModel:
    """Base model class with common fields."""
    
    @declared_attr
    def __tablename__(cls) -> str:
        """Generate table name from class name."""
        return cls.__name__.lower() + 's'
    
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert model instance to dictionary."""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
    
    def __repr__(self) -> str:
        """String representation of model."""
        return f"<{self.__class__.__name__}(id={self.id})>"


# Create the base class for all models
Base = declarative_base(cls=BaseModel)