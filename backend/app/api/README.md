# API Layer

The API layer provides RESTful endpoints for all Project 2501 functionality. Built with FastAPI, it handles HTTP requests, validation, and coordinates between frontend and backend services.

## 📁 Files Overview

### Core Endpoints

#### [websocket_chat.py](websocket_chat.py)
**WebSocket chat endpoint**

Provides real-time chat with bidirectional communication:
- `WS /ws/chat` - WebSocket endpoint for chat with cancellation support

**Message Types (Client → Server):**
- `chat` - Send message with provider settings
- `cancel` - Cancel active chat session
- `ping` - Heartbeat

**Message Types (Server → Client):**
- `session_start` - WebSocket session established
- `chat_session_start` - Chat message processing started
- `stage_update` - Module execution stage updates
- `chunk` - Streaming content chunks
- `done` - Main response complete
- `post_response_complete` - POST_RESPONSE modules complete
- `cancelled` - Session cancelled
- `error` - Error occurred
- `pong` - Heartbeat response

**Key Features:**
- Real-time bidirectional communication
- <100ms cancellation latency
- Stage-aware execution tracking
- Thread pool execution (prevents event loop blocking)
- Provider integration (Ollama/OpenAI)
- System prompt resolution (Stages 1 & 2)
- POST_RESPONSE module execution (Stages 4 & 5)

**Flow:**
1. Client connects to WebSocket
2. Server sends session_start with WebSocket session ID
3. Client sends chat message
4. Server sends chat_session_start with chat session ID
5. Server executes stages and streams chunks
6. Server sends done and post_response_complete
7. Client can cancel anytime with cancel message

---

#### [chat_models.py](chat_models.py)
**Pydantic models for chat**

Request/response validation models:
- `ChatSendRequest` - Chat message with provider settings
- `ChatSendResponse` - Complete response with metadata
- `ProcessingStage` - Stage tracking enum
- `DebugData` - Debug information
- Various WebSocket message models

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

## 🔄 WebSocket Chat & Cancellation

### Session Management
1. **WebSocket Session**: Connection-level session (one per browser tab)
2. **Chat Session**: Message-level session (unique per user message)
3. **Cancellation Token**: Shared state for cancellation detection

### Cancellation Flow
1. Client sends `cancel` message with chat_session_id
2. Server sets cancellation token
3. All stages check token periodically
4. Processing stops within <100ms
5. Server sends `cancelled` message

### Cancellation Points
- Stage 1-2: System prompt resolution
- Stage 3: AI provider streaming
- Stage 4-5: POST_RESPONSE modules

### Consecutive Messages
- New message auto-cancels current session
- Immediate responsiveness
- No blocking

---

## 📊 WebSocket Message Examples

### Chat Request
```json
{
  "type": "chat",
  "data": {
    "message": "Hello!",
    "provider": "ollama",
    "persona_id": "uuid",
    "conversation_id": "uuid",
    "provider_settings": {...},
    "chat_controls": {...}
  }
}
```

### Streaming Chunk
```json
{
  "type": "chunk",
  "data": {
    "content": "AI response chunk",
    "thinking": null,
    "done": false
  }
}
```

### Cancellation
```json
{
  "type": "cancel",
  "session_id": "chat-session-id"
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
