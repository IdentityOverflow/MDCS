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

## 📐 Architecture Overview (Current Implementation)

### 3-Layer Architecture

```
Frontend (Vue 3) ←→ Backend (FastAPI) ←→ Database (PostgreSQL + pgvector)
```

**Frontend Layer (Vue 3.5.18)**
- **Framework**: Vue 3 with Composition API and TypeScript
- **Build System**: Vite for fast development and building
- **State Management**: Pinia stores for complex application state
- **Chat Interface**: Real-time streaming chat with persona integration
- **Module Management**: Visual editors for Simple/Advanced modules
- **Debug System**: AI provider request/response inspector for Stage 3 analysis
- **Settings Storage**: Frontend localStorage (no backend duplication)

**Backend Layer (FastAPI 0.104.1)**
- **Framework**: FastAPI with SQLAlchemy 2.0.23 ORM
- **Core Engine**: 5-Stage Staged Execution Pipeline (see below)
- **AI Providers**: Ollama + OpenAI with streaming support
- **Script Sandbox**: RestrictedPython 7.0 with 15+ plugin functions
- **API Endpoints**: Complete REST API with streaming chat support
- **Test Coverage**: 461/461 tests passing (comprehensive TDD approach)

**Database Layer (PostgreSQL + pgvector)**
- **Models**: Persona, Module, Conversation, Message, ConversationState
- **Primary Keys**: UUID-based for all entities
- **State Persistence**: ConversationState table for POST_RESPONSE module results
- **Cascade Deletion**: Proper cleanup on conversation/message deletion

### 🚀 5-Stage Staged Execution Pipeline (Current Implementation)

Replaces the old BEFORE/AFTER timing system with clear execution stages:

**Stage 1: Template Preparation**
- Simple modules (static text)
- IMMEDIATE Non-AI modules  
- Previous POST_RESPONSE results retrieval
- Module: `StagedModuleResolver._execute_stage1()`

**Stage 2: Pre-Response AI Processing**
- IMMEDIATE AI-powered modules
- Uses `ctx.reflect()` for AI introspection
- Module: `StagedModuleResolver._execute_stage2()`

**Stage 3: Main AI Response Generation** 
- Handled by chat API (`/api/chat/send`, `/api/chat/stream`)
- Fully resolved system prompt from Stages 1+2
- Debug data captured for AI provider requests/responses

**Stage 4: Post-Response Processing (Non-AI)**
- POST_RESPONSE modules without AI inference
- Results stored in ConversationState table
- Module: `StagedModuleResolver.execute_post_response_modules()`

**Stage 5: Post-Response AI Analysis**
- POST_RESPONSE modules with AI inference (reflection, analysis)
- Uses `ctx.reflect()` for AI introspection
- Results stored for next conversation's Stage 1

### 🧩 Advanced Module System (Implemented)

**Simple Modules:**
- Static text content with `@module_name` references
- Recursive module resolution supported

**Advanced Modules:**
- Python scripts with RestrictedPython 7.0 sandbox
- 15+ built-in plugin functions (time, conversation, AI reflection)
- Variable outputs using `${variable}` syntax
- Execution contexts: IMMEDIATE, POST_RESPONSE, ON_DEMAND
- Trigger pattern support (regex/keyword matching)
- AI inference detection and stage assignment

**Self-Reflecting AI:**
- `ctx.reflect()` function for AI introspection
- AI can analyze its own responses and improve
- Examples: response quality assessment, conversation analysis

### 🔧 Core System Components

**1. StagedModuleResolver**
- 5-stage execution pipeline coordinator
- Module dependency resolution and circular reference detection
- ConversationState persistence for POST_RESPONSE results
- File: `backend/app/services/staged_module_resolver.py`

**2. Script Engine & Plugins**
- RestrictedPython sandbox with timeout protection
- 15+ plugin functions (time, conversation, utilities, AI reflection)
- Auto-discovery decorator system for extensibility
- Files: `backend/app/core/script_*` and `backend/app/plugins/`

