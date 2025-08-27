# CLAUDE.md

## 🎯 Project Vision: Project 2501 - Cognitive Systems Framework

**Core Innovation**: Dynamic System Prompt Architecture - treats system prompts as living, modular heads-up displays that stay visible throughout conversations, solving static prompt limitations and context rot.

### Key Features:
- **Simple Modules**: Static text templates 
- **Advanced Modules**: Python scripts with dynamic content generation
- **Self-Reflecting AI**: AI introspection via `ctx.reflect()`
- **Template System**: `@module_name` references and `${variable}` outputs

## 📐 Architecture (3-Layer)
```
Frontend (Vue 3) ←→ Backend (FastAPI) ←→ Database (PostgreSQL + pgvector)
```

**Stack**:
- **Frontend**: Vue 3.5.18, TypeScript, Pinia, Vite
- **Backend**: FastAPI 0.104.1, SQLAlchemy 2.0.23, RestrictedPython 7.0
- **Database**: PostgreSQL with pgvector, UUID primary keys

## 📁 Project Structure
```
project-2501/
├── frontend/         # Vue 3 app (components, stores, types)
├── backend/          # FastAPI backend
│   ├── app/core/    # Script engine, plugins, validation
│   ├── app/models/  # Database models (Persona, Module, Conversation)
│   ├── app/api/     # REST endpoints
│   └── tests/       # 461 tests (unit + integration)
├── database/        # PostgreSQL setup
└── scripts/         # Development scripts
```

## 🛠️ Development Setup

### Backend
```bash
./scripts/install_BE.sh
conda activate project2501
./scripts/run_BE.sh

# Testing (461 tests)
source /home/q/miniforge3/etc/profile.d/conda.sh && conda activate project2501 && pytest -v
```

### Frontend
```bash
cd frontend
npm run dev        # localhost:5173
npm run build
npm run lint
```

### Database
- **Main**: project2501 (project2501 user)
- **Test**: project2501_test 
- **Models**: Persona, Module, Conversation, Message (UUIDs)

## 💡 Core API Endpoints

```
Chat:          POST /api/chat/send          # Complete response
               POST /api/chat/stream        # Streaming response
Templates:     POST /api/templates/resolve  # Resolve @module_name references
Conversations: GET  /api/conversations/by-persona/{id}
Messages:      GET  /api/messages/by-conversation/{id}
Modules:       GET  /api/modules/
Personas:      GET  /api/personas/
```

## 🚨 Development Principles

### Search Before Code
```bash
# Always search first to avoid reimplementation
grep -r "feature_name" backend/ frontend/
find . -name "*.py" -o -name "*.vue" | xargs grep -l "keyword"
```

### Architecture Guidelines
- **3-Layer**: Frontend ↔ Backend ↔ Database 
- **Modularity**: Single responsibility, loose coupling
- **Settings Storage**: Frontend localStorage only (no backend duplication)
- **Testing**: 461/461 tests passing - maintain TDD approach

## ⚡ Workflow

### Before Committing
```bash
# Backend
cd backend && pytest && python app/main.py

# Frontend  
cd frontend && npm run lint && npm run format
```

### Frontend-First Development
1. Design UI components first
2. Define API contracts based on frontend needs
3. Write tests
4. Implement backend endpoints
5. Integration testing

## ✅ Implementation Status

### Complete Features
- **Full Chat System**: Ollama/OpenAI streaming with persona integration
- **Advanced Modules**: Python scripts with RestrictedPython sandbox + 15+ plugins  
- **Self-Reflecting AI**: `ctx.reflect()` for AI introspection
- **Module System**: `@module_name` and `${variable}` resolution
- **Conversation Persistence**: Full CRUD with message editing/thinking
- **Test Coverage**: 461/461 tests passing

### Chat System Architecture
**Settings**: Frontend localStorage only (no backend storage)
**Request Format**: All settings passed in request payload
**Providers**: Ollama + OpenAI with streaming support
**Personas**: System prompt resolution with module integration

**LocalStorage Keys**:
- `chat-controls`: Temperature, tokens, provider selection
- `ollama-connection`: Host, model, options
- `openai-connection`: API key, model, base URL


### Chat Request Format
```json
{
  "message": "Hello!",
  "provider": "ollama" | "openai",
  "persona_id": "uuid-string",
  "provider_settings": { "host": "...", "model": "..." },
  "chat_controls": { "temperature": 0.7, "max_tokens": 1024 }
}
```


### Database Models
**Persona**: AI persona configurations with templates
**Module**: Simple (static) and Advanced (Python script) modules
**Conversation**: UUID primary key, persona relationship, provider info
**Message**: Content, thinking, token counts, cascade deletion

### Advanced Modules
**Plugin Functions**: 15+ built-in functions (time, conversation, utilities)
**Script Execution**: RestrictedPython sandbox with trigger patterns  
**Variable System**: `${variable}` for dynamic script outputs
**Timing Options**: BEFORE, AFTER, CUSTOM execution modes

### Plugin Examples
```python
# Time functions
ctx.get_current_time("%H:%M")
ctx.get_relative_time("2 hours ago")

# Conversation functions  
ctx.get_message_count()
ctx.get_recent_messages(5)

# AI reflection
ctx.reflect("Rate this response quality 1-10")
```

## 🚀 Next Priorities
- **Refactor streaming state management** - Current implementation uses overlapping boolean flags that create complex timing dependencies:
  - **Current state**: `isStreaming`, `isProcessingAfter`, `messageCompleted`, `hideStreamingUI`, `processingStage`, plus content variables
  - **Issues**: Race conditions, order-dependent flag setting, template conditions that require multiple boolean checks
  - **Target**: Single `streamingState` enum (`THINKING_BEFORE`, `GENERATING`, `MESSAGE_COMPLETE`, `THINKING_AFTER`, `IDLE`) with clear transitions
  - **Benefits**: Predictable state transitions, simpler template conditions, easier debugging, no timing races
- Template editor with @module autocomplete
- Debug screen for resolved system prompts
- Import/export system for personas
- Advanced chat features (file uploads, tools)
- Module marketplace



