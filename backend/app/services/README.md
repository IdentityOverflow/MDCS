# Services Layer

The Services layer implements business logic, AI provider integration, module execution, and orchestration. This is the most complex layer with 50+ files organized into subpackages.

## 📁 Directory Structure

```
services/
├── ai_providers.py               # Provider factory and interfaces
├── chat_session_manager.py       # Session lifecycle and cancellation
├── streaming_accumulator.py      # Stream → Response conversion
├── exceptions.py                 # Service-layer exceptions
├── system_prompt_state.py        # State-aware system prompt tracking
├── system_prompt_debug.py        # Debug/logging for prompts
├── modules/                      # Module execution system
│   ├── resolver.py              # Main StagedModuleResolver
│   ├── template_parser.py       # @module_name parsing
│   ├── execution/               # Module executors
│   │   ├── simple_executor.py
│   │   ├── script_executor.py
│   │   └── ai_executor.py
│   ├── stages/                  # 5-stage pipeline
│   │   ├── base_stage.py
│   │   ├── stage1.py (Template prep)
│   │   ├── stage2.py (Pre-response AI)
│   │   ├── stage3.py (Main AI - external)
│   │   ├── stage4.py (Post-response Non-AI)
│   │   └── stage5.py (Post-response AI)
│   └── resolver/                # Resolution components
│       ├── orchestrator.py
│       ├── pipeline_executor.py
│       ├── session_manager.py
│       ├── state_tracker.py
│       ├── streaming_handler.py
│       ├── template_resolver.py
│       ├── post_response_handler.py
│       └── result_models.py
├── providers/                    # AI provider implementations
│   ├── base/                    # Base classes
│   │   ├── provider_service.py
│   │   ├── http_client.py
│   │   └── stream_processor.py
│   ├── ollama/                  # Ollama provider
│   │   ├── service.py
│   │   ├── models.py
│   │   ├── request_builder.py
│   │   └── response_parser.py
│   └── openai/                  # OpenAI provider
│       ├── service.py
│       ├── models.py
│       ├── request_builder.py
│       └── response_parser.py
└── utils/                       # Service utilities
    ├── async_helpers.py
    ├── error_handling.py
    └── validation.py
```

---

## 🔑 Key Components

### **ai_providers.py**
Provider factory and base interfaces.

**Classes:**
- `ProviderType(Enum)`: OLLAMA, OPENAI
- `ChatRequest`: Universal request format
- `ChatResponse`: Universal response format
- `StreamingChunk`: Streaming response chunk
- `ProviderFactory`: Creates provider instances

**Usage:**
```python
provider = ProviderFactory.create_provider(ProviderType.OLLAMA)
response = await provider.send_message(chat_request)
```

---

### **chat_session_manager.py**
Session lifecycle management and cancellation.

**Features:**
- Session registration with AsyncIO tasks
- Cancellation token tracking
- Active session monitoring
- Stage-aware cancellation

**Key Methods:**
```python
manager.register_session(session_id, conversation_id, asyncio_task, stage)
manager.cancel_session(session_id)  # Returns bool
manager.get_session_status(session_id)  # Returns SessionStatus enum
manager.get_active_session_count()  # Returns int
```

**Session Lifecycle:**
1. API endpoint generates session_id
2. Register session with current AsyncIO task
3. Store cancellation token
4. Process request (streaming/non-streaming)
5. Check cancellation at key points
6. Cleanup session on completion/cancellation

---

### **streaming_accumulator.py**
Converts streaming responses to complete responses with cancellation support.

**Key Classes:**
- `StreamingAccumulator`: Accumulates chunks into complete response
- `StreamingToNonStreamingConverter`: Convenience wrapper

**Usage:**
```python
accumulator = StreamingAccumulator()
result = await accumulator.accumulate_stream(
    stream_generator,
    session_id=session_id,
    conversation_id=conversation_id
)
# result is ChatResponse with full content
```

**Features:**
- Cancellation checking per chunk
- Metadata accumulation
- Token counting
- Error handling

---

### **system_prompt_state.py**
State-aware system prompt tracking across execution stages.

**Purpose:**
- Track system prompt evolution through 5-stage pipeline
- Provide stage-appropriate prompts for AI plugins
- Enable reflection with current resolved state

**Key Methods:**
```python
state = SystemPromptState()
state.set_stage_prompt(1, resolved_template)
state.set_stage_prompt(2, after_stage2_prompt)
current_prompt = state.get_prompt_for_stage(2)
full_history = state.get_all_stages()
```

