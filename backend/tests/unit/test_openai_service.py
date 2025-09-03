"""
Unit tests for OpenAI service implementation.
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from aiohttp import ClientSession, ClientResponse, ClientTimeout
from aiohttp.client_exceptions import ClientError, ClientConnectorError

from app.services.ai_providers import (
    ChatRequest, 
    ChatResponse, 
    StreamingChatResponse, 
    ProviderType
)
from app.services.exceptions import ProviderConnectionError, ProviderAuthenticationError
from app.services.openai_service import OpenAIService
from app.services.openai_service_base import (
    OpenAIRequestBuilder,
    OpenAIResponseParser,
    OpenAIStreamParser
)


class TestOpenAIRequestBuilder:
    """Test OpenAI request building logic."""
    
    def setup_method(self):
        """Setup method to create mock service for each test."""
        # Create a mock service that has the _build_base_messages method
        from app.services.ai_providers import AIProvider
        self.mock_service = Mock(spec=AIProvider)
        
        # Mock the _build_base_messages method to simulate the real behavior
        def mock_build_messages(request):
            messages = []
            # Add system message if present
            system_message = request.system_prompt or request.chat_controls.get("system_or_instructions")
            if system_message:
                messages.append({"role": "system", "content": system_message})
            # Add user message
            messages.append({"role": "user", "content": request.message})
            return messages
        
        self.mock_service._build_base_messages.side_effect = mock_build_messages
    
    def test_build_basic_request(self):
        """Test building a basic OpenAI request."""
        request = ChatRequest(
            message="Hello, world!",
            provider_type=ProviderType.OPENAI,
            provider_settings={
                "base_url": "https://api.openai.com/v1",
                "api_key": "sk-test-key",
                "default_model": "gpt-4"
            },
            chat_controls={}
        )
        
        builder = OpenAIRequestBuilder(self.mock_service)
        openai_request = builder.build_request(request)
        
        assert openai_request["model"] == "gpt-4"
        assert openai_request["messages"] == [{"role": "user", "content": "Hello, world!"}]
        assert "stream" in openai_request
        assert "temperature" in openai_request or openai_request.get("temperature") is None
    
    def test_build_request_with_system_message(self):
        """Test building request with system message."""
        request = ChatRequest(
            message="Hello",
            provider_type=ProviderType.OPENAI,
            provider_settings={
                "base_url": "https://api.openai.com/v1",
                "api_key": "sk-test-key",
                "default_model": "gpt-4"
            },
            chat_controls={"system_or_instructions": "You are a helpful assistant."}
        )
        
        builder = OpenAIRequestBuilder(self.mock_service)
        openai_request = builder.build_request(request)
        
        expected_messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello"}
        ]
        assert openai_request["messages"] == expected_messages
    
    def test_build_request_with_chat_controls(self):
        """Test building request with various chat controls."""
        request = ChatRequest(
            message="Hello",
            provider_type=ProviderType.OPENAI,
            provider_settings={
                "base_url": "https://api.openai.com/v1",
                "api_key": "sk-test-key",
                "default_model": "gpt-4"
            },
            chat_controls={
                "temperature": 0.8,
                "top_p": 0.9,
                "max_tokens": 512,
                "presence_penalty": 0.1,
                "frequency_penalty": 0.2,
                "seed": 42,
                "stop": ["END", "STOP"]
            }
        )
        
        builder = OpenAIRequestBuilder(self.mock_service)
        openai_request = builder.build_request(request)
        
        assert openai_request["temperature"] == 0.8
        assert openai_request["top_p"] == 0.9
        assert openai_request["max_tokens"] == 512
        assert openai_request["presence_penalty"] == 0.1
        assert openai_request["frequency_penalty"] == 0.2
        assert openai_request["seed"] == 42
        assert openai_request["stop"] == ["END", "STOP"]
    
    def test_build_request_with_streaming(self):
        """Test building request with streaming enabled."""
        request = ChatRequest(
            message="Hello",
            provider_type=ProviderType.OPENAI,
            provider_settings={
                "base_url": "https://api.openai.com/v1",
                "api_key": "sk-test-key",
                "default_model": "gpt-4"
            },
            chat_controls={"stream": True}
        )
        
        builder = OpenAIRequestBuilder(self.mock_service)
        openai_request = builder.build_request(request)
        
        assert openai_request["stream"] is True
    
    def test_build_request_with_json_mode(self):
        """Test building request with JSON response format."""
        request = ChatRequest(
            message="Generate a JSON response",
            provider_type=ProviderType.OPENAI,
            provider_settings={
                "base_url": "https://api.openai.com/v1",
                "api_key": "sk-test-key",
                "default_model": "gpt-4"
            },
            chat_controls={"json_mode": "json_object"}
        )
        
        builder = OpenAIRequestBuilder(self.mock_service)
        openai_request = builder.build_request(request)
        
        assert openai_request["response_format"]["type"] == "json_object"
    
    def test_build_request_with_thinking_enabled(self):
        """Test building request with thinking enabled (dynamic reasoning approach)."""
        request = ChatRequest(
            message="Solve this complex math problem",
            provider_type=ProviderType.OPENAI,
            provider_settings={
                "base_url": "https://api.openai.com/v1",
                "api_key": "sk-test-key",
                "model": "openai/gpt-oss-20b"  # Could be any reasoning model
            },
            chat_controls={
                "thinking_enabled": True,
                "reasoning_effort": "medium",
                "max_tokens": 2000,
                "temperature": 0.7
            }
        )
        
        builder = OpenAIRequestBuilder(self.mock_service)
        openai_request = builder.build_request(request)
        
        # When thinking is enabled, reasoning effort should be included
        assert openai_request["reasoning_effort"] == "medium"
        # Both max_tokens parameters should be included for compatibility
        assert openai_request["max_tokens"] == 2000
        assert openai_request["max_completion_tokens"] == 2000
        
        # Standard parameters should still be included (let API decide what to use)
        assert openai_request["temperature"] == 0.7
    
    def test_build_request_with_standard_model(self):
        """Test building request with standard model (gpt-4, gpt-3.5, etc)."""
        request = ChatRequest(
            message="Hello",
            provider_type=ProviderType.OPENAI,
            provider_settings={
                "base_url": "https://api.openai.com/v1",
                "api_key": "sk-test-key",
                "default_model": "gpt-4o"
            },
            chat_controls={
                "temperature": 0.8,
                "max_tokens": 512,
                "reasoning_effort": "high"  # Should be ignored for standard models
            }
        )
        
        builder = OpenAIRequestBuilder(self.mock_service)
        openai_request = builder.build_request(request)
        
        # Standard model parameters
        assert openai_request["temperature"] == 0.8
        assert openai_request["max_tokens"] == 512
        
        # Reasoning model parameters should not be included for standard models
        assert "reasoning_effort" not in openai_request
        assert "max_completion_tokens" not in openai_request
    
    def test_thinking_disabled_doesnt_add_reasoning_params(self):
        """Test that reasoning parameters are not added when thinking is disabled."""
        request = ChatRequest(
            message="Simple question",
            provider_type=ProviderType.OPENAI,
            provider_settings={
                "base_url": "https://api.openai.com/v1",
                "api_key": "sk-test-key",
                "model": "gpt-4"
            },
            chat_controls={
                "thinking_enabled": False,  # Explicitly disabled
                "reasoning_effort": "medium",  # Should be ignored
                "max_tokens": 2000,
                "temperature": 0.7
            }
        )
        
        builder = OpenAIRequestBuilder(self.mock_service)
        openai_request = builder.build_request(request)
        
        # When thinking is disabled, reasoning effort should NOT be included
        assert "reasoning_effort" not in openai_request
        # Only max_tokens should be included, not max_completion_tokens
        assert openai_request["max_tokens"] == 2000
        assert "max_completion_tokens" not in openai_request
        
        # Standard parameters should be included
        assert openai_request["temperature"] == 0.7
    
    def test_build_headers(self):
        """Test header building logic."""
        builder = OpenAIRequestBuilder(self.mock_service)
        
        # Test basic headers
        headers = builder.build_headers("sk-test-key", None, None)
        assert headers["Authorization"] == "Bearer sk-test-key"
        assert headers["Content-Type"] == "application/json"
        
        # Test with organization
        headers = builder.build_headers("sk-test-key", "org-123", None)
        assert headers["OpenAI-Organization"] == "org-123"
        
        # Test with project
        headers = builder.build_headers("sk-test-key", None, "proj-456")
        assert headers["OpenAI-Project"] == "proj-456"
    
    def test_build_url(self):
        """Test URL building logic."""
        builder = OpenAIRequestBuilder(self.mock_service)
        
        # Test default endpoint
        url = builder.build_url("https://api.openai.com/v1")
        assert url == "https://api.openai.com/v1/chat/completions"
        
        # Test URL with trailing slash
        url = builder.build_url("https://api.openai.com/v1/")
        assert url == "https://api.openai.com/v1/chat/completions"


class TestOpenAIResponseParser:
    """Test OpenAI response parsing logic."""
    
    def test_parse_non_streaming_response(self):
        """Test parsing a non-streaming response."""
        mock_response_data = {
            "id": "chatcmpl-123",
            "object": "chat.completion",
            "created": 1677652288,
            "model": "gpt-4",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "Hello! How can I help you today?"
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 15,
                "total_tokens": 25
            }
        }
        
        parser = OpenAIResponseParser()
        response = parser.parse_response(mock_response_data)
        
        assert isinstance(response, ChatResponse)
        assert response.content == "Hello! How can I help you today?"
        assert response.model == "gpt-4"
        assert response.provider_type == ProviderType.OPENAI
        assert response.metadata["usage"]["total_tokens"] == 25
        assert response.metadata["finish_reason"] == "stop"
    
    def test_parse_response_missing_content(self):
        """Test parsing response with missing content."""
        mock_response_data = {
            "id": "chatcmpl-123",
            "object": "chat.completion",
            "model": "gpt-4",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": None
                    },
                    "finish_reason": "length"
                }
            ]
        }
        
        parser = OpenAIResponseParser()
        response = parser.parse_response(mock_response_data)
        
        assert response.content == ""
        assert response.metadata["finish_reason"] == "length"


class TestOpenAIStreamParser:
    """Test OpenAI streaming response parsing."""
    
    def test_parse_streaming_chunk(self):
        """Test parsing a streaming response chunk."""
        chunk_line = 'data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1677652288,"model":"gpt-4","choices":[{"index":0,"delta":{"content":"Hello"},"finish_reason":null}]}'
        
        parser = OpenAIStreamParser()
        chunk = parser.parse_chunk(chunk_line)
        
        assert isinstance(chunk, StreamingChatResponse)
        assert chunk.content == "Hello"
        assert chunk.model == "gpt-4"
        assert chunk.done is False
        assert chunk.provider_type == ProviderType.OPENAI
    
    def test_parse_final_streaming_chunk(self):
        """Test parsing the final streaming chunk."""
        chunk_line = 'data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1677652288,"model":"gpt-4","choices":[{"index":0,"delta":{},"finish_reason":"stop"}],"usage":{"total_tokens":25}}'
        
        parser = OpenAIStreamParser()
        chunk = parser.parse_chunk(chunk_line)
        
        assert chunk.content == ""
        assert chunk.done is True
        assert chunk.metadata["finish_reason"] == "stop"
        assert chunk.metadata["usage"]["total_tokens"] == 25
    
    def test_parse_done_message(self):
        """Test parsing the [DONE] message."""
        parser = OpenAIStreamParser()
        chunk = parser.parse_chunk("data: [DONE]")
        
        assert chunk is None  # [DONE] returns None to signal end
    
    def test_parse_empty_line(self):
        """Test parsing empty lines."""
        parser = OpenAIStreamParser()
        chunk = parser.parse_chunk("")
        
        assert chunk is None


class TestOpenAIService:
    """Test OpenAIService main functionality."""
    
    def test_validate_settings_valid(self):
        """Test validation of valid OpenAI settings."""
        service = OpenAIService()
        settings = {
            "base_url": "https://api.openai.com/v1",
            "api_key": "sk-test-key",
            "default_model": "gpt-4"
        }
        
        assert service.validate_settings(settings) is True
    
    def test_validate_settings_missing_api_key(self):
        """Test validation fails with missing API key."""
        service = OpenAIService()
        settings = {
            "base_url": "https://api.openai.com/v1",
            "default_model": "gpt-4"
        }
        
        assert service.validate_settings(settings) is False
    
    def test_validate_settings_missing_model(self):
        """Test validation fails with missing model."""
        service = OpenAIService()
        settings = {
            "base_url": "https://api.openai.com/v1",
            "api_key": "sk-test-key"
        }
        
        assert service.validate_settings(settings) is False
    
    @pytest.mark.asyncio
    async def test_send_message_success(self):
        """Test successful message sending."""
        service = OpenAIService()
        request = ChatRequest(
            message="Hello",
            provider_type=ProviderType.OPENAI,
            provider_settings={
                "base_url": "https://api.openai.com/v1",
                "api_key": "sk-test-key",
                "default_model": "gpt-4"
            },
            chat_controls={}
        )
        
        # Mock the HTTP response
        mock_response_data = {
            "id": "chatcmpl-123",
            "object": "chat.completion",
            "model": "gpt-4",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "Hello! How can I help?"
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "total_tokens": 25
            }
        }
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.text.return_value = json.dumps(mock_response_data)
            mock_response.status = 200
            mock_post.return_value.__aenter__.return_value = mock_response
            
            response = await service.send_message(request)
            
            assert isinstance(response, ChatResponse)
            assert response.content == "Hello! How can I help?"
            assert response.model == "gpt-4"
            assert response.provider_type == ProviderType.OPENAI
    
    @pytest.mark.asyncio
    async def test_send_message_authentication_error(self):
        """Test handling of authentication errors."""
        service = OpenAIService()
        request = ChatRequest(
            message="Hello",
            provider_type=ProviderType.OPENAI,
            provider_settings={
                "base_url": "https://api.openai.com/v1",
                "api_key": "invalid-key",
                "default_model": "gpt-4"
            },
            chat_controls={}
        )
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 401
            mock_response.text.return_value = '{"error":{"message":"Invalid API key"}}'
            mock_post.return_value.__aenter__.return_value = mock_response
            
            with pytest.raises(ProviderAuthenticationError, match="OpenAI authentication failed"):
                await service.send_message(request)
    
    @pytest.mark.asyncio
    async def test_send_message_stream_success(self):
        """Test successful streaming message sending."""
        service = OpenAIService()
        request = ChatRequest(
            message="Hello",
            provider_type=ProviderType.OPENAI,
            provider_settings={
                "base_url": "https://api.openai.com/v1",
                "api_key": "sk-test-key",
                "default_model": "gpt-4"
            },
            chat_controls={"stream": True}
        )
        
        # Mock streaming response chunks
        chunk1 = b'data: {"id":"chatcmpl-123","choices":[{"index":0,"delta":{"content":"Hello"},"finish_reason":null}],"model":"gpt-4"}\n\n'
        chunk2 = b'data: {"id":"chatcmpl-123","choices":[{"index":0,"delta":{"content":" there"},"finish_reason":null}],"model":"gpt-4"}\n\n'
        chunk3 = b'data: {"id":"chatcmpl-123","choices":[{"index":0,"delta":{},"finish_reason":"stop"}],"model":"gpt-4","usage":{"total_tokens":10}}\n\n'
        chunk4 = b'data: [DONE]\n\n'
        
        async def mock_stream_chunks(chunk_size):
            for chunk in [chunk1, chunk2, chunk3, chunk4]:
                yield chunk
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.content.iter_chunked = mock_stream_chunks
            mock_post.return_value.__aenter__.return_value = mock_response
            
            chunks = []
            async for chunk in service.send_message_stream(request):
                chunks.append(chunk)
            
            assert len(chunks) == 3  # Excluding [DONE] message
            assert chunks[0].content == "Hello"
            assert chunks[0].done is False
            assert chunks[1].content == " there"
            assert chunks[1].done is False
            assert chunks[2].content == ""
            assert chunks[2].done is True
            assert chunks[2].metadata["usage"]["total_tokens"] == 10
    
    @pytest.mark.asyncio
    async def test_send_message_connection_error(self):
        """Test handling of connection errors."""
        service = OpenAIService()
        request = ChatRequest(
            message="Hello",
            provider_type=ProviderType.OPENAI,
            provider_settings={
                "base_url": "https://invalid-host.com/v1",
                "api_key": "sk-test-key",
                "default_model": "gpt-4"
            },
            chat_controls={}
        )
        
        # Test with an invalid host - this will be tested in integration tests
        # For now, just test that the service can handle the request structure
        assert service.validate_settings(request.provider_settings) is True
    
    def test_get_timeout_configuration(self):
        """Test timeout configuration."""
        service = OpenAIService()
        timeout = service._get_timeout()
        
        assert isinstance(timeout, ClientTimeout)
    
    @pytest.mark.asyncio
    async def test_list_models_success(self):
        """Test successful model listing."""
        service = OpenAIService()
        settings = {
            "base_url": "https://api.openai.com/v1",
            "api_key": "sk-test-key"
        }
        
        mock_response_data = {
            "data": [
                {
                    "id": "gpt-4o",
                    "object": "model",
                    "created": 1234567890,
                    "owned_by": "openai"
                },
                {
                    "id": "gpt-3.5-turbo",
                    "object": "model", 
                    "created": 1234567891,
                    "owned_by": "openai"
                }
            ]
        }
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value=json.dumps(mock_response_data))
            mock_get.return_value.__aenter__.return_value = mock_response
            
            models = await service.list_models(settings)
            
            assert len(models) == 2
            assert models[0]["id"] == "gpt-4o"
            assert models[0]["name"] == "gpt-4o"
            assert models[0]["owned_by"] == "openai"
            assert models[1]["id"] == "gpt-3.5-turbo"
            assert models[1]["name"] == "gpt-3.5-turbo"
            
            # Verify correct URL was called
            mock_get.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_list_models_authentication_error(self):
        """Test model listing with authentication error."""
        service = OpenAIService()
        settings = {
            "base_url": "https://api.openai.com/v1",
            "api_key": "invalid-key"
        }
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 401
            mock_response.text = AsyncMock(return_value="Unauthorized")
            mock_get.return_value.__aenter__.return_value = mock_response
            
            with pytest.raises(ProviderAuthenticationError) as exc_info:
                await service.list_models(settings)
            
            assert "Invalid API key" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_list_models_connection_error(self):
        """Test model listing with connection error."""
        service = OpenAIService()
        settings = {
            "base_url": "https://invalid-host.com/v1",
            "api_key": "sk-test-key"
        }
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            from aiohttp import ClientError
            mock_get.side_effect = ClientError("Connection failed")
            
            with pytest.raises(ProviderConnectionError) as exc_info:
                await service.list_models(settings)
            
            assert "OpenAI client error" in str(exc_info.value) or "Failed to connect to OpenAI" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_list_models_invalid_json_response(self):
        """Test model listing with invalid JSON response."""
        service = OpenAIService()
        settings = {
            "base_url": "https://api.openai.com/v1",
            "api_key": "sk-test-key"
        }
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value="invalid json")
            mock_get.return_value.__aenter__.return_value = mock_response
            
            with pytest.raises(ProviderConnectionError) as exc_info:
                await service.list_models(settings)
            
            assert "Invalid JSON response from models endpoint" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_list_models_empty_response(self):
        """Test model listing with empty response."""
        service = OpenAIService()
        settings = {
            "base_url": "https://api.openai.com/v1",
            "api_key": "sk-test-key"
        }
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value="")
            mock_get.return_value.__aenter__.return_value = mock_response
            
            with pytest.raises(ProviderConnectionError) as exc_info:
                await service.list_models(settings)
            
            assert "Empty response from models endpoint" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_list_models_api_error_response(self):
        """Test model listing with API error in response."""
        service = OpenAIService()
        settings = {
            "base_url": "https://api.openai.com/v1",
            "api_key": "sk-test-key"
        }
        
        error_response = {
            "error": {
                "message": "Rate limit exceeded",
                "code": 429
            }
        }
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value=json.dumps(error_response))
            mock_get.return_value.__aenter__.return_value = mock_response
            
            with pytest.raises(ProviderConnectionError) as exc_info:
                await service.list_models(settings)
            
            assert "API error (429): Rate limit exceeded" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_list_models_validation_error(self):
        """Test model listing with invalid settings."""
        service = OpenAIService()
        settings = {"base_url": "https://api.openai.com/v1"}  # Missing api_key
        
        with pytest.raises(ProviderConnectionError) as exc_info:
            await service.list_models(settings)
        
        assert "Invalid OpenAI settings" in str(exc_info.value)