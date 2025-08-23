# Project 2501 - Cognitive Systems Framework
## Design Collaboration Scratchpad

*"Building dynamic cognitive architectures through scriptable modules"*

---

## 🎯 Project Vision

**Project 2501** is a cognitive systems framework that reimagines how we interact with AI by solving some common limitations of static system prompts and context rot.

### The Problem
Traditional AI systems use static system prompts providing a rigid set of instructions limiting adaptibility and may even get buried as conversations grow depending on how it's inserted. This approach tends to lead to:
- **Context rot**: This is a subtle yet critical phenomenon in large language models (LLMs), where the model's performance begins to deteriorate as the amount of input increases.
- **Memory loss**: AI forgets crucial information or instructions from earlier in conversation.
- **Inflexibility**: Cannot adapt behavior dynamically based on conversation state
- **Limited persistence**: Each session starts from scratch

### Proposed Solution: Dynamic System Prompt Architecture
Project 2501 treats the system prompt as a **living, modular heads-up display** that stays persistently visible to the AI throughout any conversation length.
So instead of the classic:
```
{
  system: "Static prompt...",
  user: "msg1",
  ai: "response1",
  user: "msg2",
  ai: "response2",
  ...
}
```

We can use something like:
```
{
  system: "Personality: @personality_module,
          Current time and date: @current_time_module,
          Long term memory: @early_conversation_summary_module,
          Recent memory: @recent_exchanges_module,
          Instructions for x: @instruction_for_x_module,
          Instructions for y: @instruction_for_y_module,
          ...",
  user: "latest_message",
  ai: "latest_response"
}
```
Where each module is defined separately, comes with all the necessay information and can be static or updated during the conversation by a script or by the AI sytem itself.

### Module System
- **Simple Modules**: Static text templates (personality, static instructions, persistent information, etc.).
- **Advanced Modules**: Python scripts with secure sandbox execution that generate dynamic content using `${variable}` outputs.
- **Dual Placeholder System**: 
  - `@module_name` - References to other modules (recursive resolution)
  - `${variable}` - Dynamic script outputs (result, memory, time, etc.)
- **Plugin Framework**: Auto-discovery decorator system for extending script functionality
- **Trigger System**: Keyword/regex patterns for conditional module activation
- **Self-Modifying**: AI can update some of its own modules, creating evolving **personas**.

### Key Innovation
This enables **virtually infinite conversations with adaptive memory**, **composable AI personas**, and **self-evolving cognitive architectures** - essentially creating a framework for building any type of AI agent or interactive system you can think of.

### Vision
A model-agnostic platform where users can design, share, and evolve sophisticated AI personas through an intuitive web interface, powered by a modular Python backend.

---

## 📐 Architecture Overview

### System Architecture Layers

**Data Layer**
- **Database**: PostgreSQL (with pgvector extension)
  - **Relational data**: personas, modules, templates, conversations
  - **Vector storage**: Semantic search capabilities (future plans)
  - **ACID compliance**: for data integrity
  - **Excellent Python ecosystem support**: Through SQLAlchemy

**Backend Layer (Python)**
- **Framework**: FastAPI for REST API development
- **Core Engine**: Module execution and template resolution
- **API Layer**: RESTful endpoints for frontend communication
- **AI model Integration**: Abstracted interface for different AI providers
- **Module Sandbox**: Secure Python execution environment
- **Import/Export System**: JSON and PNG-embedded formats

**Frontend Layer (Web UI)**
- **Framework**: Vue 3 with Composition API
- **Real-time Communication**: WebSocket for live chat updates
- **Golden Ratio Layout**: Responsive viewport management
- **Persona Management**: Visual editing interface for personas/modules/templates
- **State Management**: Pinia for complex application state
- **Debug tool**: System prompt debug tool to facilitate module creation and integration

### Core System Modules

**1. Cognitive Architecture Engine**
- Template resolution and module injection
- Module lifecycle management
- Dependency validation and circular reference detection
- Execution timing coordination

