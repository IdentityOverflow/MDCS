"""
Configuration management for Project 2501 backend.
Loads environment variables from .env file and provides validated configuration.
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator, ConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database configuration
    db_host: str = Field(..., description="Database host")
    db_port: int = Field(5432, description="Database port")
    db_name: str = Field(..., description="Database name")
    db_user: str = Field(..., description="Database user")
    db_password: str = Field(..., description="Database password")
    
    # Optional database URL (if provided, overrides individual settings)
    database_url: Optional[str] = Field(None, description="Complete database URL")
    
    # Application settings
    app_name: str = Field("Project 2501 Backend", description="Application name")
    debug: bool = Field(False, description="Debug mode")
    
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_prefix=""
    )
    
    @field_validator('db_port')
    @classmethod
    def validate_port(cls, v):
        if not (1 <= v <= 65535):
            raise ValueError('Port must be between 1 and 65535')
        return v
    
    def get_database_url(self) -> str:
        """
        Get the database URL, either from DATABASE_URL env var or construct from components.
        """
        if self.database_url:
            return self.database_url
        
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
    
    def validate_database_config(self) -> bool:
        """
        Validate that all required database configuration is present.
        """
        if self.database_url:
            return bool(self.database_url.strip())
        
        required_fields = [self.db_host, self.db_name, self.db_user, self.db_password]
        return all(field and str(field).strip() for field in required_fields)


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get the global settings instance."""
    return settings