**3. AI Provider Abstraction**
- Unified interface for Ollama and OpenAI
- Streaming and non-streaming support
- Debug data capture for Stage 3 analysis
- Files: `backend/app/services/ai_providers.py`, `ollama_service.py`, `openai_service.py`

**4. Debug System**
- Captures actual AI provider API requests/responses
- Shows resolved system prompts with all module processing
- Frontend debug console for development and troubleshooting
- Files: Frontend debug components and backend debug data embedding

**5. Chat System**
- Complete streaming chat with persona integration
- Settings passed in request payload (no backend storage)
- Conversation persistence with message editing support
- POST_RESPONSE module execution after responses

---

## 🧩 Module System Design
*Based on previous prototypes implementation insights*

### 🎯 Module System (Current Implementation Status)

**Simple Modules: ✅ Complete**
- Static text content with `@module_name` references
- Recursive module resolution supported
- Used for personalities, static instructions, fixed context
- Always execute in Stage 1

**Advanced Modules: ✅ Complete**
- Python scripts with RestrictedPython 7.0 sandbox
- Multiple named outputs using `${variable}` syntax
- Execution contexts replace old timing system:
  - **IMMEDIATE**: Execute in Stage 1 (non-AI) or Stage 2 (AI-powered)
  - **POST_RESPONSE**: Execute in Stage 4 (non-AI) or Stage 5 (AI-powered) 
  - **ON_DEMAND**: Execute only when explicitly triggered
- Trigger pattern support (regex/keyword matching)
- AI inference auto-detection with `requires_ai_inference` field
- Rich execution context with 15+ plugin functions

**Plugin Functions: ✅ 15+ Implemented**
- **Time Functions**: `ctx.get_current_time()`, `ctx.get_relative_time()`, business hours
- **Conversation Functions**: `ctx.get_message_count()`, `ctx.get_recent_messages()`, history access
- **AI Reflection**: `ctx.reflect()` for AI introspection and analysis
- **Utilities**: String manipulation, data processing, custom logic
- **Auto-Discovery**: Decorator-based plugin registration system

### 📝 Template System (5-Stage Resolution)

**Dual Placeholder Syntax:**
- `@module_name` - References to other modules (recursive resolution)
- `${variable}` - Dynamic script outputs from module execution

**5-Stage Resolution Process:**
1. **Stage 1**: Parse `@module_name`, resolve Simple modules + IMMEDIATE non-AI + previous POST_RESPONSE results
2. **Stage 2**: Execute IMMEDIATE AI-powered modules with `ctx.reflect()`
3. **Stage 3**: Send fully resolved system prompt to AI provider (Ollama/OpenAI)
4. **Stage 4**: Execute POST_RESPONSE non-AI modules, store results in ConversationState
5. **Stage 5**: Execute POST_RESPONSE AI-powered modules, store for next conversation

**State Persistence:**
- POST_RESPONSE results stored in ConversationState table
- Retrieved in Stage 1 of subsequent conversations
- Enables continuous learning and adaptation

**Resolution Features:**
- Circular dependency detection and prevention
- Recursive module resolution support
- Trigger pattern matching for conditional execution
- Error handling with detailed warnings
- Debug data capture at each stage 

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

## ✅ Implementation Status (Current State)

### 🎯 **COMPLETED FEATURES**

**✅ Core Infrastructure (100% Complete)**
- 3-layer architecture: Vue 3 + FastAPI + PostgreSQL
- Database models with UUID primary keys
- Complete REST API with streaming chat support
- 461/461 tests passing (comprehensive TDD coverage)

**✅ 5-Stage Execution Pipeline (100% Complete)**
- `StagedModuleResolver` replacing old `ModuleResolver`
- Stage 1-2: Template resolution with IMMEDIATE modules
- Stage 3: AI provider integration (Ollama + OpenAI)
- Stage 4-5: POST_RESPONSE processing with state persistence
- ConversationState table for cross-conversation continuity

**✅ Advanced Module System (100% Complete)**
- RestrictedPython 7.0 sandbox with timeout protection
- 15+ plugin functions (time, conversation, AI reflection)
- Auto-discovery decorator system for extensibility
- Trigger pattern support (regex/keyword matching)
- AI inference detection with automatic stage assignment