**2. Module System**
- Simple module (static text) management
- Advanced module (Python script) execution
- Trigger word/phrase detection
- Inter-module communication

**3. Model Abstraction Layer**
- Unified interface for AI providers ( Ollama, LMStudion, OpenAI, Anthropic etc.)
- Token counting and rate limiting
- Response streaming and error handling

**4. Import/Export System**
- **JSON Format**: Standard persona serialization
- **PNG Embedding**: SillyTavern-style persona cards with embedded JSON
- Module sharing and marketplace preparation
- Version management and migration

**5. Security & Sandbox**
- Python script execution isolation
- Safe function whitelisting
- User-generated code validation

---

## 🧩 Module System Design
*Based on previous prototypes implementation insights*

### Module Types

**Simple Modules:**
- Static text content inserted into templates
- Manual updates only
- Use case: Personalities, static instructions, fixed context

**Advanced Modules:**
- Python scripted content with secure RestrictedPython sandbox execution
- Multiple named outputs using `${variable}` syntax (result, memory, time, etc.)
- Conditional trigger system (keyword/regex pattern activation)
- Multiple execution timing options:
  - BEFORE: Execute before AI response (update system prompt)
  - AFTER: Execute after AI response (prepare for next exchange)
  - CUSTOM: Execute on-demand via API calls
  - ALWAYS: Execute on every template resolution (for timestamps, counters)
- Rich execution context with full conversation/database access via plugin system
- Plugin framework for extending functionality (time, conversation, AI processing, custom)
- Use case examples: Dynamic memory, contextual awareness, self-modifying behavior, adaptive personas

### Template System
- **Dual Placeholder Syntax**:
  - `@module_name` - References to other modules (recursive resolution)
  - `${variable}` - Dynamic script outputs to avoid naming collisions with modules
- Template defines how modules are arranged in final prompt
- **Resolution Process**:
  1. Parse `@module_name` references in templates
  2. Check trigger patterns for advanced modules
  3. Execute Python scripts in secure sandbox with rich context
  4. Resolve `${variable}` placeholders using script outputs  
  5. Replace `@module_name` with final resolved content
  6. Continue recursive resolution for nested dependencies
- Support for saved/loaded template presets 

### Module Features Observed
- **Trigger Words/Phrases**: Modules can activate based on conversation content
- **Conditional Logic**: Python scripts can implement complex decision making
- **State Management**: Access to conversation history, exchange counts, etc.
- **Helper Functions**: Built-in utilities for common operations
- **Plugin system**: For making aditional helper function available for scripting
- **Execution Control**: Fine-grained control over when modules update

### Module Dependencies & Execution
- Modules can reference other modules using `@module_name`
- Recursive call detection prevents infinite loops
- Missing dependency validation with user warnings
- User responsibility for architectural coherence

### Performance & Timing
- Background execution for post-response modules (e.g., memory updates)
- Fast modules (time, static data) vs AI-dependent modules
- Execution timing options provide performance optimization opportunities

---

## 📁 Project Structure Plan (will change over time)

