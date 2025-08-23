"""
Integration tests for the Template Resolution API.

Tests the API endpoint for resolving @module_name references in templates
with real database interactions.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.models import Module, ModuleType


@pytest.fixture
def client(test_engine, setup_test_database):
    """Create a test client for the FastAPI app with test database."""
    from app.database.connection import get_db
    
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
def db_session(test_engine, setup_test_database):
    """Create a database session for testing."""
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestSessionLocal()
    
    yield session
    
    # Cleanup: rollback any uncommitted changes and close session
    session.rollback()
    session.close()


class TestTemplateResolutionAPI:
    """Integration tests for template resolution API endpoint."""

    def test_resolve_template_basic_success(self, client, db_session):
        """Test successful basic template resolution via API."""
        # Create test modules
        greeting_module = Module(
            name="greeting",
            description="Greeting module",
            content="Hello! I'm here to help.",
            type=ModuleType.SIMPLE,
            is_active=True
        )
        
        safety_module = Module(
            name="safety",
            description="Safety guidelines",
            content="I follow safety guidelines.",
            type=ModuleType.SIMPLE,
            is_active=True
        )
        
        db_session.add(greeting_module)
        db_session.add(safety_module)
        db_session.commit()
        
        # Test template resolution
        template = "You are an AI. @greeting Also, @safety"
        
        response = client.post(
            "/api/templates/resolve",
            json={"template": template}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        expected_content = "You are an AI. Hello! I'm here to help. Also, I follow safety guidelines."
        assert data["resolved_template"] == expected_content
        assert data["warnings"] == []
        assert sorted(data["resolved_modules"]) == ["greeting", "safety"]

    def test_resolve_template_missing_modules(self, client, db_session):
        """Test resolution with missing modules."""
        # Create only one module
        greeting_module = Module(
            name="greeting",
            description="Greeting module",
            content="Hello!",
            type=ModuleType.SIMPLE,
            is_active=True
        )
        
        db_session.add(greeting_module)
        db_session.commit()
        
        template = "AI assistant. @greeting @missing_module"
        
        response = client.post(
            "/api/templates/resolve",
            json={"template": template}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Missing module should keep the module name string
        expected_content = "AI assistant. Hello! @missing_module"
        assert data["resolved_template"] == expected_content
        
        # Should have warning about missing module
        assert len(data["warnings"]) == 1
        warning = data["warnings"][0]
        assert warning["module_name"] == "missing_module"
        assert warning["warning_type"] == "module_not_found"
        assert "not found" in warning["message"]

    def test_resolve_template_recursive_resolution(self, client, db_session):
        """Test recursive module resolution."""
        # Module A references Module B
        module_a = Module(
            name="module_a",
            description="Module A",
            content="Start @module_b end",
            type=ModuleType.SIMPLE,
            is_active=True
        )
        
        module_b = Module(
            name="module_b",
            description="Module B",
            content="middle content",
            type=ModuleType.SIMPLE,
            is_active=True
        )
        
        db_session.add(module_a)
        db_session.add(module_b)
        db_session.commit()
        
        template = "Begin @module_a finish"
        
        response = client.post(
            "/api/templates/resolve",
            json={"template": template}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        expected_content = "Begin Start middle content end finish"
        assert data["resolved_template"] == expected_content
        assert sorted(data["resolved_modules"]) == ["module_a", "module_b"]

    def test_resolve_template_circular_dependency(self, client, db_session):
        """Test circular dependency detection."""
        # Module A references Module B, Module B references Module A
        module_a = Module(
            name="module_a",
            description="Module A",
            content="A: @module_b",
            type=ModuleType.SIMPLE,
            is_active=True
        )
        
        module_b = Module(
            name="module_b",
            description="Module B",
            content="B: @module_a",
            type=ModuleType.SIMPLE,
            is_active=True
        )
        
        db_session.add(module_a)
        db_session.add(module_b)
        db_session.commit()
        
        template = "Start @module_a end"
        
        response = client.post(
            "/api/templates/resolve",
            json={"template": template}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should detect circular dependency
        assert len(data["warnings"]) >= 1
        circular_warning = next(
            (w for w in data["warnings"] if w["warning_type"] == "circular_dependency"), 
            None
        )
        assert circular_warning is not None
        
        # Should still return content without crashing
        assert "Start" in data["resolved_template"]
        assert "end" in data["resolved_template"]

    def test_resolve_template_empty_content(self, client, db_session):
        """Test resolution with empty/null module content."""
        empty_module = Module(
            name="empty_module",
            description="Empty module",
            content="",  # Empty string
            type=ModuleType.SIMPLE,
            is_active=True
        )
        
        null_module = Module(
            name="null_module",
            description="Null module",
            content=None,  # Null content
            type=ModuleType.SIMPLE,
            is_active=True
        )
        
        db_session.add(empty_module)
        db_session.add(null_module)
        db_session.commit()
        
        template = "Start @empty_module middle @null_module end"
        
        response = client.post(
            "/api/templates/resolve",
            json={"template": template}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Empty/null modules should be replaced with empty string
        assert data["resolved_template"] == "Start  middle  end"
        assert data["warnings"] == []

    def test_resolve_template_inactive_modules(self, client, db_session):
        """Test that inactive modules are not resolved."""
        # Create an inactive module
        inactive_module = Module(
            name="inactive_module",
            description="Inactive module",
            content="I should not appear",
            type=ModuleType.SIMPLE,
            is_active=False  # Inactive
        )
        
        db_session.add(inactive_module)
        db_session.commit()
        
        template = "Test @inactive_module content"
        
        response = client.post(
            "/api/templates/resolve",
            json={"template": template}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Inactive module should be treated as missing
        assert data["resolved_template"] == "Test @inactive_module content"
        assert len(data["warnings"]) == 1
        assert data["warnings"][0]["warning_type"] == "module_not_found"

    def test_resolve_template_invalid_request(self, client, db_session):
        """Test validation of invalid requests."""
        # Missing template field
        response = client.post(
            "/api/templates/resolve",
            json={}
        )
        
        assert response.status_code == 422  # Validation error
        
        # Invalid template type
        response = client.post(
            "/api/templates/resolve",
            json={"template": 123}
        )
        
        assert response.status_code == 422  # Validation error

    def test_resolve_template_no_modules(self, client, db_session):
        """Test template with no module references."""
        template = "You are a helpful AI assistant. No modules here!"
        
        response = client.post(
            "/api/templates/resolve",
            json={"template": template}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Template should be returned unchanged
        assert data["resolved_template"] == template
        assert data["warnings"] == []
        assert data["resolved_modules"] == []

    def test_resolve_template_empty_template(self, client, db_session):
        """Test resolution of empty template."""
        response = client.post(
            "/api/templates/resolve",
            json={"template": ""}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["resolved_template"] == ""
        assert data["warnings"] == []
        assert data["resolved_modules"] == []

    def test_resolve_template_whitespace_handling(self, client, db_session):
        """Test proper handling of whitespace around module references."""
        greeting_module = Module(
            name="greeting",
            description="Greeting",
            content="Hello",
            type=ModuleType.SIMPLE,
            is_active=True
        )
        
        db_session.add(greeting_module)
        db_session.commit()
        
        # Test various whitespace scenarios
        templates = [
            ("@greeting world", "Hello world"),
            ("Say @greeting please", "Say Hello please"),
            ("@greeting", "Hello"),
            ("  @greeting  ", "  Hello  "),
        ]
        
        for template, expected in templates:
            response = client.post(
                "/api/templates/resolve",
                json={"template": template}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["resolved_template"] == expected

    def test_resolve_template_multiple_same_module(self, client, db_session):
        """Test template with multiple references to the same module."""
        greeting_module = Module(
            name="greeting",
            description="Greeting",
            content="Hello",
            type=ModuleType.SIMPLE,
            is_active=True
        )
        
        db_session.add(greeting_module)
        db_session.commit()
        
        template = "@greeting world! @greeting again!"
        
        response = client.post(
            "/api/templates/resolve",
            json={"template": template}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["resolved_template"] == "Hello world! Hello again!"
        assert data["resolved_modules"] == ["greeting"]  # Should only appear once

    def test_resolve_template_with_persona_id(self, client, db_session):
        """Test template resolution with persona_id parameter."""
        
        # This tests the optional persona_id parameter that might be used
        # for persona-specific module resolution in the future
        greeting_module = Module(
            name="greeting_api_test",
            description="Greeting for API test",
            content="Hello from API",
            type=ModuleType.SIMPLE,
            is_active=True
        )
        
        db_session.add(greeting_module)
        db_session.commit()
        
        template = "@greeting_api_test"
        
        response = client.post(
            "/api/templates/resolve",
            json={
                "template": template,
                "persona_id": "some-uuid-string"  # Optional parameter
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Debug: Print the actual response
        print(f"Expected: 'Hello from API', Got: '{data['resolved_template']}'")
        print(f"Warnings: {data.get('warnings', [])}")
        print(f"Resolved modules: {data.get('resolved_modules', [])}")
        
        assert data["resolved_template"] == "Hello from API"