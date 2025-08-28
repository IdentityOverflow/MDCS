"""
Tests for database models.
"""

import pytest
from datetime import datetime
import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base, Conversation, Message, MessageRole, Persona, Module, ModuleType, ExecutionContext


# Using db_session fixture from conftest.py instead of in-memory SQLite


class TestBaseModel:
    """Test the base model functionality."""
    
    def test_base_model_fields(self, clean_db):
        """Test that base model fields are present."""
        conversation = Conversation(title="Test Conversation")
        clean_db.add(conversation)
        clean_db.commit()
        
        # Check that base fields are populated
        assert conversation.id is not None
        assert conversation.created_at is not None
        assert conversation.updated_at is not None
        assert isinstance(conversation.created_at, datetime)
        assert isinstance(conversation.updated_at, datetime)
    
    def test_to_dict(self, clean_db):
        """Test the to_dict method."""
        conversation = Conversation(title="Test Conversation")
        clean_db.add(conversation)
        clean_db.commit()
        
        conv_dict = conversation.to_dict()
        
        assert isinstance(conv_dict, dict)
        assert conv_dict['title'] == "Test Conversation"
        assert 'id' in conv_dict
        assert 'created_at' in conv_dict
        assert 'updated_at' in conv_dict


class TestConversationModel:
    """Test the Conversation model."""
    
    def test_create_conversation(self, clean_db):
        """Test creating a conversation."""
        conversation = Conversation(
            title="Test Chat",
            provider_type="openai",
            provider_config={"model": "gpt-4"}
        )
        
        clean_db.add(conversation)
        clean_db.commit()
        
        assert conversation.id is not None
        assert isinstance(conversation.id, uuid.UUID)
        assert conversation.title == "Test Chat"
        assert conversation.provider_type == "openai"
        assert conversation.provider_config == {"model": "gpt-4"}
    
    def test_conversation_with_messages(self, clean_db):
        """Test conversation with related messages."""
        conversation = Conversation(title="Test Chat")
        clean_db.add(conversation)
        clean_db.commit()
        
        # Add messages
        message1 = Message(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content="Hello!"
        )
        message2 = Message(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content="Hi there!"
        )
        
        clean_db.add_all([message1, message2])
        clean_db.commit()
        
        # Test relationship
        assert len(conversation.messages) == 2
        assert conversation.messages[0].content == "Hello!"
        assert conversation.messages[1].content == "Hi there!"
    
    def test_conversation_repr(self, clean_db):
        """Test conversation string representation."""
        conversation = Conversation(title="Test Chat")
        clean_db.add(conversation)
        clean_db.commit()
        
        repr_str = repr(conversation)
        assert "Conversation" in repr_str
        assert "Test Chat" in repr_str
        assert str(conversation.id) in repr_str


class TestMessageModel:
    """Test the Message model."""
    
    def test_create_message(self, clean_db):
        """Test creating a message."""
        conversation = Conversation(title="Test Chat")
        clean_db.add(conversation)
        clean_db.commit()
        
        message = Message(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content="Test message",
            extra_data={"source": "test"},
            input_tokens=10,
            output_tokens=20
        )
        
        clean_db.add(message)
        clean_db.commit()
        
        assert message.id is not None
        assert message.conversation_id == conversation.id
        assert message.role == MessageRole.USER
        assert message.content == "Test message"
        assert message.extra_data == {"source": "test"}
        assert message.input_tokens == 10
        assert message.output_tokens == 20
    
    def test_message_role_enum(self):
        """Test message role enumeration."""
        assert MessageRole.USER == "user"
        assert MessageRole.ASSISTANT == "assistant"
        assert MessageRole.SYSTEM == "system"
    
    def test_message_repr(self, clean_db):
        """Test message string representation."""
        conversation = Conversation(title="Test Chat")
        clean_db.add(conversation)
        clean_db.commit()
        
        message = Message(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content="This is a test message"
        )
        clean_db.add(message)
        clean_db.commit()
        
        repr_str = repr(message)
        assert "Message" in repr_str
        assert "user" in repr_str
        assert "This is a test message" in repr_str
    
    def test_message_content_truncation_in_repr(self, clean_db):
        """Test that long message content is truncated in repr."""
        conversation = Conversation(title="Test Chat")
        clean_db.add(conversation)
        clean_db.commit()
        
        long_content = "This is a very long message content that should be truncated in the string representation"
        message = Message(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content=long_content
        )
        clean_db.add(message)
        clean_db.commit()
        
        repr_str = repr(message)
        assert "..." in repr_str
        assert len(repr_str) < len(long_content) + 100  # Should be much shorter


