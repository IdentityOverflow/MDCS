# API Layer

The API layer provides RESTful endpoints for all Project 2501 functionality. Built with FastAPI, it handles HTTP requests, validation, and coordinates between frontend and backend services.

## 📁 Files Overview

### Core Endpoints

#### [chat.py](chat.py)
**FastAPI chat endpoints**

Provides the main chat interface with streaming and non-streaming responses:
- `POST /api/chat/send` - Complete chat response with cancellation
- `POST /api/chat/stream` - Server-sent events streaming with cancellation
- `POST /api/chat/cancel/{session_id}` - Cancel active chat session
- `GET /api/chat/status/{session_id}` - Check session status
- `GET /api/chat/sessions/active` - List active sessions

**Key Features:**
- Provider integration (Ollama/OpenAI)
- System prompt resolution with module execution (Stages 1 & 2)
- POST_RESPONSE module execution (Stages 4 & 5)
- Streaming to non-streaming conversion for cancellation
- ConversationState management
- Session-based cancellation support

**Flow:**
1. Generate session ID (client-provided or auto-generated)
2. Register session for cancellation
3. Resolve system prompt (execute Stage 1 & 2 modules)
4. Call AI provider (Stage 3)
5. Execute POST_RESPONSE modules (Stages 4 & 5)
6. Cleanup session

---

#### [chat_models.py](chat_models.py)
**Pydantic models for chat API**

Request/response validation models:
- `ChatSendRequest` - Chat message with provider settings
- `ChatSendResponse` - Complete response with metadata
- `StreamingChatResponse` - SSE streaming chunks
- `ChatError` - Error handling
- `ProcessingStage` - Stage tracking enum
- `DebugData` - Debug information

---

#### [personas.py](personas.py)
**Persona CRUD endpoints**

Manages AI persona configurations:
- `POST /api/personas` - Create new persona
- `GET /api/personas` - List personas (with filtering)
- `GET /api/personas/{persona_id}` - Get persona details
- `PUT /api/personas/{persona_id}` - Update persona
- `DELETE /api/personas/{persona_id}` - Delete persona
- `POST /api/personas/upload-image` - Upload persona image

**Features:**
- Mode validation (reactive/autonomous)
- Template storage for system prompts
- Image upload with UUID filenames
- Active/inactive filtering

---

#### [modules.py](modules.py)
**Module CRUD endpoints**

Manages simple and advanced cognitive modules:
- `POST /api/modules` - Create module
- `GET /api/modules` - List modules (with filtering)
- `GET /api/modules/{module_id}` - Get module
- `PUT /api/modules/{module_id}` - Update module
- `DELETE /api/modules/{module_id}` - Delete module
- `GET /api/modules/plugin-functions` - List available plugin functions
- `POST /api/modules/test-script` - Test advanced module script

**Features:**
- Automatic script analysis for AI dependencies
- Plugin function introspection
- Script testing sandbox
- ExecutionContext management
- ConversationState cleanup on deletion

---

#### [conversations.py](conversations.py)
**Conversation CRUD endpoints**

Manages chat conversation lifecycle:
- `POST /api/conversations` - Create conversation
- `GET /api/conversations/{conversation_id}` - Get conversation
- `GET /api/conversations/by-persona/{persona_id}` - Get persona conversation
- `PUT /api/conversations/{conversation_id}` - Update conversation
- `DELETE /api/conversations/{conversation_id}` - Delete conversation
- `DELETE /api/conversations/{conversation_id}/memories` - Clear memories

**Features:**
- Persona relationship validation
- Provider config storage
- Cascade deletion of messages
- Memory management

---

#### [messages.py](messages.py)
**Message CRUD endpoints**

Manages individual messages within conversations:
- `POST /api/messages` - Create message
- `GET /api/messages/{message_id}` - Get message
- `GET /api/messages/by-conversation/{conversation_id}` - List messages
- `PUT /api/messages/{message_id}` - Update message
- `DELETE /api/messages/{message_id}` - Delete message

**Features:**
- Role validation (user/assistant/system)
- Thinking content support
- Token count tracking
- Extra metadata storage

---

#### [templates.py](templates.py)
**Template resolution endpoint**

Provides template resolution for testing:
- `POST /api/templates/resolve` - Resolve template with modules

**Features:**
- Module reference resolution (`@module_name`)
- Variable substitution (`${variable}`)
- Advanced module execution
- Trigger pattern matching

---

### Supporting Files

#### [connections.py](connections.py)
**Connection management endpoints** (if used)

Provider connection testing and validation.

---

#### [database.py](database.py)
**Database utility endpoints** (if used)

Database health checks and status.

---

#### [__init__.py](__init__.py)
**API package initialization**

Router registration and module exports.

---

## 🏗️ Architecture Patterns

### Request Flow
```
Client Request → FastAPI Router → Pydantic Validation → Service Layer → Database → Response
```

### Dependency Injection
```python
def endpoint(
    request: ChatSendRequest,
    db: Session = Depends(get_db),
    session_manager: ChatSessionManager = Depends(get_chat_session_manager)
):
    # Endpoint logic
```

### Error Handling
- `HTTPException` for client errors (400, 404, 422)
- Structured error responses with `ChatError`
- Database rollback on failures
- Cancellation handling for async operations

---

## 🔄 Chat Cancellation System

The chat endpoints implement a sophisticated cancellation system:

### Session Management
1. **Registration**: Each request gets unique session ID
2. **Tracking**: Session stored in `ChatSessionManager`
3. **Cancellation**: Stop button triggers `/cancel/{session_id}`
4. **Cleanup**: Automatic cleanup on completion/cancellation

### Cancellation Points
- System prompt resolution (Stages 1 & 2)
- AI provider streaming (Stage 3)
- POST_RESPONSE modules (Stages 4 & 5)

### Consecutive Messages
- New message auto-cancels current session
- Immediate responsiveness
- No queuing or blocking

---

## 📊 API Response Patterns

### Success Response
```json
{
  "content": "AI response",
  "metadata": {...},
  "response_time": 1.23
}
```

### Streaming Response
```
data: {"event_type": "content", "content": "chunk", "done": false}
data: {"event_type": "content", "content": "", "done": true}
```

### Error Response
```json
{
  "error_type": "provider_error",
  "message": "Connection failed",
  "details": {...}
}
```

---

## 🧪 Testing Endpoints

### Script Testing
```bash
curl -X POST http://localhost:8000/api/modules/test-script \
  -H "Content-Type: application/json" \
  -d '{"script": "ctx.set_output(\"greeting\", \"Hello!\")"}'
```

### Plugin Functions
```bash
curl http://localhost:8000/api/modules/plugin-functions
```

---

## 🔐 Validation

All endpoints use Pydantic models for:
- Request validation
- Response serialization
- Type safety
- Automatic OpenAPI documentation

---

## 📝 Notes

- All UUIDs are validated before database queries
- Database sessions use dependency injection
- Logging throughout for debugging
- CORS configured in main.py
- All endpoints support OpenAPI/Swagger UI