**Integration:**
- Created in StagedModuleResolver
- Passed to ScriptExecutionContext
- Used by `reflect()` and `generate()` plugins
- Tracks prompt modifications across stages

---

## 📦 Modules Subsystem

### **modules/resolver.py**
Main `StagedModuleResolver` class - orchestrates 5-stage execution pipeline.

**Key Methods:**
```python
# Template resolution (Stage 1 + 2)
await resolver.resolve_template_stages_1_and_2(
    template, session_id, conversation_id, persona_id, db_session,
    trigger_context, current_provider, provider_settings, chat_controls
)

# Post-response execution (Stage 4 + 5)
await resolver.execute_post_response_stages(
    template, ai_response, session_id, conversation_id, persona_id,
    db_session, trigger_context, provider, provider_settings, chat_controls
)
```

**Features:**
- State tracking with SystemPromptState
- Cancellation support throughout
- ConversationState persistence
- Recursive module resolution
- Error handling and recovery

---

### **modules/template_parser.py**
Parses persona templates for `@module_name` references.

**Features:**
- Regex-based module reference detection
- Dependency extraction
- Circular reference detection
- Nested module support

**Example:**
```python
template = "Hello @greeting, the time is @time_module"
parser = TemplateParser()
refs = parser.parse_template(template)
# Returns: ["greeting", "time_module"]
```

---

### **modules/execution/**
Module executor implementations.

#### **simple_executor.py**
Executes simple (static text) modules.

```python
executor = SimpleModuleExecutor()
result = executor.execute(module, trigger_context, script_context)
# Returns resolved static content
```

#### **script_executor.py**
Executes advanced module Python scripts.

```python
executor = ScriptModuleExecutor()
result = await executor.execute(
    module, trigger_context, script_context,
    conversation_id, persona_id, db_session
)
# Returns ScriptExecutionResult with variables
```

**Features:**
- ScriptEngine integration
- Plugin function access
- Variable extraction
- Error handling

#### **ai_executor.py**
Wrapper for AI-powered modules (uses script_executor + AI plugins).

---

### **modules/stages/**
5-stage execution pipeline implementation.

#### **Stage 1: Template Preparation** (stage1.py)
- Simple modules
- IMMEDIATE Non-AI modules
- Previous POST_RESPONSE state variables

#### **Stage 2: Pre-response AI** (stage2.py)
- IMMEDIATE AI-powered modules
- `generate()` / `reflect()` calls
- Executed before main AI response

#### **Stage 3: Main AI Response**
- Handled by chat endpoint
- Not part of module system
- Uses resolved template from Stage 1+2

#### **Stage 4: Post-response Non-AI** (stage4.py)
- POST_RESPONSE modules without AI
- Fast processing after AI response
- State saved to ConversationState

#### **Stage 5: Post-response AI** (stage5.py)
- POST_RESPONSE modules with AI
- Reflection and analysis
- State saved to ConversationState

**Each stage:**
- Filters modules by context + AI requirement
- Executes in priority order
- Handles cancellation
- Updates SystemPromptState
- Logs execution results

---

### **modules/resolver/** Components

#### **orchestrator.py**
High-level orchestration of stage execution.

#### **pipeline_executor.py**
Executes stages sequentially with error handling.

#### **session_manager.py**
Manages session context during resolution.

#### **state_tracker.py**
Tracks ConversationState changes.

#### **streaming_handler.py**
Handles streaming responses during module execution.

#### **template_resolver.py**
Resolves `@module_name` references recursively.

#### **post_response_handler.py**
Executes Stages 4 & 5 after AI response.

#### **result_models.py**
Pydantic models for resolution results.

---

## 🌐 Providers Subsystem

### **providers/base/**
Base classes for provider implementations.

#### **provider_service.py**
Abstract base class for all providers.

```python
class BaseProviderService(ABC):
    @abstractmethod
    async def send_message(request: ChatRequest) -> ChatResponse:
        pass

    @abstractmethod
    async def send_message_stream(request: ChatRequest):
        pass

    @abstractmethod
    def validate_settings(settings: dict) -> bool:
        pass
```

#### **http_client.py**
HTTP client with retry logic and error handling.

#### **stream_processor.py**
SSE (Server-Sent Events) stream processing.

---

### **providers/ollama/**
Ollama provider implementation.

**Files:**
- `service.py`: Main Ollama service
- `models.py`: Ollama-specific request/response models
- `request_builder.py`: Builds Ollama API requests
- `response_parser.py`: Parses Ollama API responses

