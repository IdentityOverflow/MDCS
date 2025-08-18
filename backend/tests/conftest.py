"""
Test configuration and fixtures for Project 2501 backend tests.
"""

import os
import pytest
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import Base

# Load test environment variables from .env.test
test_env_path = Path(__file__).parent.parent / ".env.test"
if test_env_path.exists():
    load_dotenv(test_env_path)


@pytest.fixture(scope="session")
def test_database_url():
    """
    Get test database URL from environment or use default PostgreSQL test database.
    """
    # Check if TEST_DATABASE_URL is set for CI/custom environments
    test_db_url = os.getenv("TEST_DATABASE_URL")
    if test_db_url:
        return test_db_url
    
    # Test database configuration from .env.test
    # All values should be loaded from the .env.test file
    test_db_config = {
        "host": os.getenv("DB_HOST"),
        "port": os.getenv("DB_PORT"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "database": os.getenv("TEST_DB_NAME")
    }
    
    # Validate that all required configuration is present
    missing_vars = [key for key, value in test_db_config.items() if not value]
    if missing_vars:
        raise ValueError(
            f"Missing test database configuration: {missing_vars}. "
            f"Please ensure .env.test file exists with all required variables."
        )
    
    return f"postgresql://{test_db_config['user']}:{test_db_config['password']}@{test_db_config['host']}:{test_db_config['port']}/{test_db_config['database']}"


@pytest.fixture(scope="session")
def test_engine(test_database_url):
    """Create test database engine."""
    engine = create_engine(
        test_database_url,
        poolclass=StaticPool,
        echo=False  # Set to True for SQL debugging
    )
    return engine


@pytest.fixture(scope="session")
def setup_test_database(test_engine):
    """Setup test database schema."""
    # Create all tables
    Base.metadata.create_all(bind=test_engine)
    yield
    # Cleanup: drop all tables after tests
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session(test_engine, setup_test_database):
    """Create a database session for testing."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = SessionLocal()
    
    yield session
    
    # Cleanup: rollback any uncommitted changes and close session
    session.rollback()
    session.close()


@pytest.fixture
def clean_db(db_session):
    """
    Provide a clean database session that automatically cleans up after each test.
    This is useful for tests that need to start with a completely clean database.
    """
    # Clear all tables before the test
    for table in reversed(Base.metadata.sorted_tables):
        db_session.execute(table.delete())
    db_session.commit()
    
    yield db_session
    
    # Clear all tables after the test
    for table in reversed(Base.metadata.sorted_tables):
        db_session.execute(table.delete())
    db_session.commit()