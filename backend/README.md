# Project 2501 Backend

A FastAPI-based backend service for the Project 2501 Cognitive Systems Framework, providing AI provider integration, staged module execution, conversation management, and advanced cognitive capabilities.

## 🏗️ Architecture

The backend follows a clean, modular architecture with complete staged execution pipeline:

```
backend/
├── app/
│   ├── api/                    # API route handlers
│   │   ├── chat.py             # Chat endpoints (streaming & non-streaming)
│   │   ├── conversations.py    # Conversation management
│   │   ├── messages.py         # Message operations
│   │   ├── personas.py         # AI persona management
│   │   ├── modules.py          # Cognitive module management
│   │   ├── templates.py        # Template resolution API
│   │   ├── connections.py      # Database connections
│   │   └── database.py         # Database utilities
│   ├── core/                   # Core engine components
│   │   ├── config.py           # Environment configuration
│   │   ├── script_engine.py    # RestrictedPython script execution
│   │   ├── script_context.py   # Execution context for modules
│   │   ├── script_analyzer.py  # AI dependency analysis
│   │   └── trigger_matcher.py  # Module trigger patterns
│   ├── services/               # Business logic services
│   │   ├── staged_module_resolver.py  # 5-Stage execution pipeline
│   │   ├── ai_providers.py     # AI provider abstraction
│   │   ├── ollama_service.py   # Ollama integration
│   │   └── openai_service.py   # OpenAI integration
│   ├── plugins/                # Plugin system for advanced modules
│   │   ├── ai_plugins.py       # AI generation & reflection
│   │   ├── conversation_plugins.py  # Conversation utilities
│   │   ├── time_plugins.py     # Time-based functions
│   │   └── core_plugins.py     # Core utility functions
│   ├── models/                 # Database models
│   │   ├── base.py             # Base model with UUID & timestamps
│   │   ├── conversation.py     # Conversation & Message models
│   │   ├── conversation_state.py  # Staged execution state
│   │   ├── persona.py          # AI persona configurations
│   │   └── module.py           # Cognitive modules with ExecutionContext
│   ├── database/               # Database management
│   │   ├── connection.py       # SQLAlchemy connection
│   │   └── migrations/         # Database schema migrations
│   └── main.py                 # FastAPI application entry point
├── tests/                      # Comprehensive test suite (501 tests)
│   ├── unit/                   # Unit tests (24 test files)
│   ├── integration/            # Integration tests (10 test files)
│   ├── conftest.py             # Test configuration
│   └── fixtures/               # Test fixtures
└── static/images/personas/     # Persona image storage
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- PostgreSQL database (with pgvector extension)
- Conda (Miniconda/Anaconda/Miniforge)

### Installation

1. **Run the installation script:**
   ```bash
   ./scripts/install_BE.sh
   ```

2. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials
   ```

3. **Start the server:**
   ```bash
   ./scripts/run_BE.sh
   ```

The backend will be available at:
- **API**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **OpenAPI Schema**: http://localhost:8000/openapi.json

## ⚙️ Configuration

The backend uses environment-based configuration via `.env` file:

### Required Environment Variables

```bash
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=project2501
DB_USER=your_username
DB_PASSWORD=your_password

# Application Configuration (Optional)
APP_NAME=Project 2501 Backend
DEBUG=false
```

## 🧠 Cognitive Systems Framework

### 5-Stage Execution Pipeline

The backend implements a sophisticated staged execution system replacing the old timing-based approach:

- **Stage 1**: Template preparation (Simple + IMMEDIATE Non-AI + Previous POST_RESPONSE)
- **Stage 2**: Pre-response AI processing (IMMEDIATE modules with AI inference)
- **Stage 3**: Main AI response generation (handled by chat system)
- **Stage 4**: Post-response processing (POST_RESPONSE modules without AI)
- **Stage 5**: Post-response AI analysis (POST_RESPONSE modules with AI reflection)

### SystemPromptState Tracking

The backend provides complete visibility into system prompt evolution through the **SystemPromptState** tracking system:

#### **Features**
- **Complete Execution Visibility**: Track how system prompts transform through each stage
- **Performance Analysis**: Stage timing, bottleneck identification, AI vs non-AI metrics
- **Debug Capabilities**: Full prompt evolution, execution metadata, warnings tracking
- **Optional Enhancement**: Zero performance overhead when disabled

