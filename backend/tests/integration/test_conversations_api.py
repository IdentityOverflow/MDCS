"""
Integration tests for conversation API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.models.persona import Persona
from app.models.conversation import Conversation, Message, MessageRole
import uuid
import json


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
def test_persona(db_session: Session):
    """Create a test persona."""
    persona = Persona(
        name="Test Persona",
        description="A test persona for conversation testing",
        template="You are a helpful assistant.",
        mode="reactive"
    )
    db_session.add(persona)
    db_session.commit()
    db_session.refresh(persona)
    return persona


@pytest.fixture
def test_conversation_data(test_persona):
    """Test conversation data."""
    return {
        "title": "Test Conversation",
        "persona_id": str(test_persona.id),
        "provider_type": "ollama",
        "provider_config": {"model": "test-model"}
    }


@pytest.fixture
def test_conversation(db_session: Session, test_persona):
    """Create a test conversation."""
    conversation = Conversation(
        title="Existing Test Conversation",
        persona_id=test_persona.id,
        provider_type="ollama",
        provider_config={"model": "test-model"}
    )
    db_session.add(conversation)
    db_session.commit()
    db_session.refresh(conversation)
    return conversation


class TestConversationsCreateEndpoint:
    """Test conversation creation endpoint."""
    
    def test_create_conversation_success(self, client: TestClient, test_conversation_data):
        """Test successful conversation creation."""
        response = client.post("/api/conversations", json=test_conversation_data)
        
        assert response.status_code == 201
        data = response.json()
        
        assert "id" in data
        assert data["title"] == test_conversation_data["title"]
        assert data["persona_id"] == test_conversation_data["persona_id"]
        assert data["provider_type"] == test_conversation_data["provider_type"]
        assert data["provider_config"] == test_conversation_data["provider_config"]
        assert data["messages"] == []
        assert "created_at" in data
        assert "updated_at" in data
    
    def test_create_conversation_without_persona(self, client: TestClient):
        """Test conversation creation without persona."""
        conversation_data = {
            "title": "No Persona Conversation",
            "provider_type": "openai"
        }
        
        response = client.post("/api/conversations", json=conversation_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["persona_id"] is None
        assert data["title"] == conversation_data["title"]
    
    def test_create_conversation_invalid_persona(self, client: TestClient):
        """Test conversation creation with invalid persona ID."""
        conversation_data = {
            "title": "Invalid Persona",
            "persona_id": str(uuid.uuid4()),  # Non-existent persona
            "provider_type": "ollama"
        }
        
        response = client.post("/api/conversations", json=conversation_data)
        
        assert response.status_code == 404
        assert "Persona not found" in response.json()["detail"]
    
    def test_create_conversation_missing_title(self, client: TestClient):
        """Test conversation creation without title."""
        response = client.post("/api/conversations", json={})
        
        assert response.status_code == 422


class TestConversationsGetEndpoint:
    """Test conversation retrieval endpoints."""
    
    def test_get_conversation_by_persona(self, client: TestClient, test_conversation, test_persona):
        """Test getting conversation by persona ID."""
        response = client.get(f"/api/conversations/by-persona/{test_persona.id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == str(test_conversation.id)
        assert data["persona_id"] == str(test_persona.id)
        assert data["title"] == test_conversation.title
    
    def test_get_conversation_by_nonexistent_persona(self, client: TestClient):
        """Test getting conversation for non-existent persona."""
        fake_persona_id = uuid.uuid4()
        response = client.get(f"/api/conversations/by-persona/{fake_persona_id}")
        
        assert response.status_code == 404
        assert "Conversation not found" in response.json()["detail"]
    
    def test_get_conversation_by_id(self, client: TestClient, test_conversation):
        """Test getting conversation by ID."""
        response = client.get(f"/api/conversations/{test_conversation.id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == str(test_conversation.id)
        assert data["title"] == test_conversation.title
    
    def test_get_nonexistent_conversation(self, client: TestClient):
        """Test getting non-existent conversation."""
        fake_id = uuid.uuid4()
        response = client.get(f"/api/conversations/{fake_id}")
        
        assert response.status_code == 404


class TestConversationsUpdateEndpoint:
    """Test conversation update endpoint."""
    
    def test_update_conversation_title(self, client: TestClient, test_conversation):
        """Test updating conversation title."""
        update_data = {"title": "Updated Title"}
        
        response = client.put(f"/api/conversations/{test_conversation.id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["id"] == str(test_conversation.id)
    
    def test_update_nonexistent_conversation(self, client: TestClient):
        """Test updating non-existent conversation."""
        fake_id = uuid.uuid4()
        update_data = {"title": "New Title"}
        
        response = client.put(f"/api/conversations/{fake_id}", json=update_data)
        
        assert response.status_code == 404


class TestConversationsDeleteEndpoint:
    """Test conversation deletion endpoint."""
    
    def test_delete_conversation(self, client: TestClient, test_conversation):
        """Test deleting a conversation."""
        response = client.delete(f"/api/conversations/{test_conversation.id}")
        
        assert response.status_code == 204
        
        # Verify conversation is deleted
        get_response = client.get(f"/api/conversations/{test_conversation.id}")
        assert get_response.status_code == 404
    
    def test_delete_nonexistent_conversation(self, client: TestClient):
        """Test deleting non-existent conversation."""
        fake_id = uuid.uuid4()
        response = client.delete(f"/api/conversations/{fake_id}")
        
        assert response.status_code == 404


class TestConversationsWithMessages:
    """Test conversation endpoints with messages."""
    
    def test_get_conversation_with_messages(self, client: TestClient, test_conversation, db_session: Session):
        """Test getting conversation that includes messages."""
        # Add some messages to the conversation
        message1 = Message(
            conversation_id=test_conversation.id,
            role=MessageRole.USER,
            content="Hello",
            thinking=None
        )
        message2 = Message(
            conversation_id=test_conversation.id,
            role=MessageRole.ASSISTANT,
            content="Hi there!",
            thinking="The user is greeting me, I should respond politely."
        )
        
        db_session.add_all([message1, message2])
        db_session.commit()
        
        response = client.get(f"/api/conversations/{test_conversation.id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["messages"]) == 2
        assert data["messages"][0]["content"] == "Hello"
        assert data["messages"][0]["thinking"] is None
        assert data["messages"][1]["content"] == "Hi there!"
        assert data["messages"][1]["thinking"] == "The user is greeting me, I should respond politely."
    
    def test_delete_conversation_cascades_messages(self, client: TestClient, test_conversation, db_session: Session):
        """Test that deleting conversation also deletes associated messages."""
        # Add a message
        message = Message(
            conversation_id=test_conversation.id,
            role=MessageRole.USER,
            content="Test message"
        )
        db_session.add(message)
        db_session.commit()
        message_id = message.id
        
        # Delete conversation
        response = client.delete(f"/api/conversations/{test_conversation.id}")
        assert response.status_code == 204
        
        # Refresh session to see changes made by the API endpoint
        db_session.expire_all()
        
        # Verify message is also deleted
        deleted_message = db_session.get(Message, message_id)
        assert deleted_message is None