```
project-2501/
├── README.md
├── docker-compose.yml
├── .env.example
├── .gitignore
│
├── frontend/                   # Vue 3 Application
│   ├── src/
│   │   ├── components/         # Reusable Vue components
│   │   │   ├── chat/          # Chat interface components
│   │   │   ├── persona/       # Persona management components
│   │   │   ├── module/        # Module editor components
│   │   │   ├── template/      # Template editor components
│   │   │   └── layout/        # Layout and UI structure components
│   │   ├── views/             # Page-level components
│   │   ├── stores/            # Pinia state management
│   │   ├── services/          # API service functions
│   │   ├── composables/       # Vue 3 composition functions
│   │   ├── types/             # TypeScript type definitions
│   │   └── utils/             # Utility functions
│   ├── public/
│   ├── tests/                 # Frontend tests
│   ├── package.json
│   ├── vite.config.js
│   └── tsconfig.json
│
├── backend/                    # Python Backend
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py            # FastAPI application entry
│   │   ├── core/              # Core business logic
│   │   │   ├── __init__.py
│   │   │   ├── cognitive_engine.py    # Main cognitive architecture engine
│   │   │   ├── module_system.py       # Module management
│   │   │   ├── template_engine.py     # Template resolution
│   │   │   └── sandbox.py             # Python script execution
│   │   ├── models/            # Database models (SQLAlchemy)
│   │   │   ├── __init__.py
│   │   │   ├── persona.py
│   │   │   ├── module.py
│   │   │   ├── template.py
│   │   │   └── conversation.py
│   │   ├── api/               # REST API endpoints
│   │   │   ├── __init__.py
│   │   │   ├── personas.py
│   │   │   ├── modules.py
│   │   │   ├── templates.py
│   │   │   ├── conversations.py
│   │   │   └── import_export.py
│   │   ├── services/          # Business logic services
│   │   │   ├── __init__.py
│   │   │   ├── ai_providers.py        # Model abstraction layer
│   │   │   ├── module_service.py
│   │   │   └── conversation_service.py
│   │   ├── database/          # Database configuration and migrations
│   │   │   ├── __init__.py
│   │   │   ├── connection.py
│   │   │   └── migrations/
│   │   └── utils/             # Utility functions
│   ├── tests/                 # Backend tests
│   │   ├── unit/              # Unit tests
│   │   ├── integration/       # Integration tests
│   │   └── fixtures/          # Test data
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   └── pyproject.toml
│
├── shared/                     # Shared resources
│   ├── schemas/               # JSON schemas for import/export
│   ├── types/                 # Shared type definitions
│   └── docs/                  # API documentation
│
├── database/                   # Database setup and seeds
│   ├── migrations/            # Database migration scripts
│   ├── seeds/                 # Sample data for development
│   └── schema.sql             # Database schema
│
├── docs/                       # Project documentation
│   ├── architecture/          # Architecture decisions and diagrams
│   ├── api/                   # API documentation
│   ├── development/           # Development guides
│   └── user/                  # User documentation
│
├── scripts/                    # Development and deployment scripts
│   ├── setup.sh              # Initial project setup
│   ├── dev.sh                # Start development environment
│   ├── test.sh               # Run all tests
│   └── build.sh              # Build for production
│
└── tests/                      # End-to-end tests
    ├── integration/           # Cross-system integration tests
    └── e2e/                   # End-to-end user workflow tests
```

---

## 🚀 Advanced Modules Implementation Plan
*Detailed TDD-based implementation strategy*

### Phase 1: Core Script Engine (Foundation)

**Files to create:**
```
backend/app/core/script_engine.py       # Main RestrictedPython execution engine
backend/app/core/script_plugins.py      # Auto-discovery decorator registry  
backend/app/core/script_context.py      # Rich execution context management
backend/app/core/script_validator.py    # Security validation for scripts
backend/app/core/trigger_matcher.py     # Simple keyword/regex trigger matching
```

**Key Components:**
- **ScriptEngine**: RestrictedPython-based secure execution with timeout handling
- **PluginRegistry**: Decorator-based auto-discovery system for plugin functions
- **ScriptExecutionContext**: Rich context object with conversation/database access
- **ScriptValidator**: AST-based validation for security (imports, attributes, functions)
- **TriggerMatcher**: Simple pattern matching for keywords (`word1|word2`) and regex

### Phase 2: Plugin System (Extensibility)

**Files to create:**
```
backend/app/plugins/__init__.py              # Plugin package initialization
backend/app/plugins/time_plugins.py         # Current time, relative time, business hours
backend/app/plugins/conversation_plugins.py # Full conversation history, message counts
backend/app/plugins/core_plugins.py         # Basic utility functions (len, str, etc.)
```

**Plugin Architecture:**
- **Auto-Discovery**: Load all modules in `app/plugins/` directory automatically
- **Decorator Registration**: `@plugin_registry.register("function_name")` 
- **Database Session Injection**: Auto-inject `db_session` parameter for functions that need it
- **Error Handling**: Graceful fallbacks for plugin function failures