#### **Architecture**
```python
# Enable state tracking
resolver = StagedModuleResolver()
resolver.enable_state_tracking()

# Execute with tracking
result = resolver.resolve_template_stage1_and_stage2(template, ...)

# Get insights
debug_summary = resolver.get_debug_summary()
performance = resolver.get_performance_summary()
current_state = resolver.get_current_state()
```

#### **State Evolution Tracking**
- **Original Template**: Initial persona template with @module_name references
- **Stage 1 Resolved**: After simple modules and immediate non-AI processing
- **Stage 2 Resolved**: After immediate AI module processing (main AI prompt)
- **Stage 4 Context**: POST_RESPONSE non-AI module variables
- **Stage 5 Context**: POST_RESPONSE AI analysis results

#### **Performance Metrics**
- **Stage Timings**: Execution time per stage for bottleneck identification
- **AI vs Non-AI Time**: Performance analysis of different module types
- **Total Execution Time**: Complete pipeline timing
- **Slowest/Fastest Stages**: Performance optimization insights

#### **Debug Information**
```json
{
  "prompt_evolution": {
    "original": "You are an AI assistant. @greeting @context",
    "stage1": "You are an AI assistant. Hello! Current time context",
    "stage2": "You are an AI assistant. Hello! Enhanced context with AI",
    "main_ai": "You are an AI assistant. Hello! Enhanced context with AI"
  },
  "performance_metrics": {
    "total_time": 0.25,
    "slowest_stage": 2,
    "ai_stages_time": 0.20,
    "non_ai_stages_time": 0.05
  }
}
```

#### **Loose Coupling Architecture**
- **Pure Observability**: SystemPromptState only tracks, never influences execution
- **Optional Feature**: Can be enabled/disabled without affecting functionality
- **No Performance Overhead**: Zero impact when tracking is disabled
- **Clean Separation**: Execution and tracking concerns are completely separate

### Execution Contexts

Modules are classified by execution context:
- **IMMEDIATE**: Execute during template resolution (Stages 1-2)
- **POST_RESPONSE**: Execute after AI response (Stages 4-5)
- **ON_DEMAND**: Execute only when explicitly triggered

### AI Dependency Detection

Advanced modules are automatically analyzed for AI dependencies:
- **Script Analysis**: Detects `ctx.reflect()`, `ctx.generate()` calls
- **Stage Classification**: AI-dependent modules scheduled appropriately
- **Performance Optimization**: Non-AI modules execute without delays

## 🗄️ Database Models

### Base Model
All models inherit from `Base` which provides:
- `id`: UUID primary key
- `created_at`: Automatic timestamp
- `updated_at`: Automatic timestamp
- `to_dict()`: Serialization method

### Core Models

#### Conversation
Represents chat sessions between users and AI personas.
```python
class Conversation(Base):
    title: str
    persona_id: UUID  # Associated persona
    provider_type: str  # "openai", "ollama", etc.
    provider_config: dict  # Provider configuration snapshot
    messages: List[Message]  # Related messages
```

#### Message  
Individual messages within conversations with thinking support.
```python
class Message(Base):
    conversation_id: UUID
    role: MessageRole  # USER, ASSISTANT, SYSTEM
    content: str
    thinking: str  # AI thinking process (optional)
    input_tokens: int  # Token usage tracking
    output_tokens: int
    extra_data: dict  # Additional message metadata
```

#### Persona
AI persona configurations with dynamic templates.
```python
class Persona(Base):
    name: str
    description: str
    template: str  # System prompt with @module_name references
    mode: str  # "reactive" or "autonomous"
    loop_frequency: str  # For autonomous mode
    first_message: str
    image_path: str
    is_active: bool
```

#### Module
Cognitive system modules with staged execution.
```python
class Module(Base):
    name: str
    description: str
    content: str  # Static content or template with ${variables}
    type: ModuleType  # SIMPLE or ADVANCED
    script: str  # Python script for advanced modules
    trigger_pattern: str  # Activation pattern (regex/keywords)
    execution_context: ExecutionContext  # IMMEDIATE, POST_RESPONSE, ON_DEMAND
    requires_ai_inference: bool  # Auto-detected from script
    script_analysis_metadata: dict  # Analysis results
    is_active: bool
```

#### ConversationState
Stores module execution state between conversations.
```python
class ConversationState(Base):
    conversation_id: UUID
    module_id: UUID
    execution_stage: str  # "stage4" or "stage5"
    variables: dict  # Script output variables
    execution_metadata: dict  # Success, timing, errors
    executed_at: datetime
```

