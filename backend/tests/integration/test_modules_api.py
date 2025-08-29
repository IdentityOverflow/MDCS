"""
Tests for modules API endpoints.
Following TDD approach - tests written before implementation.
"""

import pytest
import uuid
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app.models import Module, ModuleType, ExecutionContext


@pytest.fixture
def client(test_engine, setup_test_database):
    """Create a test client for the FastAPI app with test database."""
    from app.database.connection import get_db
    from sqlalchemy.orm import sessionmaker
    
    # Create test session factory
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    
    def override_get_db():
        """Override database dependency to use test database."""
        try:
            db = TestSessionLocal()
            yield db
        finally:
            db.close()
    
    # Override the database dependency
    app.dependency_overrides[get_db] = override_get_db
    
    yield TestClient(app)
    
    # Clean up dependency overrides after tests
    app.dependency_overrides.clear()


@pytest.fixture
def sample_simple_module_data():
    """Sample data for a simple module."""
    return {
        "name": "Test Logger",
        "description": "Simple logging utility for testing",
        "content": "console.log('test message')",
        "type": "simple"
    }


@pytest.fixture
def sample_advanced_module_data():
    """Sample data for an advanced module."""
    return {
        "name": "Test Validator",
        "description": "Advanced validation module for testing",
        "content": "Validation logic here...",
        "type": "advanced",
        "trigger_pattern": "/test/*",
        "script": "print('validation script')",
        "execution_context": "IMMEDIATE"
    }


@pytest.fixture
def sample_module_uuid():
    """Sample UUID for testing."""
    return str(uuid.uuid4())


class TestModulesCreateEndpoint:
    """Test the POST /api/modules endpoint."""
    
    def test_create_simple_module_success(self, client, sample_simple_module_data):
        """Test successful creation of a simple module."""
        response = client.post("/api/modules", json=sample_simple_module_data)
        
        assert response.status_code == 201
        data = response.json()
        
        # Check returned data structure
        assert "id" in data
        assert data["name"] == sample_simple_module_data["name"]
        assert data["description"] == sample_simple_module_data["description"]
        assert data["content"] == sample_simple_module_data["content"]
        assert data["type"] == "simple"
        assert data["is_active"] is True
        
        # Optional fields for simple modules
        assert data["trigger_pattern"] is None
        assert data["script"] is None
        assert data["execution_context"] == "ON_DEMAND"  # Default execution context is ON_DEMAND
        assert data["requires_ai_inference"] is False  # Default is False
        
        # Check timestamps
        assert "created_at" in data
        assert "updated_at" in data
    
    def test_create_advanced_module_success(self, client, sample_advanced_module_data):
        """Test successful creation of an advanced module."""
        response = client.post("/api/modules", json=sample_advanced_module_data)
        
        assert response.status_code == 201
        data = response.json()
        
        # Check all advanced fields are present
        assert data["name"] == sample_advanced_module_data["name"]
        assert data["type"] == "advanced"
        assert data["trigger_pattern"] == sample_advanced_module_data["trigger_pattern"]
        assert data["script"] == sample_advanced_module_data["script"]
        assert data["execution_context"] == "IMMEDIATE"
        assert data["requires_ai_inference"] is False  # Should be False for simple script
    
    def test_create_module_missing_required_fields(self, client):
        """Test creation fails with missing required fields."""
        incomplete_data = {
            "name": "Incomplete Module"
            # Missing description, content, type
        }
        
        response = client.post("/api/modules", json=incomplete_data)
        assert response.status_code == 422  # Validation error
    
    def test_create_module_invalid_type(self, client, sample_simple_module_data):
        """Test creation fails with invalid module type."""
        invalid_data = sample_simple_module_data.copy()
        invalid_data["type"] = "invalid_type"
        
        response = client.post("/api/modules", json=invalid_data)
        assert response.status_code == 422
    
    def test_create_module_invalid_execution_context(self, client, sample_advanced_module_data):
        """Test creation fails with invalid execution context value."""
        invalid_data = sample_advanced_module_data.copy()
        invalid_data["execution_context"] = "INVALID_CONTEXT"
        
        response = client.post("/api/modules", json=invalid_data)
        assert response.status_code == 422


class TestModulesListEndpoint:
    """Test the GET /api/modules endpoint."""
    
    def test_get_modules_empty_list(self, client, clean_db):
        """Test getting modules when none exist."""
        response = client.get("/api/modules")
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) == 0
    
    def test_get_modules_with_data(self, client, clean_db, sample_simple_module_data, sample_advanced_module_data):
        """Test getting modules when some exist."""
        # First create some modules
        client.post("/api/modules", json=sample_simple_module_data)
        client.post("/api/modules", json=sample_advanced_module_data)
        
        response = client.get("/api/modules")
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) == 2
        
        # Check that both modules are returned
        module_names = [module["name"] for module in data]
        assert sample_simple_module_data["name"] in module_names
        assert sample_advanced_module_data["name"] in module_names
    
    def test_get_modules_filter_by_type(self, client, clean_db):
        """Test filtering modules by type."""
        response = client.get("/api/modules?type=simple")
        
        assert response.status_code == 200
        data = response.json()
        
        # All returned modules should be simple type
        for module in data:
            assert module["type"] == "simple"


