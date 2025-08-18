"""
Integration tests for modules API with real PostgreSQL database.
These tests verify that the API works end-to-end with actual database operations.
"""

import pytest
import uuid
from fastapi.testclient import TestClient

from app.main import app
from app.models import Module, ModuleType, ExecutionTiming


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


class TestModulesIntegration:
    """Integration tests for modules CRUD operations with real database."""
    
    def test_full_module_lifecycle_simple(self, client, clean_db):
        """Test complete lifecycle of a simple module."""
        # Create module
        module_data = {
            "name": "Integration Test Logger",
            "description": "Simple logging utility for integration testing",
            "content": "console.log('integration test')",
            "type": "simple"
        }
        
        create_response = client.post("/api/modules", json=module_data)
        assert create_response.status_code == 201
        
        created_module = create_response.json()
        module_id = created_module["id"]
        
        # Verify UUID format
        uuid.UUID(module_id)  # This will raise ValueError if invalid
        
        # Read module
        get_response = client.get(f"/api/modules/{module_id}")
        assert get_response.status_code == 200
        
        retrieved_module = get_response.json()
        assert retrieved_module["id"] == module_id
        assert retrieved_module["name"] == module_data["name"]
        assert retrieved_module["type"] == "simple"
        assert retrieved_module["is_active"] is True
        
        # Update module
        updated_data = module_data.copy()
        updated_data["name"] = "Updated Integration Logger"
        updated_data["description"] = "Updated description for integration test"
        
        update_response = client.put(f"/api/modules/{module_id}", json=updated_data)
        assert update_response.status_code == 200
        
        updated_module = update_response.json()
        assert updated_module["name"] == "Updated Integration Logger"
        assert updated_module["description"] == "Updated description for integration test"
        
        # Verify update persisted
        get_updated_response = client.get(f"/api/modules/{module_id}")
        assert get_updated_response.json()["name"] == "Updated Integration Logger"
        
        # Delete module
        delete_response = client.delete(f"/api/modules/{module_id}")
        assert delete_response.status_code == 204
        
        # Verify deletion
        get_deleted_response = client.get(f"/api/modules/{module_id}")
        assert get_deleted_response.status_code == 404
    
    def test_full_module_lifecycle_advanced(self, client, clean_db):
        """Test complete lifecycle of an advanced module."""
        # Create advanced module
        module_data = {
            "name": "Integration Test Validator",
            "description": "Advanced validation module for integration testing",
            "content": "Validation logic for integration test",
            "type": "advanced",
            "trigger_pattern": "/integration/*",
            "script": "print('integration validation')",
            "timing": "before"
        }
        
        create_response = client.post("/api/modules", json=module_data)
        assert create_response.status_code == 201
        
        created_module = create_response.json()
        module_id = created_module["id"]
        
        # Verify all advanced fields
        assert created_module["trigger_pattern"] == "/integration/*"
        assert created_module["script"] == "print('integration validation')"
        assert created_module["timing"] == "before"
        
        # Test updating timing
        updated_data = module_data.copy()
        updated_data["timing"] = "after"
        
        update_response = client.put(f"/api/modules/{module_id}", json=updated_data)
        assert update_response.status_code == 200
        
        updated_module = update_response.json()
        assert updated_module["timing"] == "after"
        
        # Clean up
        client.delete(f"/api/modules/{module_id}")
    
    def test_module_list_pagination(self, client, clean_db):
        """Test module listing with multiple modules."""
        # Create multiple modules
        modules_created = []
        
        for i in range(5):
            module_data = {
                "name": f"Integration Module {i}",
                "description": f"Description for module {i}",
                "content": f"Content for module {i}",
                "type": "simple" if i % 2 == 0 else "advanced"
            }
            
            if module_data["type"] == "advanced":
                module_data["trigger_pattern"] = f"/test/{i}/*"
                module_data["timing"] = "before" if i % 4 == 1 else "after"
            
            response = client.post("/api/modules", json=module_data)
            assert response.status_code == 201
            modules_created.append(response.json()["id"])
        
        # Test listing all modules
        list_response = client.get("/api/modules")
        assert list_response.status_code == 200
        
        modules = list_response.json()
        assert len(modules) == 5
        
        # Test filtering by type
        simple_response = client.get("/api/modules?type=simple")
        assert simple_response.status_code == 200
        simple_modules = simple_response.json()
        assert len(simple_modules) == 3  # Modules 0, 2, 4
        
        for module in simple_modules:
            assert module["type"] == "simple"
        
        advanced_response = client.get("/api/modules?type=advanced")
        assert advanced_response.status_code == 200
        advanced_modules = advanced_response.json()
        assert len(advanced_modules) == 2  # Modules 1, 3
        
        for module in advanced_modules:
            assert module["type"] == "advanced"
        
        # Clean up
        for module_id in modules_created:
            client.delete(f"/api/modules/{module_id}")
    
    def test_database_constraints_validation(self, client, clean_db):
        """Test that database constraints are properly enforced."""
        # Test unique constraint if any (currently none in model)
        # Test field length constraints
        
        # Name too long (database should enforce 255 char limit)
        module_data = {
            "name": "x" * 256,
            "description": "Test description",
            "content": "Test content",
            "type": "simple"
        }
        
        response = client.post("/api/modules", json=module_data)
        # Should be rejected by validation before hitting database
        assert response.status_code == 422
    
    def test_enum_values_persistence(self, client, clean_db):
        """Test that enum values are correctly stored and retrieved."""
        # Test all valid ModuleType values
        for module_type in ["simple", "advanced"]:
            module_data = {
                "name": f"Test {module_type.title()} Module",
                "description": f"Testing {module_type} type",
                "content": "Test content",
                "type": module_type
            }
            
            response = client.post("/api/modules", json=module_data)
            assert response.status_code == 201
            
            created_module = response.json()
            assert created_module["type"] == module_type
            
            # Verify in database by retrieving
            module_id = created_module["id"]
            get_response = client.get(f"/api/modules/{module_id}")
            assert get_response.json()["type"] == module_type
            
            # Clean up
            client.delete(f"/api/modules/{module_id}")
        
        # Test all valid ExecutionTiming values for advanced modules
        for timing in ["before", "after", "custom"]:
            module_data = {
                "name": f"Test {timing.title()} Module",
                "description": f"Testing {timing} timing",
                "content": "Test content",
                "type": "advanced",
                "timing": timing
            }
            
            response = client.post("/api/modules", json=module_data)
            assert response.status_code == 201
            
            created_module = response.json()
            assert created_module["timing"] == timing
            
            # Clean up
            client.delete(f"/api/modules/{created_module['id']}")
    
    def test_concurrent_operations(self, client, clean_db):
        """Test concurrent creation and modification of modules."""
        # Create base module
        module_data = {
            "name": "Concurrency Test Module",
            "description": "Testing concurrent operations",
            "content": "Initial content",
            "type": "simple"
        }
        
        create_response = client.post("/api/modules", json=module_data)
        assert create_response.status_code == 201
        module_id = create_response.json()["id"]
        
        # Simulate concurrent updates
        update_data_1 = module_data.copy()
        update_data_1["name"] = "Updated by Process 1"
        
        update_data_2 = module_data.copy()
        update_data_2["name"] = "Updated by Process 2"
        
        # Both updates should succeed (last one wins)
        response_1 = client.put(f"/api/modules/{module_id}", json=update_data_1)
        response_2 = client.put(f"/api/modules/{module_id}", json=update_data_2)
        
        assert response_1.status_code == 200
        assert response_2.status_code == 200
        
        # Verify final state
        final_response = client.get(f"/api/modules/{module_id}")
        final_module = final_response.json()
        assert final_module["name"] == "Updated by Process 2"
        
        # Clean up
        client.delete(f"/api/modules/{module_id}")
    
    def test_error_handling_with_database(self, client, clean_db):
        """Test error handling scenarios with real database."""
        # Test invalid UUID format
        invalid_uuid_response = client.get("/api/modules/not-a-uuid")
        assert invalid_uuid_response.status_code == 422
        
        # Test non-existent UUID (valid format but doesn't exist)
        non_existent_uuid = str(uuid.uuid4())
        not_found_response = client.get(f"/api/modules/{non_existent_uuid}")
        assert not_found_response.status_code == 404
        
        # Test deleting non-existent module
        delete_response = client.delete(f"/api/modules/{non_existent_uuid}")
        assert delete_response.status_code == 404
        
        # Test updating non-existent module
        update_data = {
            "name": "Non-existent Module",
            "description": "This shouldn't work",
            "content": "Test content",
            "type": "simple"
        }
        update_response = client.put(f"/api/modules/{non_existent_uuid}", json=update_data)
        assert update_response.status_code == 404