### Phase 3: Integration (Connect to Existing System)

**Files to modify:**
```
backend/app/services/module_resolver.py     # Add ${variable} resolution and script execution
backend/app/api/modules.py                  # Enhanced API for advanced module management
backend/requirements.txt                    # Add RestrictedPython dependency
```

**Integration Points:**
- **Enhanced ModuleResolver**: Add advanced module detection and script execution
- **Variable Resolution**: `${variable}` pattern matching and replacement after script execution
- **API Extensions**: New endpoints for advanced module creation, testing, and debugging
- **Backward Compatibility**: Simple modules continue working without changes

### Phase 4: Testing (TDD Implementation)

**Files to create:**
```
backend/tests/unit/test_script_engine.py        # Script execution, validation, security tests
backend/tests/unit/test_plugins.py              # Plugin registration and function tests  
backend/tests/integration/test_advanced_modules.py # Full advanced module workflow tests
```

**Testing Strategy:**
- **Write Tests First**: All functionality implemented following TDD approach
- **Security Testing**: Validate sandbox restrictions and escape prevention
- **Plugin Testing**: Verify auto-discovery, registration, and context injection
- **Integration Testing**: Full workflow from template to resolved output
- **Performance Testing**: Script execution timeouts and resource limits

### Advanced Module Examples

**Example 1: Dynamic Memory Module**
```python
# Script (trigger: "memory|remember|recall")
messages = ctx.get_conversation_history(ctx.conversation_id, 20)
total_count = ctx.get_message_count(ctx.conversation_id)

if total_count > 50:
    memory_summary = "We've had extensive discussions"
elif total_count > 10:
    memory_summary = "I recall our previous conversations"  
else:
    memory_summary = "We're building our conversation history"

# Multiple named outputs
result = memory_summary
count = str(total_count)
```

**Content:**
```
${result}. Total messages: ${count}.
```

**Example 2: Time-Aware Greeting Module**
```python  
# Script (timing: ALWAYS - execute every resolution)
current_time = ctx.get_current_time("%H:%M")
is_business = ctx.is_business_hours()

if is_business:
    greeting = f"Good day! It's {current_time}"
else:
    greeting = f"Good evening! It's {current_time}"

# Output
result = greeting
```

**Content:**
```
${result}. How can I help you today?
```

---

## 🏗️ Development Approach
*Learning from previous technical debt issues*

### Core Problem Identified
Previous implementation suffered from **AI context loss during development** - each Claude Code session lost architectural awareness, leading to:
- Unnecessary reimplementation
- Tight coupling between modules
- Frontend solutions to backend problems
- Architectural drift over time

### Proposed Solutions

**Test-Driven Development (TDD) for Advanced Modules**
- **Write Tests First**: All advanced module functionality follows strict TDD approach
- **Current Test Status**: 330/330 tests passing - maintain this standard
- **Security-First Testing**: Sandbox restrictions and escape prevention tested before implementation
- **Plugin Testing**: Auto-discovery, registration, and context injection verified
- **Integration Testing**: Full workflow from script execution to template resolution
- **Performance Testing**: Script timeouts, resource limits, and execution monitoring
- **Comprehensive Coverage**: Tests serve as living documentation of system behavior
- **Modular Design**: TDD forces clean interfaces and testable architecture

**High Modularity Principles**
- Clear separation of concerns
- Well-defined interfaces between modules
- Minimal coupling, maximum cohesion
- Each module has single responsibility

**Architectural Documentation Strategy**
- Living architectural documentation updated with every change
- Clear API specifications
- Module interaction diagrams
- Decision logs for architectural choices

**Database & Technology Upgrades**
- PostgreSQL + pgvector for both relational and vector storage
- FastAPI for robust REST API development
- Vue 3 + Composition API for reactive frontend
- JSON + PNG-embedded import/export formats
