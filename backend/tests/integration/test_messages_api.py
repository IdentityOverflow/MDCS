"""
Integration tests for message API endpoints.
Following TDD approach - comprehensive tests for message CRUD operations.
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
        description="A test persona for message testing",
        template="You are a helpful assistant.",
        mode="reactive"
    )
    db_session.add(persona)
    db_session.commit()
    db_session.refresh(persona)
    return persona


@pytest.fixture
def test_conversation(db_session: Session, test_persona):
    """Create a test conversation."""
    conversation = Conversation(
        title="Test Conversation",
        persona_id=test_persona.id,
        provider_type="ollama",
        provider_config={"model": "test-model"}
    )
    db_session.add(conversation)
    db_session.commit()
    db_session.refresh(conversation)
    return conversation


@pytest.fixture
def test_message_data(test_conversation):
    """Test message data for creation."""
    return {
        "conversation_id": str(test_conversation.id),
        "role": "user",
        "content": "Hello, this is a test message",
        "thinking": None,
        "extra_data": {"test": "metadata"},
        "input_tokens": None,
        "output_tokens": None
    }


@pytest.fixture
def test_message_with_thinking_data(test_conversation):
    """Test message data with thinking content."""
    return {
        "conversation_id": str(test_conversation.id),
        "role": "assistant",
        "content": "Hello! I'm happy to help you with your questions.",
        "thinking": "The user is greeting me. I should respond politely and offer assistance.",
        "extra_data": {"reasoning_steps": ["greeting_detected", "polite_response_planned"]},
        "input_tokens": 15,
        "output_tokens": 42
    }


@pytest.fixture
def test_message(db_session: Session, test_conversation):
    """Create a test message."""
    message = Message(
        conversation_id=test_conversation.id,
        role=MessageRole.USER,
        content="Existing test message",
        thinking=None,
        extra_data={"test": "existing"}
    )
    db_session.add(message)
    db_session.commit()
    db_session.refresh(message)
    return message


class TestMessagesCreateEndpoint:
    """Test message creation endpoint."""
    
    def test_create_message_success(self, client: TestClient, test_message_data):
        """Test successful message creation."""
        response = client.post("/api/messages", json=test_message_data)
        
        assert response.status_code == 201
        data = response.json()
        
        assert "id" in data
        assert data["conversation_id"] == test_message_data["conversation_id"]
        assert data["role"] == test_message_data["role"]
        assert data["content"] == test_message_data["content"]
        assert data["thinking"] == test_message_data["thinking"]
        assert data["extra_data"] == test_message_data["extra_data"]
        assert data["input_tokens"] == test_message_data["input_tokens"]
        assert data["output_tokens"] == test_message_data["output_tokens"]
        assert "created_at" in data
        assert "updated_at" in data
    
    def test_create_message_with_thinking(self, client: TestClient, test_message_with_thinking_data):
        """Test creating message with thinking content."""
        response = client.post("/api/messages", json=test_message_with_thinking_data)
        
        assert response.status_code == 201
        data = response.json()
        
        assert data["role"] == "assistant"
        assert data["content"] == test_message_with_thinking_data["content"]
        assert data["thinking"] == test_message_with_thinking_data["thinking"]
        assert data["input_tokens"] == 15
        assert data["output_tokens"] == 42
    
    def test_create_message_invalid_conversation_id(self, client: TestClient, test_message_data):
        """Test message creation with invalid conversation ID."""
        invalid_data = test_message_data.copy()
        invalid_data["conversation_id"] = str(uuid.uuid4())  # Non-existent conversation
        
        response = client.post("/api/messages", json=invalid_data)
        
        assert response.status_code == 404
        assert "Conversation not found" in response.json()["detail"]
    
    def test_create_message_invalid_role(self, client: TestClient, test_message_data):
        """Test message creation with invalid role."""
        invalid_data = test_message_data.copy()
        invalid_data["role"] = "invalid_role"
        
        response = client.post("/api/messages", json=invalid_data)
        
        assert response.status_code == 422
    
    def test_create_message_missing_content(self, client: TestClient, test_message_data):
        """Test message creation without content."""
        invalid_data = test_message_data.copy()
        del invalid_data["content"]
        
        response = client.post("/api/messages", json=invalid_data)
        
        assert response.status_code == 422
    
    def test_create_message_empty_content(self, client: TestClient, test_message_data):
        """Test message creation with empty content."""
        invalid_data = test_message_data.copy()
        invalid_data["content"] = ""
        
        response = client.post("/api/messages", json=invalid_data)
        
        assert response.status_code == 422


class TestMessagesGetEndpoint:
    """Test message retrieval endpoints."""
    
    def test_get_message_by_id(self, client: TestClient, test_message):
        """Test getting message by ID."""
        response = client.get(f"/api/messages/{test_message.id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == str(test_message.id)
        assert data["conversation_id"] == str(test_message.conversation_id)
        assert data["role"] == test_message.role.value
        assert data["content"] == test_message.content
        assert data["thinking"] == test_message.thinking
        assert data["extra_data"] == test_message.extra_data
    
    def test_get_nonexistent_message(self, client: TestClient):
        """Test getting non-existent message."""
        fake_id = uuid.uuid4()
        response = client.get(f"/api/messages/{fake_id}")
        
        assert response.status_code == 404
    
    def test_get_message_invalid_uuid(self, client: TestClient):
        """Test getting message with invalid UUID format."""
        response = client.get("/api/messages/invalid-uuid")
        
        assert response.status_code == 422
    
    def test_list_messages_by_conversation(self, client: TestClient, test_conversation, db_session: Session):
        """Test listing messages for a specific conversation."""
        # Create multiple messages
        messages_data = [
            Message(
                conversation_id=test_conversation.id,
                role=MessageRole.USER,
                content="First message"
            ),
            Message(
                conversation_id=test_conversation.id,
                role=MessageRole.ASSISTANT,
                content="Second message",
                thinking="Processing the first message"
            ),
            Message(
                conversation_id=test_conversation.id,
                role=MessageRole.USER,
                content="Third message"
            )
        ]
        
        db_session.add_all(messages_data)
        db_session.commit()
        
        response = client.get(f"/api/messages/by-conversation/{test_conversation.id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) == 3
        
        # Check ordering (should be by created_at)
        assert data[0]["content"] == "First message"
        assert data[1]["content"] == "Second message"
        assert data[1]["thinking"] == "Processing the first message"
        assert data[2]["content"] == "Third message"
    
    def test_list_messages_nonexistent_conversation(self, client: TestClient):
        """Test listing messages for non-existent conversation."""
        fake_conversation_id = uuid.uuid4()
        response = client.get(f"/api/messages/by-conversation/{fake_conversation_id}")
        
        assert response.status_code == 404


class TestMessagesUpdateEndpoint:
    """Test message update endpoint."""
    
    def test_update_message_content(self, client: TestClient, test_message):
        """Test updating message content."""
        update_data = {
            "content": "Updated message content",
            "thinking": "Updated thinking content"
        }
        
        response = client.put(f"/api/messages/{test_message.id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == str(test_message.id)
        assert data["content"] == "Updated message content"
        assert data["thinking"] == "Updated thinking content"
        # Other fields should remain unchanged
        assert data["role"] == test_message.role.value
        assert data["extra_data"] == test_message.extra_data
    
    def test_update_message_thinking_only(self, client: TestClient, test_message):
        """Test updating only thinking content."""
        update_data = {
            "thinking": "New thinking content"
        }
        
        response = client.put(f"/api/messages/{test_message.id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["thinking"] == "New thinking content"
        assert data["content"] == test_message.content  # Original content unchanged
    
    def test_update_message_token_counts(self, client: TestClient, test_message):
        """Test updating token counts."""
        update_data = {
            "input_tokens": 25,
            "output_tokens": 50
        }
        
        response = client.put(f"/api/messages/{test_message.id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["input_tokens"] == 25
        assert data["output_tokens"] == 50
    
    def test_update_nonexistent_message(self, client: TestClient):
        """Test updating non-existent message."""
        fake_id = uuid.uuid4()
        update_data = {"content": "New content"}
        
        response = client.put(f"/api/messages/{fake_id}", json=update_data)
        
        assert response.status_code == 404
    
    def test_update_message_empty_content(self, client: TestClient, test_message):
        """Test updating message with empty content should fail."""
        update_data = {"content": ""}
        
        response = client.put(f"/api/messages/{test_message.id}", json=update_data)
        
        assert response.status_code == 422
    
    def test_update_message_role_forbidden(self, client: TestClient, test_message):
        """Test that updating message role is forbidden."""
        update_data = {"role": "assistant"}
        
        response = client.put(f"/api/messages/{test_message.id}", json=update_data)
        
        # Role updates should be ignored or forbidden
        assert response.status_code in [200, 422]
        if response.status_code == 200:
            # If update succeeds, role should remain unchanged
            data = response.json()
            assert data["role"] == test_message.role.value


class TestMessagesDeleteEndpoint:
    """Test message deletion endpoint."""
    
    def test_delete_message(self, client: TestClient, test_message):
        """Test deleting a message."""
        message_id = test_message.id
        
        response = client.delete(f"/api/messages/{message_id}")
        
        assert response.status_code == 204
        
        # Verify message is deleted
        get_response = client.get(f"/api/messages/{message_id}")
        assert get_response.status_code == 404
    
    def test_delete_nonexistent_message(self, client: TestClient):
        """Test deleting non-existent message."""
        fake_id = uuid.uuid4()
        response = client.delete(f"/api/messages/{fake_id}")
        
        assert response.status_code == 404
    
    def test_delete_message_invalid_uuid(self, client: TestClient):
        """Test deleting message with invalid UUID format."""
        response = client.delete("/api/messages/invalid-uuid")
        
        assert response.status_code == 422


class TestMessageValidation:
    """Test message validation rules."""
    
    def test_message_role_validation(self, client: TestClient, test_conversation):
        """Test all valid message roles."""
        valid_roles = ["user", "assistant", "system"]
        
        for role in valid_roles:
            message_data = {
                "conversation_id": str(test_conversation.id),
                "role": role,
                "content": f"Test message with {role} role"
            }
            
            response = client.post("/api/messages", json=message_data)
            assert response.status_code == 201
            
            data = response.json()
            assert data["role"] == role
    
    def test_message_thinking_optional(self, client: TestClient, test_conversation):
        """Test that thinking field is optional."""
        # Message without thinking
        message_data = {
            "conversation_id": str(test_conversation.id),
            "role": "user",
            "content": "Message without thinking"
        }
        
        response = client.post("/api/messages", json=message_data)
        assert response.status_code == 201
        
        data = response.json()
        assert data["thinking"] is None
    
    def test_message_extra_data_optional(self, client: TestClient, test_conversation):
        """Test that extra_data field is optional."""
        message_data = {
            "conversation_id": str(test_conversation.id),
            "role": "user",
            "content": "Message without extra data"
        }
        
        response = client.post("/api/messages", json=message_data)
        assert response.status_code == 201
        
        data = response.json()
        assert data["extra_data"] is None
    
    def test_message_token_counts_optional(self, client: TestClient, test_conversation):
        """Test that token count fields are optional."""
        message_data = {
            "conversation_id": str(test_conversation.id),
            "role": "assistant",
            "content": "Message without token counts"
        }
        
        response = client.post("/api/messages", json=message_data)
        assert response.status_code == 201
        
        data = response.json()
        assert data["input_tokens"] is None
        assert data["output_tokens"] is None


class TestMessageIntegration:
    """Test message endpoints integration with conversations."""
    
    def test_message_belongs_to_conversation(self, client: TestClient, test_conversation, test_message):
        """Test that messages are properly linked to conversations."""
        # Get the conversation and verify the message is included
        conv_response = client.get(f"/api/conversations/{test_conversation.id}")
        assert conv_response.status_code == 200
        
        conv_data = conv_response.json()
        message_ids = [msg["id"] for msg in conv_data["messages"]]
        assert str(test_message.id) in message_ids
    
    def test_create_message_updates_conversation(self, client: TestClient, test_conversation):
        """Test that creating a message is reflected in conversation."""
        # Create a new message
        message_data = {
            "conversation_id": str(test_conversation.id),
            "role": "user",
            "content": "New message for conversation"
        }
        
        msg_response = client.post("/api/messages", json=message_data)
        assert msg_response.status_code == 201
        new_message_id = msg_response.json()["id"]
        
        # Check that conversation includes the new message
        conv_response = client.get(f"/api/conversations/{test_conversation.id}")
        conv_data = conv_response.json()
        
        message_ids = [msg["id"] for msg in conv_data["messages"]]
        assert new_message_id in message_ids
    
    def test_delete_message_removes_from_conversation(self, client: TestClient, test_conversation, test_message):
        """Test that deleting a message removes it from conversation."""
        message_id = str(test_message.id)
        
        # Verify message exists in conversation
        conv_response = client.get(f"/api/conversations/{test_conversation.id}")
        conv_data = conv_response.json()
        message_ids_before = [msg["id"] for msg in conv_data["messages"]]
        assert message_id in message_ids_before
        
        # Delete the message
        delete_response = client.delete(f"/api/messages/{message_id}")
        assert delete_response.status_code == 204
        
        # Verify message is removed from conversation
        conv_response = client.get(f"/api/conversations/{test_conversation.id}")
        conv_data = conv_response.json()
        message_ids_after = [msg["id"] for msg in conv_data["messages"]]
        assert message_id not in message_ids_after