## 🛠️ API Endpoints

### Chat System
- **POST /api/chat/send** - Complete chat response
- **POST /api/chat/stream** - Streaming chat response with SSE
  ```json
  {
    "message": "Hello!",
    "provider": "ollama",
    "persona_id": "uuid-string",
    "provider_settings": {"host": "localhost:11434", "model": "llama3.2"},
    "chat_controls": {"temperature": 0.7, "max_tokens": 1024}
  }
  ```

### Conversation Management
- **GET /api/conversations/by-persona/{persona_id}** - Get conversations for persona
- **POST /api/conversations** - Create new conversation
- **PUT /api/conversations/{id}** - Update conversation
- **DELETE /api/conversations/{id}** - Delete conversation

### Message Operations
- **GET /api/messages/by-conversation/{conversation_id}** - Get conversation messages
- **POST /api/messages** - Create message
- **PUT /api/messages/{id}** - Update message (with thinking)
- **DELETE /api/messages/{id}** - Delete message

### Persona Management
- **GET /api/personas** - List all personas
- **POST /api/personas** - Create persona
- **PUT /api/personas/{id}** - Update persona
- **DELETE /api/personas/{id}** - Delete persona

### Module Management
- **GET /api/modules** - List all modules
- **POST /api/modules** - Create module (with automatic script analysis)
- **PUT /api/modules/{id}** - Update module
- **DELETE /api/modules/{id}** - Delete module

### Template Resolution
- **POST /api/templates/resolve** - Resolve @module_name references
  ```json
  {
    "template": "You are an AI assistant. @greeting @context_module",
    "persona_id": "optional-uuid"
  }
  ```

### Database Utilities
- **GET /api/database/test** - Test database connection
- **GET /api/database/info** - Database information and table list

## 🔌 AI Provider Integration

### Supported Providers
- **Ollama**: Local LLM hosting with streaming support
- **OpenAI**: GPT models with streaming and function calling

### Provider Configuration
Settings are passed with each request (no backend storage):
```json
{
  "ollama": {
    "host": "localhost:11434",
    "model": "llama3.2:latest",
    "options": {"temperature": 0.7}
  },
  "openai": {
    "api_key": "sk-...",
    "model": "gpt-4",
    "base_url": "https://api.openai.com/v1"
  }
}
```

## 🧩 Plugin System

### Available Plugins (15+ functions)

#### AI Generation Plugins (State-Aware)
- `ctx.reflect()` - AI-powered self-reflection with SystemPromptState integration
- `ctx.generate()` - Custom AI generation with flexible parameters

**State-Aware Intelligence**: When SystemPromptState tracking is enabled, AI plugins automatically receive stage-appropriate system prompts and context, enabling sophisticated self-reflection and adaptive behavior without coupling to the core execution system.

#### Conversation Plugins  
- `ctx.get_recent_messages()` - Retrieve conversation history
- `ctx.get_message_count()` - Get total message count
- `ctx.get_conversation_summary()` - Generate conversation summaries

#### Time Plugins
- `ctx.get_current_time()` - Current time with formatting
- `ctx.get_relative_time()` - Parse relative time expressions

#### Utility Plugins
- `ctx.log()` - Enhanced logging with context
- `ctx.set_variable()` / `ctx.get_variable()` - Variable management

### Plugin Security
- **RestrictedPython**: Sandboxed execution environment
- **Import Restrictions**: Only allowed modules accessible
- **Execution Timeouts**: Prevents infinite loops
- **Reflection Safety**: Prevents nested AI generation loops

## 🧪 Testing

### Test Coverage: 525 Tests (100% Passing)

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test categories
pytest tests/unit/test_staged_module_resolver.py -v
pytest tests/integration/test_chat_api.py -v

# Run with coverage
pytest --cov=app --cov-report=html
```

### Test Structure
- **Unit Tests** (24 files): Individual component testing
- **Integration Tests** (10 files): Full workflow testing  
- **Fixtures**: Database setup, test data, mocking utilities

### Key Test Areas
- Staged module execution pipeline (30+ tests)
- SystemPromptState tracking and integration (25 tests)
- AI provider integration (25+ tests)
- Chat API functionality (14 tests)
- Database operations (50+ tests)
- Plugin system security (15+ tests)
- Template resolution (12 tests)

## 🔧 Development

### Code Quality Tools
```bash
pip install -r requirements-dev.txt
pytest --cov=app  # Coverage analysis
```

### Database Management
- **Automatic Schema Creation**: Models create tables on startup
- **Migration System**: 6 migrations implemented (UUID conversion, staged execution)
- **Connection Pooling**: SQLAlchemy session management

### Performance Considerations
- **Connection Pooling**: Efficient database connections
- **Staged Execution**: Optimized module processing order
- **Streaming Responses**: Server-Sent Events for real-time chat
- **Lazy Loading**: On-demand module and persona loading

## 🚢 Deployment

### Production Configuration
```bash
DEBUG=false
DB_HOST=your_production_host
DB_SSL_MODE=require
# Configure for production database
```

### Production Server
```bash
# Install production dependencies
pip install gunicorn uvicorn[standard]

