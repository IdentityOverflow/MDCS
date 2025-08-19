"""
Integration tests for personas API with real PostgreSQL database.
These tests verify that the API works end-to-end with actual database operations.
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


class TestPersonasIntegration:
    """Integration tests for personas CRUD operations with real database."""
    
    def test_full_persona_lifecycle_reactive(self, client, clean_db):
        """Test complete lifecycle of a reactive persona."""
        # Create persona
        persona_data = {
            "name": "Integration Test Analyst",
            "description": "Reactive persona for integration testing",
            "template": "You are a data analyst specialized in {data_analysis} tasks.",
            "mode": "reactive",
            "first_message": "Hello! Ready to analyze data."
        }
        
        create_response = client.post("/api/personas", json=persona_data)
        assert create_response.status_code == 201
        
        created_persona = create_response.json()
        persona_id = created_persona["id"]
        
        # Verify UUID format
        uuid.UUID(persona_id)  # This will raise ValueError if invalid
        
        # Read persona
        get_response = client.get(f"/api/personas/{persona_id}")
        assert get_response.status_code == 200
        
        retrieved_persona = get_response.json()
        assert retrieved_persona["id"] == persona_id
        assert retrieved_persona["name"] == persona_data["name"]
        assert retrieved_persona["mode"] == "reactive"
        assert retrieved_persona["is_active"] is True
        assert retrieved_persona["loop_frequency"] is None
        
        # Update persona
        updated_data = persona_data.copy()
        updated_data["name"] = "Updated Integration Analyst"
        updated_data["description"] = "Updated description for integration test"
        
        update_response = client.put(f"/api/personas/{persona_id}", json=updated_data)
        assert update_response.status_code == 200
        
        updated_persona = update_response.json()
        assert updated_persona["name"] == "Updated Integration Analyst"
        assert updated_persona["description"] == "Updated description for integration test"
        
        # Verify update persisted
        get_updated_response = client.get(f"/api/personas/{persona_id}")
        assert get_updated_response.json()["name"] == "Updated Integration Analyst"
        
        # Delete persona
        delete_response = client.delete(f"/api/personas/{persona_id}")
        assert delete_response.status_code == 204
        
        # Verify deletion
        get_deleted_response = client.get(f"/api/personas/{persona_id}")
        assert get_deleted_response.status_code == 404
    
    def test_full_persona_lifecycle_autonomous(self, client, clean_db):
        """Test complete lifecycle of an autonomous persona."""
        # Create autonomous persona
        persona_data = {
            "name": "Integration Test Monitor",
            "description": "Autonomous monitoring persona for integration testing",
            "template": "You are a system monitor with {monitoring_module} capabilities.",
            "mode": "autonomous",
            "loop_frequency": "3.5",
            "first_message": "System monitoring initialized."
        }
        
        create_response = client.post("/api/personas", json=persona_data)
        assert create_response.status_code == 201
        
        created_persona = create_response.json()
        persona_id = created_persona["id"]
        
        # Verify all autonomous fields
        assert created_persona["mode"] == "autonomous"
        assert created_persona["loop_frequency"] == "3.5"
        assert created_persona["first_message"] == "System monitoring initialized."
        
        # Test updating mode from autonomous to reactive
        updated_data = {
            "mode": "reactive",
            "loop_frequency": None  # Clear loop frequency for reactive mode
        }
        
        update_response = client.put(f"/api/personas/{persona_id}", json=updated_data)
        assert update_response.status_code == 200
        
        updated_persona = update_response.json()
        assert updated_persona["mode"] == "reactive"
        assert updated_persona["loop_frequency"] is None
        
        # Clean up
        client.delete(f"/api/personas/{persona_id}")
    
    def test_persona_list_pagination(self, client, clean_db):
        """Test persona listing with multiple personas."""
        # Create multiple personas
        personas_created = []
        
        for i in range(5):
            persona_data = {
                "name": f"Integration Persona {i}",
                "description": f"Description for persona {i}",
                "template": f"Template for persona {i}",
                "mode": "reactive" if i % 2 == 0 else "autonomous"
            }
            
            if persona_data["mode"] == "autonomous":
                persona_data["loop_frequency"] = f"{i + 1}.0"
            
            response = client.post("/api/personas", json=persona_data)
            assert response.status_code == 201
            personas_created.append(response.json()["id"])
        
        # Test listing all personas
        list_response = client.get("/api/personas")
        assert list_response.status_code == 200
        
        personas = list_response.json()
        assert len(personas) == 5
        
        # Test filtering by mode
        reactive_response = client.get("/api/personas?mode=reactive")
        assert reactive_response.status_code == 200
        reactive_personas = reactive_response.json()
        assert len(reactive_personas) == 3  # Personas 0, 2, 4
        
        for persona in reactive_personas:
            assert persona["mode"] == "reactive"
        
        autonomous_response = client.get("/api/personas?mode=autonomous")
        assert autonomous_response.status_code == 200
        autonomous_personas = autonomous_response.json()
        assert len(autonomous_personas) == 2  # Personas 1, 3
        
        for persona in autonomous_personas:
            assert persona["mode"] == "autonomous"
        
        # Clean up
        for persona_id in personas_created:
            client.delete(f"/api/personas/{persona_id}")
    
    def test_database_constraints_validation(self, client, clean_db):
        """Test that database constraints are properly enforced."""
        # Name too long (database should enforce 255 char limit)
        persona_data = {
            "name": "x" * 256,
            "description": "Test description",
            "template": "Test template",
            "mode": "reactive"
        }
        
        response = client.post("/api/personas", json=persona_data)
        # Should be rejected by validation before hitting database
        assert response.status_code == 422
    
    def test_mode_values_persistence(self, client, clean_db):
        """Test that mode values are correctly stored and retrieved."""
        # Test all valid mode values
        for mode in ["reactive", "autonomous"]:
            persona_data = {
                "name": f"Test {mode.title()} Persona",
                "description": f"Testing {mode} mode",
                "template": "Test template",
                "mode": mode
            }
            
            if mode == "autonomous":
                persona_data["loop_frequency"] = "2.0"
            
            response = client.post("/api/personas", json=persona_data)
            assert response.status_code == 201
            
            created_persona = response.json()
            assert created_persona["mode"] == mode
            
            # Verify in database by retrieving
            persona_id = created_persona["id"]
            get_response = client.get(f"/api/personas/{persona_id}")
            assert get_response.json()["mode"] == mode
            
            # Clean up
            client.delete(f"/api/personas/{persona_id}")
    
    def test_concurrent_operations(self, client, clean_db):
        """Test concurrent creation and modification of personas."""
        # Create base persona
        persona_data = {
            "name": "Concurrency Test Persona",
            "description": "Testing concurrent operations",
            "template": "Initial template",
            "mode": "reactive"
        }
        
        create_response = client.post("/api/personas", json=persona_data)
        assert create_response.status_code == 201
        persona_id = create_response.json()["id"]
        
        # Simulate concurrent updates
        update_data_1 = {"name": "Updated by Process 1"}
        update_data_2 = {"name": "Updated by Process 2"}
        
        # Both updates should succeed (last one wins)
        response_1 = client.put(f"/api/personas/{persona_id}", json=update_data_1)
        response_2 = client.put(f"/api/personas/{persona_id}", json=update_data_2)
        
        assert response_1.status_code == 200
        assert response_2.status_code == 200
        
        # Verify final state
        final_response = client.get(f"/api/personas/{persona_id}")
        final_persona = final_response.json()
        assert final_persona["name"] == "Updated by Process 2"
        
        # Clean up
        client.delete(f"/api/personas/{persona_id}")
    
    def test_error_handling_with_database(self, client, clean_db):
        """Test error handling scenarios with real database."""
        # Test invalid UUID format
        invalid_uuid_response = client.get("/api/personas/not-a-uuid")
        assert invalid_uuid_response.status_code == 422
        
        # Test non-existent UUID (valid format but doesn't exist)
        non_existent_uuid = str(uuid.uuid4())
        not_found_response = client.get(f"/api/personas/{non_existent_uuid}")
        assert not_found_response.status_code == 404
        
        # Test deleting non-existent persona
        delete_response = client.delete(f"/api/personas/{non_existent_uuid}")
        assert delete_response.status_code == 404
        
        # Test updating non-existent persona
        update_data = {
            "name": "Non-existent Persona",
            "description": "This shouldn't work",
            "template": "Test template",
            "mode": "reactive"
        }
        update_response = client.put(f"/api/personas/{non_existent_uuid}", json=update_data)
        assert update_response.status_code == 404