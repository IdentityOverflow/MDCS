"""
Tests for configuration management.
"""

import os
import pytest
from unittest.mock import patch
from pydantic_core import ValidationError
from app.core.config import Settings, get_settings


class TestSettings:
    """Test the Settings configuration class."""
    
    def test_settings_with_all_env_vars(self):
        """Test settings creation with all environment variables."""
        env_vars = {
            'DB_HOST': 'localhost',
            'DB_PORT': '5432',
            'DB_NAME': 'testdb',
            'DB_USER': 'testuser',
            'DB_PASSWORD': 'testpass'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings()
            
            assert settings.db_host == 'localhost'
            assert settings.db_port == 5432
            assert settings.db_name == 'testdb'
            assert settings.db_user == 'testuser'
            assert settings.db_password == 'testpass'
    
    def test_settings_with_database_url(self):
        """Test settings with DATABASE_URL override."""
        env_vars = {
            'DATABASE_URL': 'postgresql://user:pass@host:5432/dbname',
            'DB_HOST': 'should_be_ignored',  # These should be ignored when DATABASE_URL is present
            'DB_NAME': 'should_be_ignored',
            'DB_USER': 'should_be_ignored',
            'DB_PASSWORD': 'should_be_ignored'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings()
            
            assert settings.database_url == 'postgresql://user:pass@host:5432/dbname'
            assert settings.get_database_url() == 'postgresql://user:pass@host:5432/dbname'
    
    
    def test_invalid_port(self):
        """Test that invalid port numbers raise ValidationError."""
        env_vars = {
            'DB_HOST': 'localhost',
            'DB_PORT': '99999',  # Invalid port
            'DB_NAME': 'testdb',
            'DB_USER': 'testuser',
            'DB_PASSWORD': 'testpass'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(ValidationError):
                Settings()
    
    def test_get_database_url_from_components(self):
        """Test database URL construction from components."""
        env_vars = {
            'DB_HOST': 'myhost',
            'DB_PORT': '5433',
            'DB_NAME': 'mydb',
            'DB_USER': 'myuser',
            'DB_PASSWORD': 'mypass'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings()
            expected_url = 'postgresql://myuser:mypass@myhost:5433/mydb'
            
            assert settings.get_database_url() == expected_url
    
    def test_validate_database_config_with_components(self):
        """Test database configuration validation with individual components."""
        env_vars = {
            'DB_HOST': 'localhost',
            'DB_PORT': '5432',
            'DB_NAME': 'testdb',
            'DB_USER': 'testuser',
            'DB_PASSWORD': 'testpass'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings()
            assert settings.validate_database_config() is True
    
    def test_validate_database_config_with_url(self):
        """Test database configuration validation with DATABASE_URL."""
        env_vars = {
            'DATABASE_URL': 'postgresql://user:pass@host:5432/dbname',
            'DB_HOST': 'localhost',  # These will be ignored but need to be present for validation
            'DB_NAME': 'testdb',
            'DB_USER': 'testuser', 
            'DB_PASSWORD': 'testpass'
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings()
            assert settings.validate_database_config() is True
    
    def test_default_values(self):
        """Test that default values are set correctly."""
        env_vars = {
            'DB_HOST': 'localhost',
            'DB_NAME': 'testdb',
            'DB_USER': 'testuser',
            'DB_PASSWORD': 'testpass'
            # DB_PORT should default to 5432
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings()
            
            assert settings.db_port == 5432
            assert settings.app_name == "Project 2501 Backend"
            assert settings.debug is False


class TestGetSettings:
    """Test the get_settings function."""
    
    def test_get_settings_returns_settings_instance(self):
        """Test that get_settings returns a Settings instance."""
        settings = get_settings()
        assert isinstance(settings, Settings)