class TestPersonaModel:
    """Test the Persona model."""
    
    def test_create_persona(self, clean_db):
        """Test creating a persona."""
        persona = Persona(
            name="Test Persona",
            description="A test persona",
            template="You are {name}, a helpful assistant.",
            mode="reactive",
            first_message="Hello! I'm here to help.",
            image_path="/images/test.png",
            extra_data={"custom": "data"}
        )
        
        clean_db.add(persona)
        clean_db.commit()
        
        assert persona.id is not None
        assert isinstance(persona.id, uuid.UUID)
        assert persona.name == "Test Persona"
        assert persona.description == "A test persona"
        assert persona.template == "You are {name}, a helpful assistant."
        assert persona.mode == "reactive"
        assert persona.first_message == "Hello! I'm here to help."
        assert persona.image_path == "/images/test.png"
        assert persona.extra_data == {"custom": "data"}
        assert persona.is_active is True
    
    def test_persona_defaults(self, clean_db):
        """Test persona default values."""
        persona = Persona(
            name="Minimal Persona",
            template="You are a helpful assistant."
        )
        
        clean_db.add(persona)
        clean_db.commit()
        
        assert persona.mode == "reactive"
        assert persona.is_active is True
        assert persona.description is None
        assert persona.loop_frequency is None
    
    def test_persona_repr(self, clean_db):
        """Test persona string representation."""
        persona = Persona(
            name="Test Persona",
            template="Test template"
        )
        clean_db.add(persona)
        clean_db.commit()
        
        repr_str = repr(persona)
        assert "Persona" in repr_str
        assert "Test Persona" in repr_str


class TestModuleModel:
    """Test the Module model."""
    
    def test_create_simple_module(self, clean_db):
        """Test creating a simple module."""
        module = Module(
            name="Test Module",
            description="A test module",
            content="This is static content",
            type=ModuleType.SIMPLE,
            execution_context=ExecutionContext.IMMEDIATE
        )
        
        clean_db.add(module)
        clean_db.commit()
        
        assert module.id is not None
        assert isinstance(module.id, uuid.UUID)
        assert module.name == "Test Module"
        assert module.description == "A test module"
        assert module.content == "This is static content"
        assert module.type == ModuleType.SIMPLE
        assert module.execution_context == ExecutionContext.IMMEDIATE
        assert module.is_active is True
    
    def test_create_advanced_module(self, clean_db):
        """Test creating an advanced module."""
        module = Module(
            name="Advanced Module",
            content="Dynamic content here",
            type=ModuleType.ADVANCED,
            trigger_pattern="hello|hi",
            script="print('Hello from script')",
            execution_context=ExecutionContext.POST_RESPONSE
        )
        
        clean_db.add(module)
        clean_db.commit()
        
        assert module.type == ModuleType.ADVANCED
        assert module.trigger_pattern == "hello|hi"
        assert module.script == "print('Hello from script')"
        assert module.execution_context == ExecutionContext.POST_RESPONSE
    
    def test_module_enums(self):
        """Test module enumeration values."""
        assert ModuleType.SIMPLE == "simple"
        assert ModuleType.ADVANCED == "advanced"
        
        assert ExecutionContext.IMMEDIATE == "IMMEDIATE"
        assert ExecutionContext.POST_RESPONSE == "POST_RESPONSE"
        assert ExecutionContext.ON_DEMAND == "ON_DEMAND"
    
    def test_module_defaults(self, clean_db):
        """Test module default values."""
        module = Module(
            name="Default Module",
            content="Test content"
        )
        
        clean_db.add(module)
        clean_db.commit()
        
        assert module.type == ModuleType.SIMPLE
        assert module.execution_context == ExecutionContext.ON_DEMAND  # Default is ON_DEMAND
        assert module.requires_ai_inference is False  # Default is False
        assert module.is_active is True
    
    def test_module_repr(self, clean_db):
        """Test module string representation."""
        module = Module(
            name="Test Module",
            content="Test content",
            type=ModuleType.ADVANCED
        )
        clean_db.add(module)
        clean_db.commit()
        
        repr_str = repr(module)
        assert "Module" in repr_str
        assert "Test Module" in repr_str
        assert "advanced" in repr_str