class TestModulesGetByIdEndpoint:
    """Test the GET /api/modules/{id} endpoint."""
    
    def test_get_module_by_id_success(self, client, sample_simple_module_data):
        """Test successfully getting a module by ID."""
        # First create a module
        create_response = client.post("/api/modules", json=sample_simple_module_data)
        created_module = create_response.json()
        module_id = created_module["id"]
        
        # Then get it by ID
        response = client.get(f"/api/modules/{module_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == module_id
        assert data["name"] == sample_simple_module_data["name"]
    
    def test_get_module_by_id_not_found(self, client, sample_module_uuid):
        """Test getting a non-existent module."""
        response = client.get(f"/api/modules/{sample_module_uuid}")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    def test_get_module_by_invalid_uuid(self, client):
        """Test getting a module with invalid UUID format."""
        response = client.get("/api/modules/invalid-uuid")
        
        assert response.status_code == 422


class TestModulesUpdateEndpoint:
    """Test the PUT /api/modules/{id} endpoint."""
    
    def test_update_module_success(self, client, sample_simple_module_data):
        """Test successfully updating a module."""
        # First create a module
        create_response = client.post("/api/modules", json=sample_simple_module_data)
        created_module = create_response.json()
        module_id = created_module["id"]
        
        # Update the module
        updated_data = sample_simple_module_data.copy()
        updated_data["name"] = "Updated Test Logger"
        updated_data["description"] = "Updated description"
        
        response = client.put(f"/api/modules/{module_id}", json=updated_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == module_id
        assert data["name"] == "Updated Test Logger"
        assert data["description"] == "Updated description"
    
    def test_update_module_not_found(self, client, sample_module_uuid, sample_simple_module_data):
        """Test updating a non-existent module."""
        response = client.put(f"/api/modules/{sample_module_uuid}", json=sample_simple_module_data)
        
        assert response.status_code == 404
    
    def test_update_module_type_change(self, client, sample_simple_module_data, sample_advanced_module_data):
        """Test changing module type from simple to advanced."""
        # Create a simple module
        create_response = client.post("/api/modules", json=sample_simple_module_data)
        module_id = create_response.json()["id"]
        
        # Update to advanced type
        response = client.put(f"/api/modules/{module_id}", json=sample_advanced_module_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["type"] == "advanced"
        assert data["trigger_pattern"] == sample_advanced_module_data["trigger_pattern"]
        assert data["script"] == sample_advanced_module_data["script"]
        assert data["execution_context"] == "IMMEDIATE"


class TestModulesDeleteEndpoint:
    """Test the DELETE /api/modules/{id} endpoint."""
    
    def test_delete_module_success(self, client, sample_simple_module_data):
        """Test successfully deleting a module."""
        # First create a module
        create_response = client.post("/api/modules", json=sample_simple_module_data)
        module_id = create_response.json()["id"]
        
        # Delete the module
        response = client.delete(f"/api/modules/{module_id}")
        
        assert response.status_code == 204  # No content
        
        # Verify module is deleted
        get_response = client.get(f"/api/modules/{module_id}")
        assert get_response.status_code == 404
    
    def test_delete_module_not_found(self, client, sample_module_uuid):
        """Test deleting a non-existent module."""
        response = client.delete(f"/api/modules/{sample_module_uuid}")
        
        assert response.status_code == 404
    
    def test_delete_module_invalid_uuid(self, client):
        """Test deleting with invalid UUID format."""
        response = client.delete("/api/modules/invalid-uuid")
        
        assert response.status_code == 422


class TestModulesValidation:
    """Test validation rules for modules."""
    
    def test_module_name_length_validation(self, client):
        """Test module name length constraints."""
        # Name too long (> 255 chars)
        long_name = "x" * 256
        data = {
            "name": long_name,
            "description": "Test",
            "content": "Test content",
            "type": "simple"
        }
        
        response = client.post("/api/modules", json=data)
        assert response.status_code == 422
    
    def test_module_empty_name_validation(self, client):
        """Test that empty module name is rejected."""
        data = {
            "name": "",
            "description": "Test",
            "content": "Test content",
            "type": "simple"
        }
        
        response = client.post("/api/modules", json=data)
        assert response.status_code == 422
    
    def test_advanced_module_without_optional_fields(self, client):
        """Test that advanced module can be created without all optional fields."""
        data = {
            "name": "Advanced Module",
            "description": "Test advanced module",
            "content": "Advanced content",
            "type": "advanced"
            # No trigger_pattern, script, or execution_context
        }
        
        response = client.post("/api/modules", json=data)
        assert response.status_code == 201
        
        created_module = response.json()
        assert created_module["trigger_pattern"] is None
        assert created_module["script"] is None
        assert created_module["execution_context"] == "ON_DEMAND"  # Default execution context is ON_DEMAND