# Run with Gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --host 0.0.0.0 --port 8000
```

### Docker Support
```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "app.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker"]
```

## 📋 Implementation Status

### ✅ Completed Features (Production Ready)

- [x] **Complete FastAPI application** with 525 passing tests
- [x] **5-Stage Execution Pipeline** replacing legacy timing system
- [x] **ExecutionContext System** (IMMEDIATE, POST_RESPONSE, ON_DEMAND)
- [x] **Dual AI Provider Support** (Ollama + OpenAI with streaming)
- [x] **Advanced Module System** with RestrictedPython sandboxing
- [x] **Plugin Architecture** with 15+ built-in functions
- [x] **Self-Reflecting AI** via `ctx.reflect()` capability  
- [x] **Conversation Management** with full CRUD operations
- [x] **Template Resolution** with @module_name references
- [x] **Database Models** with UUID primary keys and relationships
- [x] **ConversationState Management** for persistent module variables
- [x] **Comprehensive API** with streaming chat support
- [x] **Script Analysis Engine** with automatic AI dependency detection
- [x] **SystemPromptState Tracking** with complete execution visibility and performance analysis
- [x] **State-Aware AI Plugins** for sophisticated self-reflection and adaptive behavior
- [x] **Frontend Integration** with CORS and localStorage compatibility

### 🔄 Future Enhancements

- [ ] **Authentication System** with JWT tokens
- [ ] **File Upload Support** for documents and images  
- [ ] **WebSocket Support** for real-time bidirectional communication
- [ ] **Module Marketplace** for sharing cognitive modules
- [ ] **Advanced Analytics** for conversation and module performance
- [ ] **Multi-tenant Support** with user isolation
- [ ] **Caching Layer** with Redis for improved performance
- [ ] **Rate Limiting** for API endpoints
- [ ] **Audit Logging** for security and compliance

## 🔗 Frontend Integration

### CORS Configuration
- Supports `localhost:5173` (Vite dev server)
- Configurable origins for production deployment

### State Management
- **Stateless Architecture**: All settings passed with requests
- **LocalStorage Integration**: Frontend manages provider configurations
- **Real-time Updates**: Server-Sent Events for streaming responses

### API Response Format
```json
{
  "content": "AI response content",
  "thinking": "Internal AI reasoning (optional)",
  "token_usage": {"input": 150, "output": 75},
  "debug_data": {
    "provider_request": "...",
    "provider_response": "...",
    "execution_stages": [1, 2, 4, 5]
  }
}
```

### SystemPromptState Integration Example
```python
# Backend usage example
from app.services.staged_module_resolver import StagedModuleResolver

# Enable state tracking
resolver = StagedModuleResolver()
resolver.enable_state_tracking()

# Execute with complete visibility
result = resolver.resolve_template_stage1_and_stage2(
    template="You are @personality. @current_context",
    conversation_id="123",
    persona_id="456"
)

# Get comprehensive insights
debug_info = resolver.get_debug_summary()
performance = resolver.get_performance_summary()

print(f"Total execution time: {performance['total_time']:.3f}s")
print(f"Slowest stage: {performance['slowest_stage']}")
print(f"AI processing time: {performance['ai_stages_time']:.3f}s")

# Access evolved system prompt
current_state = resolver.get_current_state()
main_ai_prompt = current_state.main_response_prompt
```

## 🤝 Contributing

1. Follow existing architectural patterns
2. Write comprehensive tests for new features
3. Use type hints throughout the codebase
4. Update documentation for API changes
5. Follow the staged execution pattern for new modules
6. Ensure 100% test coverage for critical components

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Project 2501 Backend** - Built with FastAPI, SQLAlchemy, and PostgreSQL for the Cognitive Systems Framework with 5-Stage Execution Pipeline and Advanced AI Integration.