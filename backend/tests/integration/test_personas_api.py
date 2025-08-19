"""
Tests for personas API endpoints.
Following TDD approach - tests written before implementation.
"""

import pytest
import uuid
from fastapi.testclient import TestClient

from app.main import app
from app.models import Persona


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
def sample_persona_data():
    """Sample data for a persona."""
    return {
        "name": "Test Data Analyst",
        "description": "AI persona specialized in data analysis and visualization",
        "template": "You are an expert data analyst. Use {data_validator} and {chart_generator} modules.",
        "mode": "reactive",
        "first_message": "Hello! I'm ready to help with data analysis."
    }


@pytest.fixture
def sample_autonomous_persona_data():
    """Sample data for an autonomous persona."""
    return {
        "name": "Test System Monitor",
        "description": "Autonomous system monitoring persona",
        "template": "You are a system administrator monitoring server performance.",
        "mode": "autonomous",
        "loop_frequency": "5.0",
        "first_message": "System monitoring active."
    }


@pytest.fixture
def sample_persona_uuid():
    """Sample UUID for testing."""
    return str(uuid.uuid4())


class TestPersonasCreateEndpoint:
    """Test the POST /api/personas endpoint."""
    
    def test_create_persona_success(self, client, sample_persona_data):
        """Test successful creation of a persona."""
        response = client.post("/api/personas", json=sample_persona_data)
        
        assert response.status_code == 201
        data = response.json()
        
        # Check returned data structure
        assert "id" in data
        assert data["name"] == sample_persona_data["name"]
        assert data["description"] == sample_persona_data["description"]
        assert data["template"] == sample_persona_data["template"]
        assert data["mode"] == "reactive"
        assert data["first_message"] == sample_persona_data["first_message"]
        assert data["is_active"] is True
        
        # Optional fields for reactive persona
        assert data["loop_frequency"] is None
        assert data["image_path"] is None
        
        # Check timestamps
        assert "created_at" in data
        assert "updated_at" in data
    
    def test_create_autonomous_persona_success(self, client, sample_autonomous_persona_data):
        """Test successful creation of an autonomous persona."""
        response = client.post("/api/personas", json=sample_autonomous_persona_data)
        
        assert response.status_code == 201
        data = response.json()
        
        # Check autonomous-specific fields
        assert data["name"] == sample_autonomous_persona_data["name"]
        assert data["mode"] == "autonomous"
        assert data["loop_frequency"] == sample_autonomous_persona_data["loop_frequency"]
    
    def test_create_persona_missing_required_fields(self, client):
        """Test creation fails with missing required fields."""
        incomplete_data = {
            "name": "Incomplete Persona"
            # Missing template
        }
        
        response = client.post("/api/personas", json=incomplete_data)
        assert response.status_code == 422  # Validation error
    
    def test_create_persona_invalid_mode(self, client, sample_persona_data):
        """Test creation fails with invalid mode."""
        invalid_data = sample_persona_data.copy()
        invalid_data["mode"] = "invalid_mode"
        
        response = client.post("/api/personas", json=invalid_data)
        assert response.status_code == 422
    
    def test_create_persona_name_too_long(self, client, sample_persona_data):
        """Test creation fails with name too long."""
        invalid_data = sample_persona_data.copy()
        invalid_data["name"] = "x" * 256  # Exceeds 255 char limit
        
        response = client.post("/api/personas", json=invalid_data)
        assert response.status_code == 422
    
    def test_create_persona_empty_name(self, client, sample_persona_data):
        """Test creation fails with empty name."""
        invalid_data = sample_persona_data.copy()
        invalid_data["name"] = ""
        
        response = client.post("/api/personas", json=invalid_data)
        assert response.status_code == 422


class TestPersonasListEndpoint:
    """Test the GET /api/personas endpoint."""
    
    def test_get_personas_empty_list(self, client, clean_db):
        """Test getting personas when none exist."""
        response = client.get("/api/personas")
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) == 0
    
    def test_get_personas_with_data(self, client, clean_db, sample_persona_data, sample_autonomous_persona_data):
        """Test getting personas when some exist."""
        # First create some personas
        client.post("/api/personas", json=sample_persona_data)
        client.post("/api/personas", json=sample_autonomous_persona_data)
        
        response = client.get("/api/personas")
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) == 2
        
        # Check that both personas are returned
        persona_names = [persona["name"] for persona in data]
        assert sample_persona_data["name"] in persona_names
        assert sample_autonomous_persona_data["name"] in persona_names
    
    def test_get_personas_filter_by_mode(self, client, clean_db):
        """Test filtering personas by mode."""
        response = client.get("/api/personas?mode=reactive")
        
        assert response.status_code == 200
        data = response.json()
        
        # All returned personas should be reactive mode
        for persona in data:
            assert persona["mode"] == "reactive"
    
    def test_get_personas_active_only(self, client, clean_db):
        """Test filtering to only active personas."""
        response = client.get("/api/personas?active_only=true")
        
        assert response.status_code == 200
        data = response.json()
        
        # All returned personas should be active
        for persona in data:
            assert persona["is_active"] is True