**Features:**
- Local Ollama server integration
- Streaming and non-streaming support
- Model management
- Context window handling

---

### **providers/openai/**
OpenAI-compatible provider (OpenAI, LM Studio, etc.).

**Files:**
- `service.py`: Main OpenAI service
- `models.py`: OpenAI-specific models
- `request_builder.py`: Builds OpenAI API requests
- `response_parser.py`: Parses OpenAI API responses

**Features:**
- OpenAI API compatibility
- Custom base URL support (LM Studio, etc.)
- Streaming with SSE
- Function calling support (future)

---

## 🔄 Execution Flows

### Template Resolution Flow
```
1. Chat endpoint receives request
2. StagedModuleResolver created
3. resolve_template_stages_1_and_2() called
4. TemplateParser finds @module_name refs
5. Stage 1 executor: Simple + IMMEDIATE Non-AI + Previous POST_RESPONSE state
6. Stage 2 executor: IMMEDIATE AI modules
7. Resolved template returned
8. Used as system prompt for Stage 3 (main AI call)
```

### Post-Response Flow
```
1. AI response completed (Stage 3)
2. execute_post_response_stages() called
3. Stage 4 executor: POST_RESPONSE Non-AI modules
4. Stage 5 executor: POST_RESPONSE AI modules
5. Results stored in ConversationState
6. Available for next conversation's Stage 1
```

### Cancellation Flow
```
1. User clicks stop button
2. Frontend calls POST /api/chat/cancel/{session_id}
3. ChatSessionManager.cancel_session() marks token as cancelled
4. StreamingAccumulator checks token per chunk
5. StagedModuleResolver checks token per stage
6. AsyncIO task cancelled if needed
7. Cleanup and partial results returned
```

---

## 🔐 Security & Safety

### Provider Security
- API keys handled securely
- Request/response validation
- Timeout enforcement
- Error sanitization

### Module Execution Safety
- RestrictedPython sandbox
- Reflection depth limiting
- Circular reference detection
- Database read-only access

### Session Management
- UUID session IDs
- Token-based cancellation
- No cross-session data leakage
- Automatic cleanup

---

## 📊 Performance Optimizations

### Caching
- Plugin registry cached on load
- Template parsing cached per request
- Provider connections pooled

### Async/Await
- Concurrent stage execution where possible
- Non-blocking AI calls
- Streaming for responsiveness

### Database
- Efficient queries with proper joins
- ConversationState indexed by conversation_id
- Bulk operations for multiple modules

---

## 🧪 Testing

### Service Testing
```python
@pytest.fixture
def mock_provider():
    return Mock(spec=BaseProviderService)

def test_staged_resolver(db_session, mock_provider):
    resolver = StagedModuleResolver(db_session)
    result = await resolver.resolve_template_stages_1_and_2(...)
    assert result.resolved_template
```

### Integration Testing
```python
def test_end_to_end_chat(client, db_session):
    response = client.post("/api/chat/send", json={
        "message": "Hello",
        "persona_id": persona_id,
        "provider": "ollama",
        "provider_settings": {...}
    })
    assert response.status_code == 200
```

---

## 📝 Key Concepts

### Staged Execution Pipeline
5-stage architecture eliminates race conditions and ensures predictable ordering.

### State-Aware Prompts
SystemPromptState tracks prompt evolution for AI reflection.

### Cancellation Support
Session-based cancellation works across all stages and AI calls.

### Provider Abstraction
Unified interface supports multiple AI providers transparently.

### Module Composition
Modules can reference other modules for complex behaviors.

### Conversation State Persistence
POST_RESPONSE module outputs available in next conversation.

---

## 🔮 Future Enhancements

### Planned Improvements (See SERVICES_REFACTORING.md)
- Modular architecture to replace monolithic files
- Domain-driven organization (providers/, session/, modules/, utils/)
- Composition over inheritance
- Single responsibility per file
- Enhanced testing and maintainability

---

## 📚 Further Reading

- **API Layer**: See [../api/README.md](../api/README.md) for endpoint integration
- **Models Layer**: See [../models/README.md](../models/README.md) for data structures
- **Core Layer**: See [../core/README.md](../core/README.md) for script engine
- **Plugins Layer**: See [../plugins/README.md](../plugins/README.md) for plugin functions

---

## 📝 Notes

- Services layer is the most complex subsystem (50+ files)
- Staged execution redesign completed 2025-01-28
- Chat cancellation system completed 2025-01-27
- Refactoring plan documented in SERVICES_REFACTORING.md
- All 627 tests passing with staged + cancellation systems
