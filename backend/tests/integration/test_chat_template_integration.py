"""
Integration tests for Chat System with Template Resolution.

Tests how the chat system integrates with the module resolution service
to resolve @module_name references in persona templates before sending to AI providers.
"""

import pytest
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.models import Module, ModuleType, Persona


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


class TestChatTemplateIntegration:
    """Integration tests for chat system with template resolution."""
    
    def test_chat_send_with_template_resolution(self, client, db_session):
        """Test that chat/send endpoint resolves persona templates."""
        # Create modules
        greeting_module = Module(
            name="greeting",
            description="Greeting module", 
            content="Hello! I'm an AI assistant.",
            type=ModuleType.SIMPLE,
            is_active=True
        )
        
        safety_module = Module(
            name="safety_rules",
            description="Safety guidelines",
            content="I follow safety protocols and am helpful, harmless, and honest.",
            type=ModuleType.SIMPLE,
            is_active=True
        )
        
        db_session.add(greeting_module)
        db_session.add(safety_module)
        db_session.commit()
        
        # Create persona with template containing module references
        persona = Persona(
            name="Test Assistant",
            description="Test persona with modules",
            template="You are a helpful AI. @greeting @safety_rules Be concise.",
            is_active=True
        )
        
        db_session.add(persona)
        db_session.commit()
        
        # Mock AI provider to capture the resolved system prompt
        with patch('app.services.ollama_service.OllamaService.send_message') as mock_ollama:
            # Mock the ChatResponse object
            from app.services.ai_providers import ChatResponse, ProviderType
            mock_ollama.return_value = ChatResponse(
                content="Hello! How can I help you?",
                model="llama3.2",
                provider_type=ProviderType.OLLAMA,
                metadata={},
                thinking=None
            )
            
            # Send chat request with persona
            response = client.post(
                "/api/chat/send",
                json={
                    "message": "Hello",
                    "persona_id": str(persona.id),
                    "provider": "ollama",
                    "stream": False,
                    "provider_settings": {
                        "host": "http://localhost:11434",
                        "model": "llama3.2"
                    },
                    "chat_controls": {
                        "temperature": 0.7,
                        "max_tokens": 100
                    }
                }
            )
            
            assert response.status_code == 200
            
            # Verify that ollama service was called with resolved template
            mock_ollama.assert_called_once()
            call_args = mock_ollama.call_args[0][0]  # First positional argument (request)
            
            # The system prompt should have module references resolved
            expected_system_prompt = "You are a helpful AI. Hello! I'm an AI assistant. I follow safety protocols and am helpful, harmless, and honest. Be concise."
            assert call_args.system_prompt == expected_system_prompt
    
    def test_chat_stream_with_template_resolution(self, client, db_session):
        """Test that chat/stream endpoint resolves persona templates."""
        # Create a simple module
        rules_module = Module(
            name="rules",
            description="Basic rules",
            content="Be helpful and accurate.",
            type=ModuleType.SIMPLE,
            is_active=True
        )
        
        db_session.add(rules_module)
        db_session.commit()
        
        # Create persona with template
        persona = Persona(
            name="Streaming Assistant",
            description="Test streaming persona",
            template="You are an AI assistant. @rules Always respond clearly.",
            is_active=True
        )
        
        db_session.add(persona)
        db_session.commit()
        
        # Mock streaming response
        def mock_stream_generator():
            yield "data: Hello"
            yield "data: [DONE]"
        
        with patch('app.services.ollama_service.OllamaService.send_message_stream') as mock_stream:
            mock_stream.return_value = mock_stream_generator()
            
            # Send streaming chat request
            response = client.post(
                "/api/chat/stream",
                json={
                    "message": "Hi there",
                    "persona_id": str(persona.id),
                    "provider": "ollama",
                    "stream": True,
                    "provider_settings": {
                        "host": "http://localhost:11434",
                        "model": "llama3.2"
                    },
                    "chat_controls": {
                        "temperature": 0.5
                    }
                }
            )
            
            assert response.status_code == 200
            
            # Verify stream service was called with resolved template
            mock_stream.assert_called_once()
            call_args = mock_stream.call_args[0][0]  # First positional argument
            
            expected_system_prompt = "You are an AI assistant. Be helpful and accurate. Always respond clearly."
            assert call_args.system_prompt == expected_system_prompt
    
    def test_chat_with_missing_modules_in_template(self, client, db_session):
        """Test chat handling when persona template has missing module references."""
        # Create persona with reference to non-existent module
        persona = Persona(
            name="Broken Template Persona",
            description="Persona with missing module reference",
            template="You are helpful. @missing_module Please assist the user.",
            is_active=True
        )
        
        db_session.add(persona)
        db_session.commit()
        
        with patch('app.services.ollama_service.OllamaService.send_message') as mock_ollama:
            from app.services.ai_providers import ChatResponse, ProviderType
            mock_ollama.return_value = ChatResponse(
                content="I'll help you!",
                model="llama3.2",
                provider_type=ProviderType.OLLAMA,
                metadata={},
                thinking=None
            )
            
            response = client.post(
                "/api/chat/send",
                json={
                    "message": "Help me",
                    "persona_id": str(persona.id),
                    "provider": "ollama",
                    "stream": False,
                    "provider_settings": {
                        "host": "http://localhost:11434",
                        "model": "llama3.2"
                    },
                    "chat_controls": {}
                }
            )
            
            assert response.status_code == 200
            
            # Verify service was called with template where missing module is kept as @name
            mock_ollama.assert_called_once()
            call_args = mock_ollama.call_args[0][0]
            
            expected_system_prompt = "You are helpful. @missing_module Please assist the user."
            assert call_args.system_prompt == expected_system_prompt
    
    def test_chat_with_recursive_module_resolution(self, client, db_session):
        """Test chat with nested module references in persona template."""
        # Create chain of modules: persona -> intro_module -> greeting_module
        greeting_module = Module(
            name="greeting",
            description="Basic greeting",
            content="Hello there!",
            type=ModuleType.SIMPLE,
            is_active=True
        )
        
        intro_module = Module(
            name="intro",
            description="Introduction with nested greeting",
            content="@greeting I'm Claude, your AI assistant.",
            type=ModuleType.SIMPLE,
            is_active=True
        )
        
        db_session.add(greeting_module)
        db_session.add(intro_module)
        db_session.commit()
        
        # Create persona that references the intro module (which references greeting)
        persona = Persona(
            name="Recursive Template Persona",
            description="Persona with nested module references",
            template="@intro How can I help you today?",
            is_active=True
        )
        
        db_session.add(persona)
        db_session.commit()
        
        with patch('app.services.openai_service.OpenAIService.send_message') as mock_openai:
            from app.services.ai_providers import ChatResponse, ProviderType
            mock_openai.return_value = ChatResponse(
                content="I'm ready to help!",
                model="gpt-4",
                provider_type=ProviderType.OPENAI,
                metadata={},
                thinking=None
            )
            
            response = client.post(
                "/api/chat/send",
                json={
                    "message": "What can you do?",
                    "persona_id": str(persona.id),
                    "provider": "openai",
                    "stream": False,
                    "provider_settings": {
                        "api_key": "test-key",
                        "model": "gpt-4"
                    },
                    "chat_controls": {
                        "temperature": 0.3
                    }
                }
            )
            
            assert response.status_code == 200
            
            # Verify recursive resolution worked
            mock_openai.assert_called_once()
            call_args = mock_openai.call_args[0][0]
            
            # Should resolve: @intro -> "@greeting I'm Claude..." -> "Hello there! I'm Claude..."
            expected_system_prompt = "Hello there! I'm Claude, your AI assistant. How can I help you today?"
            assert call_args.system_prompt == expected_system_prompt
    
    def test_chat_with_circular_dependency_in_template(self, client, db_session):
        """Test chat handling of circular dependencies in module resolution."""
        # Create circular reference: module_a -> module_b -> module_a
        module_a = Module(
            name="module_a",
            description="Module A",
            content="A references @module_b",
            type=ModuleType.SIMPLE,
            is_active=True
        )
        
        module_b = Module(
            name="module_b", 
            description="Module B",
            content="B references @module_a",
            type=ModuleType.SIMPLE,
            is_active=True
        )
        
        db_session.add(module_a)
        db_session.add(module_b)
        db_session.commit()
        
        # Create persona that triggers the circular reference
        persona = Persona(
            name="Circular Template Persona",
            description="Persona with circular module dependencies",
            template="You are an AI. @module_a Please help.",
            is_active=True
        )
        
        db_session.add(persona)
        db_session.commit()
        
        with patch('app.services.ollama_service.OllamaService.send_message') as mock_ollama:
            from app.services.ai_providers import ChatResponse, ProviderType
            mock_ollama.return_value = ChatResponse(
                content="I'm here to help!",
                model="llama3.2",
                provider_type=ProviderType.OLLAMA,
                metadata={},
                thinking=None
            )
            
            response = client.post(
                "/api/chat/send",
                json={
                    "message": "Help me",
                    "persona_id": str(persona.id),
                    "provider": "ollama",
                    "stream": False,
                    "provider_settings": {
                        "host": "http://localhost:11434",
                        "model": "llama3.2"
                    },
                    "chat_controls": {}
                }
            )
            
            # Should still succeed despite circular dependency
            assert response.status_code == 200
            
            # Verify service was called with partially resolved template
            mock_ollama.assert_called_once()
            call_args = mock_ollama.call_args[0][0]
            
            # Should handle circular dependency gracefully (exact content depends on implementation)
            assert "You are an AI." in call_args.system_prompt
            assert "Please help." in call_args.system_prompt
    
    def test_chat_without_persona_uses_empty_system_prompt(self, client, db_session):
        """Test that chat without persona_id uses empty system prompt."""
        with patch('app.services.ollama_service.OllamaService.send_message') as mock_ollama:
            from app.services.ai_providers import ChatResponse, ProviderType
            mock_ollama.return_value = ChatResponse(
                content="Hello!",
                model="llama3.2",
                provider_type=ProviderType.OLLAMA,
                metadata={},
                thinking=None
            )
            
            response = client.post(
                "/api/chat/send",
                json={
                    "message": "Hi",
                    # No persona_id provided
                    "provider": "ollama",
                    "stream": False,
                    "provider_settings": {
                        "host": "http://localhost:11434",
                        "model": "llama3.2"
                    },
                    "chat_controls": {}
                }
            )
            
            assert response.status_code == 200
            
            # Verify empty system prompt was used
            mock_ollama.assert_called_once()
            call_args = mock_ollama.call_args[0][0]
            assert call_args.system_prompt == ""
    
    def test_chat_with_inactive_persona_fails(self, client, db_session):
        """Test that chat with inactive persona returns error."""
        # Create inactive persona
        persona = Persona(
            name="Inactive Persona",
            description="This persona is inactive",
            template="You are helpful.",
            is_active=False  # Inactive
        )
        
        db_session.add(persona)
        db_session.commit()
        
        response = client.post(
            "/api/chat/send",
            json={
                "message": "Hello",
                "persona_id": str(persona.id),
                "provider": "ollama",
                "stream": False,
                "provider_settings": {
                    "host": "http://localhost:11434",
                    "model": "llama3.2"
                },
                "chat_controls": {}
            }
        )
        
        assert response.status_code == 404  # Persona not found (inactive)
        
    def test_chat_with_nonexistent_persona_fails(self, client, db_session):
        """Test that chat with non-existent persona ID returns error."""
        import uuid
        
        response = client.post(
            "/api/chat/send",
            json={
                "message": "Hello",
                "persona_id": str(uuid.uuid4()),  # Non-existent UUID
                "provider": "ollama",
                "stream": False,
                "provider_settings": {
                    "host": "http://localhost:11434",
                    "model": "llama3.2"
                },
                "chat_controls": {}
            }
        )
        
        assert response.status_code == 404  # Persona not found
    
    def test_resolved_template_stored_in_conversation(self, client, db_session):
        """Test that resolved system prompt is stored in conversation for debugging."""
        # Create a module and persona
        module = Module(
            name="debug_module",
            description="Debug module",
            content="Debug info: I'm in debug mode.",
            type=ModuleType.SIMPLE,
            is_active=True
        )
        
        db_session.add(module)
        db_session.commit()
        
        persona = Persona(
            name="Debug Persona",
            description="Persona for debug testing",
            template="System: @debug_module Ready to help.",
            is_active=True
        )
        
        db_session.add(persona)
        db_session.commit()
        
        with patch('app.services.ollama_service.OllamaService.send_message') as mock_ollama:
            from app.services.ai_providers import ChatResponse, ProviderType
            mock_ollama.return_value = ChatResponse(
                content="Debug response",
                model="llama3.2",
                provider_type=ProviderType.OLLAMA,
                metadata={},
                thinking=None
            )
            
            response = client.post(
                "/api/chat/send",
                json={
                    "message": "Debug test",
                    "persona_id": str(persona.id),
                    "provider": "ollama",
                    "stream": False,
                    "provider_settings": {
                        "host": "http://localhost:11434",
                        "model": "llama3.2"
                    },
                    "chat_controls": {}
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Response should include the resolved system prompt for debugging
            assert "resolved_system_prompt" in data
            expected_prompt = "System: Debug info: I'm in debug mode. Ready to help."
            assert data["resolved_system_prompt"] == expected_prompt

    def test_chat_with_advanced_module_variable_resolution(self, client, db_session):
        """Test chat with advanced module that uses ${variable} resolution."""
        from app.models import ExecutionContext
        
        # Create advanced module with script
        advanced_module = Module(
            name="ai_identity",
            description="AI identity with dynamic content",
            content="Hello! I'm ${name}. The time is ${current_time}.",
            type=ModuleType.ADVANCED,
            script="""
name = "AVA"
current_time = ctx.get_current_time()
""",
            trigger_pattern=None,  # Always execute
            execution_context=ExecutionContext.IMMEDIATE,
            is_active=True
        )
        
        db_session.add(advanced_module)
        db_session.commit()
        
        # Create persona that uses the advanced module
        persona = Persona(
            name="Advanced Test Persona",
            description="Persona with advanced module",
            template="@ai_identity Nice to meet you!",
            is_active=True
        )
        
        db_session.add(persona)
        db_session.commit()
        
        with patch('app.services.ollama_service.OllamaService.send_message') as mock_ollama:
            from app.services.ai_providers import ChatResponse, ProviderType
            mock_ollama.return_value = ChatResponse(
                content="Nice to meet you too!",
                model="llama3.2",
                provider_type=ProviderType.OLLAMA,
                metadata={},
                thinking=None
            )
            
            response = client.post(
                "/api/chat/send",
                json={
                    "message": "Hello",
                    "persona_id": str(persona.id),
                    "provider": "ollama",
                    "stream": False,
                    "provider_settings": {
                        "host": "http://localhost:11434",
                        "model": "llama3.2"
                    },
                    "chat_controls": {}
                }
            )
            
            assert response.status_code == 200
            
            # Verify service was called with resolved system prompt
            mock_ollama.assert_called_once()
            call_args = mock_ollama.call_args[0][0]
            
            # Advanced module should be resolved with script variables
            # The ${name} and ${current_time} should be replaced with actual values
            system_prompt = call_args.system_prompt
            assert system_prompt.startswith("Hello! I'm AVA. The time is ")
            assert "Nice to meet you!" in system_prompt
            assert "${name}" not in system_prompt  # Should be resolved
            assert "${current_time}" not in system_prompt  # Should be resolved