**✅ Self-Reflecting AI (100% Complete)**
- `ctx.reflect()` function for AI introspection
- AI can analyze its own responses and improve performance
- POST_RESPONSE modules for continuous learning
- Example: Response quality assessment and feedback loops

**✅ Chat System (100% Complete)**
- Real-time streaming chat with persona integration
- Settings passed in request payload (frontend localStorage)
- Conversation persistence with message editing
- POST_RESPONSE module execution after AI responses

**✅ Debug System (100% Complete)**
- Captures actual AI provider API requests/responses
- Shows resolved system prompts after all module processing
- Stage 3 AI provider interaction analysis
- Frontend debug console for development

**✅ Frontend Integration (100% Complete)**
- Vue 3.5.18 with TypeScript and Vite build system
- Complete CRUD interfaces for personas and modules
- Real-time chat interface with streaming support
- Debug tools for system prompt analysis
- ExecutionContext UI integration (IMMEDIATE/POST_RESPONSE/ON_DEMAND)

### 🔧 **KNOWN ISSUES & IMPROVEMENTS**

**⚠️ POST_RESPONSE Variable Resolution**
- **Status**: Module inclusion fixed, variable resolution needs refinement
- **Issue**: POST_RESPONSE modules show static content instead of resolved AI responses
- **Root Cause**: Variable substitution logic needs enhancement for stored state
- **Priority**: Medium (functionality works, output formatting needs improvement)

**📋 FUTURE ENHANCEMENTS** 

**🎯 Import/Export System**
- JSON persona serialization
- PNG-embedded persona cards (SillyTavern compatible) 
- Module marketplace preparation
- Version management and migration

**🎯 Advanced Features**
- Template editor with `@module` autocomplete
- Advanced debug screens for resolved system prompts
- Module dependency visualization
- Performance monitoring and optimization

**🎯 Vector Storage Integration**
- pgvector extension for semantic search
- Long-term memory with vector embeddings
- Contextual conversation retrieval

### 🌟 Advanced Module Examples (Working Implementation)

**Example 1: AI Self-Assessment Module (POST_RESPONSE)**
```python
# Script: response_assessor (ExecutionContext: POST_RESPONSE, AI: Required)
my_last_response = ctx.get_recent_messages(1)
quality_rating = ctx.reflect(
    "Rate this response quality from 1-10 and suggest improvements, in less than 150 tokens. Be short and concise.", 
    my_last_response, 
    temperature=0.8, 
    max_tokens=150
)
```
**Content:**
```
My self-assessment: ${quality_rating}
```
**Execution**: Runs after AI response, stores results for next conversation

**Example 2: Dynamic Memory Module (IMMEDIATE)**
```python
# Script: conversation_summary (ExecutionContext: IMMEDIATE, AI: Not Required)
messages = ctx.get_conversation_history(ctx.conversation_id, 20)
total_count = ctx.get_message_count(ctx.conversation_id)

if total_count > 50:
    memory_summary = "We've had extensive discussions"
elif total_count > 10:
    memory_summary = "I recall our previous conversations"  
else:
    memory_summary = "We're building our conversation history"

result = memory_summary
count = str(total_count)
```
**Content:**
```
${result}. Total messages: ${count}.
```
**Execution**: Runs during system prompt resolution (Stage 1)

**Example 3: Time-Aware Context Module (IMMEDIATE)**
```python
# Script: current_context (ExecutionContext: IMMEDIATE, AI: Not Required)
current_time = ctx.get_current_time("%H:%M")
current_date = ctx.get_current_time("%Y-%m-%d")
is_business = ctx.is_business_hours()

time_context = f"Current time: {current_time} on {current_date}"
if is_business:
    availability = "I'm available during business hours"
else:
    availability = "I'm available outside business hours"

result = f"{time_context}. {availability}"
```
**Content:**
```
${result}
```
**Execution**: Runs every conversation during system prompt resolution

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
- **Current Test Status**: 525/525 tests passing - maintain this standard
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