class TestPersonasGetByIdEndpoint:
    """Test the GET /api/personas/{id} endpoint."""
    
    def test_get_persona_by_id_success(self, client, sample_persona_data):
        """Test successfully getting a persona by ID."""
        # First create a persona
        create_response = client.post("/api/personas", json=sample_persona_data)
        created_persona = create_response.json()
        persona_id = created_persona["id"]
        
        # Then get it by ID
        response = client.get(f"/api/personas/{persona_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == persona_id
        assert data["name"] == sample_persona_data["name"]
        assert data["template"] == sample_persona_data["template"]
    
    def test_get_persona_by_id_not_found(self, client, sample_persona_uuid):
        """Test getting a non-existent persona."""
        response = client.get(f"/api/personas/{sample_persona_uuid}")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    def test_get_persona_by_invalid_uuid(self, client):
        """Test getting a persona with invalid UUID format."""
        response = client.get("/api/personas/invalid-uuid")
        
        assert response.status_code == 422


class TestPersonasUpdateEndpoint:
    """Test the PUT /api/personas/{id} endpoint."""
    
    def test_update_persona_success(self, client, sample_persona_data):
        """Test successfully updating a persona."""
        # First create a persona
        create_response = client.post("/api/personas", json=sample_persona_data)
        created_persona = create_response.json()
        persona_id = created_persona["id"]
        
        # Update the persona
        updated_data = sample_persona_data.copy()
        updated_data["name"] = "Updated Data Analyst"
        updated_data["description"] = "Updated description for testing"
        
        response = client.put(f"/api/personas/{persona_id}", json=updated_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == persona_id
        assert data["name"] == "Updated Data Analyst"
        assert data["description"] == "Updated description for testing"
    
    def test_update_persona_not_found(self, client, sample_persona_uuid, sample_persona_data):
        """Test updating a non-existent persona."""
        response = client.put(f"/api/personas/{sample_persona_uuid}", json=sample_persona_data)
        
        assert response.status_code == 404
    
    def test_update_persona_mode_change(self, client, sample_persona_data):
        """Test changing persona mode from reactive to autonomous."""
        # Create a reactive persona
        create_response = client.post("/api/personas", json=sample_persona_data)
        persona_id = create_response.json()["id"]
        
        # Update to autonomous mode
        update_data = {
            "mode": "autonomous",
            "loop_frequency": "2.5"
        }
        
        response = client.put(f"/api/personas/{persona_id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["mode"] == "autonomous"
        assert data["loop_frequency"] == "2.5"
    
    def test_update_persona_partial_update(self, client, sample_persona_data):
        """Test partial update of persona fields."""
        # Create a persona
        create_response = client.post("/api/personas", json=sample_persona_data)
        persona_id = create_response.json()["id"]
        
        # Update only name and description
        update_data = {
            "name": "Partially Updated Persona",
            "description": "Only name and description changed"
        }
        
        response = client.put(f"/api/personas/{persona_id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["name"] == "Partially Updated Persona"
        assert data["description"] == "Only name and description changed"
        # Other fields should remain unchanged
        assert data["template"] == sample_persona_data["template"]


class TestPersonasDeleteEndpoint:
    """Test the DELETE /api/personas/{id} endpoint."""
    
    def test_delete_persona_success(self, client, sample_persona_data):
        """Test successfully deleting a persona."""
        # First create a persona
        create_response = client.post("/api/personas", json=sample_persona_data)
        persona_id = create_response.json()["id"]
        
        # Delete the persona
        response = client.delete(f"/api/personas/{persona_id}")
        
        assert response.status_code == 204  # No content
        
        # Verify persona is deleted
        get_response = client.get(f"/api/personas/{persona_id}")
        assert get_response.status_code == 404
    
    def test_delete_persona_not_found(self, client, sample_persona_uuid):
        """Test deleting a non-existent persona."""
        response = client.delete(f"/api/personas/{sample_persona_uuid}")
        
        assert response.status_code == 404
    
    def test_delete_persona_invalid_uuid(self, client):
        """Test deleting with invalid UUID format."""
        response = client.delete("/api/personas/invalid-uuid")
        
        assert response.status_code == 422


class TestPersonasValidation:
    """Test validation rules for personas."""
    
    def test_persona_without_optional_fields(self, client):
        """Test that persona can be created with minimal fields."""
        minimal_data = {
            "name": "Minimal Persona",
            "template": "You are a helpful assistant.",
            "mode": "reactive"
        }
        response = client.post("/api/personas", json=minimal_data)
        assert response.status_code == 201
        
        data = response.json()
        assert data["name"] == "Minimal Persona"
        assert data["description"] is None
        assert data["first_message"] is None
    
    def test_persona_template_validation(self, client, sample_persona_data):
        """Test template field validation."""
        # Empty template should fail
        invalid_data = sample_persona_data.copy()
        invalid_data["template"] = ""
        
        response = client.post("/api/personas", json=invalid_data)
        assert response.status_code == 422
    
    def test_persona_loop_frequency_validation(self, client, sample_persona_data):
        """Test loop_frequency validation for autonomous personas."""
        # Invalid loop_frequency format
        invalid_data = sample_persona_data.copy()
        invalid_data["mode"] = "autonomous"
        invalid_data["loop_frequency"] = "invalid"
        
        response = client.post("/api/personas", json=invalid_data)
        assert response.status_code == 422
    
    def test_persona_reactive_without_loop_frequency(self, client, sample_persona_data):
        """Test that reactive persona can be created without loop_frequency."""
        # This should succeed
        response = client.post("/api/personas", json=sample_persona_data)
        assert response.status_code == 201
        
        created_persona = response.json()
        assert created_persona["mode"] == "reactive"
        assert created_persona["loop_frequency"] is None