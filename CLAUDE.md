# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🎯 Project Vision: Project 2501 - Cognitive Systems Framework

**Core Innovation**: Dynamic System Prompt Architecture that treats the system prompt as a **living, modular heads-up display** that stays persistently visible to AI throughout any conversation length, solving the fundamental limitations of static system prompts and context rot.

### Key Components:
- **Simple Modules**: Static text templates (personalities, instructions, tools)
- **Advanced Modules**: Python scripts that update dynamically (memory, context, time, custom logic)
- **Self-Reflecting AI**: AI can introspect on its own thoughts and responses using `ctx.reflect()`
- **Self-Modifying**: AI can update some of its own modules, creating evolving personas

## 📐 Architecture Overview

### System Architecture (3-Layer)
```
Frontend (Vue 3) ←→ Backend (FastAPI) ←→ Database (PostgreSQL + pgvector)
```

**Data Layer**: PostgreSQL with pgvector extension
- Relational data: personas, modules, templates, conversations
- Vector storage: Future AI embeddings, semantic search capabilities
- UUID-based primary keys for all entities

**Backend Layer**: Python FastAPI
- Core Engine: Module execution and template resolution
- API Layer: RESTful endpoints for frontend communication
- Model Integration: Abstracted interface for different AI providers
- Module Sandbox: Secure Python execution environment

**Frontend Layer**: Vue 3 Web UI
- Golden Ratio Layout: Responsive viewport management (4-panel grid)
- Real-time Communication: WebSocket for live chat updates
- Persona Management: Visual editing interface for personas/modules/templates

### 🧩 Module System Design

**Template System**: Uses dual placeholder syntax for maximum flexibility:
- `@module_name` - References to other modules (static/advanced)
- `${variable}` - Dynamic script outputs (result, memory, time, etc.)

**Simple Modules**: Static text content resolved directly into templates

**Advanced Module Architecture**:
- **Python Script Execution**: Secure RestrictedPython sandbox with plugin system
- **Dynamic Content Generation**: Scripts produce multiple named outputs via `${variable}` syntax
- **Trigger System**: Keyword/regex patterns activate modules based on conversation context
- **Execution Timing**: BEFORE (pre-AI), AFTER (post-AI), CUSTOM (on-demand), ALWAYS (every resolution)
- **Plugin Framework**: Auto-discovery decorator system for extending script functionality
- **Full Context Access**: Scripts have access to conversation history, database, and helper functions

**Module Resolution Flow**:
1. Parse `@module_name` references in templates
2. Load modules and check trigger patterns for advanced modules  
3. Execute Python scripts in sandbox with rich execution context
4. Resolve `${variable}` references in module content using script outputs
5. Replace `@module_name` with final resolved content
6. Continue recursive resolution for nested module references

**Module Dependencies**: 
- Modules reference other modules using `@module_name` syntax
- Advanced modules use `${variable}` for script outputs to avoid naming collisions
- Recursive call detection prevents infinite loops
- Missing dependency validation with user warnings

## 📁 Current Project Structure

```
project-2501/
├── frontend/              # Vue 3 Application  
│   ├── src/
│   │   ├── components/    # Reusable Vue components
│   │   │   ├── chat/     # Chat interface components
│   │   │   ├── views/    # Page-level components (Personas, Modules, Settings, etc.)
│   │   │   └── connections/ # API connection components
│   │   ├── stores/       # Pinia state management
│   │   ├── types/        # TypeScript type definitions
│   │   └── composables/  # Vue 3 composition functions
├── backend/              # Python Backend
│   ├── app/
│   │   ├── main.py      # FastAPI application entry
│   │   ├── core/        # Core business logic
│   │   │   ├── config.py         # Configuration management
│   │   │   ├── script_engine.py  # Advanced module script execution engine
│   │   │   ├── script_plugins.py # Plugin registry and auto-discovery
│   │   │   ├── script_context.py # Execution context management
│   │   │   ├── script_validator.py # Security validation for scripts
│   │   │   └── trigger_matcher.py # Simple trigger pattern matching
│   │   ├── plugins/     # Extensible plugin system
│   │   │   ├── __init__.py
│   │   │   ├── time_plugins.py        # Time/date functions
│   │   │   ├── conversation_plugins.py # Conversation access functions
│   │   │   └── core_plugins.py        # Basic utility functions
│   │   ├── models/      # Database models (SQLAlchemy)
│   │   │   ├── persona.py       # AI personas
│   │   │   ├── module.py        # Simple & Advanced modules
│   │   │   ├── conversation.py  # Chat conversations & messages
│   │   │   └── base.py          # Base model with common fields
│   │   ├── api/         # REST API endpoints
│   │   │   └── database.py      # Database test/info endpoints
│   │   ├── database/    # Database connection management
│   │   │   └── connection.py    # Connection pooling & testing
│   │   └── services/    # Business logic services
│   │       ├── module_resolver.py      # Enhanced with advanced module support
│   │       └── advanced_module_service.py # Advanced module coordination
│   ├── tests/          # Comprehensive test suite (396 tests passing)
│   │   ├── unit/       # Unit tests (181 tests) - Models, services, core logic
│   │   ├── integration/ # Integration tests (215 tests) - Full HTTP API with real DB
│   │   └── conftest.py # PostgreSQL test fixtures
├── database/           # Database setup and seeds
├── docs/              # Project documentation
│   └── architecture/  # Architecture decisions and diagrams
└── scripts/           # Development and deployment scripts
    ├── install_BE.sh  # Backend installation script
    └── run_BE.sh     # Backend run script
```

## 🛠️ Technology Stack

### Backend (Python)
- **Framework**: FastAPI 0.104.1
- **Database**: PostgreSQL with SQLAlchemy 2.0.23
- **Configuration**: Pydantic 2.11.7 + pydantic-settings 2.10.1
- **Script Execution**: RestrictedPython 7.0 for secure Python sandbox execution ✅
- **Testing**: pytest 7.4.3 with PostgreSQL integration
- **Environment**: conda environment `project2501`

### Frontend (Vue 3)  
- **Framework**: Vue 3.5.18 with TypeScript
- **State**: Pinia 3.0.3
- **Routing**: Vue Router 4.5.1
- **Markdown**: marked 16.2.0 + @types/marked 5.0.2
- **Testing**: Vitest 3.2.4
- **Build**: Vite 7.0.6

### Database (PostgreSQL with pgvector extension)
- **Primary**: project2501 (owned by project2501 user) 
- **Test DB**: project2501_test (owned by project2501 user)
- **Models**: Persona, Module, Conversation, Message (all with UUIDs)

## 🧪 Development Environment

### Backend Development

**Setup**:
```bash
# Initial setup
./scripts/install_BE.sh

# Activate environment
conda activate project2501

# Run backend server  
./scripts/run_BE.sh
# OR manually:
cd backend && python app/main.py
```

**Testing**:
```bash
# IMPORTANT: Use the full conda path since project2501 environment is in miniforge3
# AND make sure you're already in the backend directory (/home/q/Documents/AI/project2501/backend)
source /home/q/miniforge3/etc/profile.d/conda.sh && conda activate project2501 && pytest -v

# Alternative commands if needed:
# Run all tests (396 tests passing)
pytest                    # Run all tests
pytest -v                # Verbose output (RECOMMENDED - shows all test details)

# Run specific test categories
pytest tests/unit/        # Unit tests only (181 tests)
pytest tests/integration/ # Integration tests only (215 tests)

# Run specific test files or methods
pytest tests/unit/test_modules_api.py -v                    # Specific file
pytest tests/unit/test_modules_api.py::TestModulesCreateEndpoint -v  # Specific class
pytest tests/unit/test_modules_api.py::TestModulesCreateEndpoint::test_create_simple_module_success -v  # Specific test

# Test with coverage (if installed)
pytest --cov=app tests/

# Integration tests require PostgreSQL running
pytest tests/integration/ -v
```

**Test Structure**:
- **Unit Tests**: Fast, isolated tests for models, services, and core logic (no database) - 181 tests
- **Integration Tests**: Full HTTP API tests using `project2501_test` database with proper cleanup - 215 tests  
- **Advanced Module Tests**: Complete test coverage for script execution, plugins, and triggers - 66 new tests
- **TDD Approach**: All advanced modules features developed test-first with comprehensive coverage

**Database Isolation**:
- **Frontend**: Connects to main database (`project2501` via backend server)
- **Tests**: Use separate test database (`project2501_test`) with automatic cleanup
- **No Cross-Contamination**: Tests never pollute the main database

**Database**:
- Main DB: `project2501` 
- Test DB: `project2501_test`
- User: `project2501` with password in `.env` and `.env.test`
- Connection test available at: `GET /api/database/test`

### Frontend Development

**Setup & Commands**:
```bash
cd frontend
npm run dev        # Start development server (localhost:5173)
npm run build      # Build for production
npm run test:unit  # Run unit tests
npm run lint       # Run ESLint
npm run format     # Format code with Prettier
```

**Current UI Structure**:
- Golden ratio 4-panel grid layout
- MainChat (Area A), DisplayArea (Area B), ControlPanel (Area C), Info (Area D)
- Cyberpunk theme with custom styling
- Components: Personas, Modules, Settings, Tools, Files, Scratchpad, Debug views

## 🚨  CRITICAL DEVELOPMENT PRINCIPLES (Anti-Technical Debt)

### 1. **Check Before You Code - Avoid Reimplementation**
- **ALWAYS SEARCH FIRST**: Before implementing ANY feature, search the entire codebase for related functionality:
  ```bash
  # Search for existing functions/components/solutions
  grep -r "function_name" backend/ frontend/
  find . -name "*.py" -o -name "*.vue" -o -name "*.ts" | xargs grep -l "keyword"
  ```
- **Check existing models/APIs/components** - they may already provide what you need
- **Extend existing functionality** rather than creating parallel implementations
- **Ask: "Has this problem been solved already?"** before writing new code

### 2. **Modularity & Loose Coupling - Keep Things Separate**
- **Single Responsibility**: Each module/component should do ONE thing well
- **Clear Interfaces**: Define clean boundaries between frontend/backend/database
- **Dependency Injection**: Pass dependencies rather than hard-coding them
- **Event-Driven**: Use events/signals instead of direct coupling where possible
- **Configuration Over Code**: Make behavior configurable rather than hardcoded
- **AVOID HARDCODING VALUES**: See previous line
- **Avoid Backend Logic in Frontend**: Keep business logic in the backend

### 3. **Architectural Awareness**
- **ALWAYS** refer to `docs/architecture/ArchitecturePlan.md` before making structural changes
- Understand the **dynamic system prompt architecture** - this is the core innovation
- Respect the **3-layer architecture**: Frontend ↔ Backend ↔ Database

### 4. **Database Models & Data Structure**
- **All data models are already defined** - use them correctly:
  - `Persona`: AI persona configurations with templates
  - `Module`: Simple (static) and Advanced (Python script) modules  
  - `Conversation` & `Message`: Chat history with relationships
- **Use PostgreSQL UUIDs** - no integer IDs for primary keys
- **Test with real database** - integration tests preferred over complex mocking

### 5. **Module System Understanding**
- **Template Resolution**: `@module_name` placeholders get resolved at runtime
- **Advanced Modules**: Python scripts with trigger patterns and execution timing
- **Dependency Chain**: Modules can reference other modules - avoid circular dependencies

### 6. **Testing Strategy** 
- **Current Status**: 81/81 tests passing, 100% pass rate
- **Model Tests**: All database models fully tested and working (17/17)
- **API Tests**: All database API endpoints working (7/7)  
- **Chat API Tests**: Complete chat functionality tested (14/14)
- **Connection Tests**: Provider connection testing (12/12)
- **Integration Tests**: Use real `project2501_test` database with comprehensive mocking
- **TDD Approach**: All new features developed test-first

### 7. **Technology Versions** (Keep Updated)
- **Pydantic**: 2.11.7 (latest stable - v3 doesn't exist yet)
- **SQLAlchemy**: 2.0.23 (modern syntax, no deprecated imports)
- **FastAPI**: 0.104.1
- **Vue**: 3.5.18 with Composition API

### 8. **Code Organization**
- **Backend**: Follow existing structure in `backend/app/`
- **Frontend**: Use existing component structure and golden ratio layout
- **API Endpoints**: RESTful, prefix with `/api`
- **Database**: Use existing connection management and fixtures

### 9. **Configuration Management**
- **Environment**: Use `.env` file in backend/ directory
- **Database**: PostgreSQL connection via environment variables
- **Settings**: Pydantic BaseSettings with proper validation
- **Testing**: Separate test database configuration

## ⚡ Development Workflow

### For New Features:

#### **CRITICAL: Search First, Code Second**
```bash
# Before implementing ANYTHING, search for existing solutions:
grep -r "feature_name" backend/ frontend/
grep -r "similar_function" .
find . -name "*.py" -o -name "*.vue" | xargs grep -i "keyword"
```

#### **Frontend-First Development Approach:**
1. **Understand the Architecture** - Read relevant docs/architecture/ files
2. **Search for Existing Solutions** - Check if feature/component already exists
3. **Design Frontend First** - Create UI components and forms first
   - Mock the data structure in frontend
   - Define what user interactions are needed
   - Determine what data needs to be sent/received
4. **Define API Contracts** - Based on frontend needs, define API endpoints
5. **Check/Update Database Models** - Ensure models support frontend requirements
6. **Write Tests** - Based on frontend needs and API contracts
7. **Implement Backend API** - Build endpoints that satisfy frontend contracts
8. **Integration Testing** - Connect frontend to real backend
9. **End-to-End Testing** - Verify complete user workflows

#### **Frontend-First Benefits:**
- **User-Centric**: UI drives the data requirements
- **Clear Contracts**: Frontend defines exactly what API should provide
- **Better UX**: User experience is designed first, not retrofitted
- **Avoid Over-Engineering**: Backend only builds what frontend actually needs

### For Bug Fixes:
1. **Search for Related Code** - Find all files/functions related to the bug
2. **Write Failing Test** - Reproduce the issue
3. **Fix Implementation** - Follow existing code patterns  
4. **Verify All Tests Pass** - Run full test suite
5. **Test Integration** - Verify with real database and frontend

### Before Committing:
```bash
# Backend
cd backend && pytest                    # All tests must pass
cd backend && python app/main.py      # Server must start without errors

# Frontend  
cd frontend && npm run lint            # Linting must pass
cd frontend && npm run format          # Format code
cd frontend && npm run test:unit       # Tests must pass (when they exist)
```

## 🎯 Current Implementation Status

### ✅ **Working (Production Ready)**:
- **Core Database Models**: All models working with PostgreSQL + UUIDs
- **Backend API Structure**: FastAPI app with proper configuration
- **Database Connection**: Connection pooling, testing, error handling
- **Frontend UI Framework**: Vue 3 app with golden ratio layout and cyberpunk theme
- **Test Infrastructure**: Comprehensive test suite (**396/396 passing**)
- **Development Environment**: Scripts, conda environment, modern dependencies

#### **🚀 COMPLETE: Full Chat Infrastructure**
- **Chat API Endpoints**: `/api/chat/send` and `/api/chat/stream` with Server-Sent Events ✅
- **Connection Testing**: `/api/connections/ollama/test` and `/api/connections/openai/test` ✅
- **AI Provider Services**: Full Ollama and OpenAI integration with streaming support ✅
- **Provider Type System**: Seamless conversion between API and service layer enums ✅
- **Frontend-Backend Integration**: Complete chat functionality with all controls working ✅
- **Settings Architecture**: Provider settings passed in requests (no backend duplication) ✅
- **Error Handling**: Comprehensive authentication, connection, and validation error handling ✅
- **TDD Coverage**: All 396 integration tests passing, including 14 chat, 14 conversation, and 27 message tests ✅

#### **Chat System Architecture:**
**Frontend-Only Settings Storage**: All provider connection settings (Ollama, OpenAI) stored in browser localStorage only.
**Request-Based Configuration**: Settings passed as `provider_settings` field in every chat request.
**No Backend Duplication**: Backend extracts settings from request payload, no backend storage.
**Complete Control Flow**: Frontend (localStorage) → Request Payload → Backend → AI Provider

**LocalStorage Keys:**
- `'chat-controls'`: All chat parameters (temperature, tokens, stream, provider selection, etc.)
- `'ollama-connection'`: Ollama host, model, route, and options
- `'openai-connection'`: OpenAI API key, base URL, model, organization, etc.

#### **Backend API Endpoints Summary:**
```
Database:      GET  /api/database/test                    # Database connection test
Modules:       GET  /api/modules/                         # List modules
               POST /api/modules/                         # Create module
Personas:      GET  /api/personas/                        # List personas  
               POST /api/personas/                        # Create persona
Templates:     POST /api/templates/resolve                # Resolve @module_name references
               GET  /api/templates/modules/available      # List available modules
               POST /api/templates/validate               # Validate template syntax
Chat:          POST /api/chat/send                        # Complete chat response (with persona_id)
               POST /api/chat/stream                      # Streaming chat response (with persona_id)
Connections:   POST /api/connections/ollama/test          # Test Ollama connection
               POST /api/connections/openai/test          # Test OpenAI connection
Conversations: GET  /api/conversations/by-persona/{id}    # Get conversation by persona
               GET  /api/conversations/{id}               # Get conversation by ID
               POST /api/conversations                    # Create conversation
               PUT  /api/conversations/{id}               # Update conversation
               DELETE /api/conversations/{id}             # Delete conversation (cascade)
Messages:      GET  /api/messages/by-conversation/{id}   # List messages in conversation
               GET  /api/messages/{id}                   # Get message by ID
               POST /api/messages                        # Create message (with thinking)
               PUT  /api/messages/{id}                   # Update message content/thinking
               DELETE /api/messages/{id}                 # Delete message
```

**Chat Request Format:**
```json
{
  "message": "Hello!",
  "provider": "ollama" | "openai", 
  "stream": true | false,
  "persona_id": "uuid-string",         // Persona for system prompt resolution
  "provider_settings": {
    "host": "http://localhost:11434",  // From localStorage
    "model": "dolphin-llama3"          // From frontend connection settings
  },
  "chat_controls": {
    "temperature": 0.7,                // From frontend chat controls
    "max_tokens": 1024,
    "stream": true
  }
}
```

#### **✅ WORKING: Complete Chat System**
- **Provider Switching**: Ollama ↔ OpenAI provider selection working perfectly ✅
- **Stream Controls**: Toggle between streaming/non-streaming responses ✅
- **Chat Controls Integration**: Temperature, tokens, penalties, all frontend settings applied ✅
- **Connection Settings**: Frontend localStorage → request payload architecture ✅
- **Persona Integration**: System prompts from selected personas ✅
- **Real-time Chat**: Full bidirectional streaming chat interface ✅

#### **🗃️ COMPLETE: Conversation Persistence System**
- **Conversation Storage**: Full CRUD API for persistent conversations with database storage ✅
- **Message Storage**: Messages stored with thinking content, token counts, and metadata ✅
- **Persona-Conversation Relationships**: Each persona has an ongoing conversation ✅
- **Cascade Deletion**: Deleting conversation automatically deletes all associated messages ✅
- **UUID Primary Keys**: All conversation and message IDs use UUIDs for better security ✅
- **Database Migrations**: Proper schema migrations for thinking field and persona relationships ✅
- **TDD Implementation**: All 14 conversation API tests passing with comprehensive coverage ✅

#### **Conversation System Architecture:**
**Database Models**:
- `Conversation`: UUID primary key, title, persona_id (FK), provider info, timestamps
- `Message`: UUID primary key, conversation_id (FK with CASCADE), role, content, thinking, token counts
- **Relationships**: One-to-many (Conversation → Messages), many-to-one (Conversation → Persona)

**API Endpoints**:
- `GET /api/conversations/by-persona/{persona_id}` - Get active conversation for persona
- `GET /api/conversations/{id}` - Get specific conversation with all messages
- `POST /api/conversations` - Create new conversation
- `PUT /api/conversations/{id}` - Update conversation (title)  
- `DELETE /api/conversations/{id}` - Delete conversation and cascade delete all messages

**Key Features**:
- **Message Thinking**: AI reasoning content stored separately from main response
- **Cascade Deletion**: Database-level foreign key constraint ensures message cleanup
- **Provider Tracking**: Snapshots of AI provider settings used for conversation
- **Full Message History**: Complete conversation state with ordering and metadata

#### **💬 COMPLETE: Message CRUD API System (Phase 3.1 - DONE)**
- **Message Storage**: Full CRUD API for individual message management with thinking support ✅
- **UUID Primary Keys**: All message IDs use UUIDs for consistency and security ✅
- **Thinking Content**: Separate storage for AI reasoning alongside main response content ✅
- **Token Tracking**: Input/output token counts for usage monitoring and billing ✅
- **Metadata Support**: Flexible extra_data JSON field for additional message information ✅
- **Role Validation**: Strict validation for message roles (user, assistant, system) ✅
- **Conversation Integration**: Messages properly linked to conversations with cascade deletion ✅
- **TDD Implementation**: All 27 message API tests passing with comprehensive coverage ✅

#### **Message API Architecture:**
**Database Model**:
- `Message`: UUID primary key, conversation_id (FK with CASCADE), role, content, thinking, extra_data, token counts
- **Relationships**: Many-to-one (Message → Conversation), proper cascade deletion

**API Endpoints**:
- `POST /api/messages` - Create new message with validation and thinking support
- `GET /api/messages/{id}` - Get specific message by ID
- `GET /api/messages/by-conversation/{conversation_id}` - List all messages in conversation (ordered)
- `PUT /api/messages/{id}` - Update message content, thinking, tokens, or metadata
- `DELETE /api/messages/{id}` - Delete message (automatically removes from conversation)

**Key Features**:
- **Thinking Support**: AI reasoning content stored separately from main response
- **Partial Updates**: Update only specific fields (content, thinking, tokens, metadata)
- **Token Tracking**: Track input/output token usage for billing and monitoring
- **Role System**: Validates user/assistant/system roles with proper enum handling
- **Database Migration**: Converted from integer to UUID primary keys for security
- **Cascade Integration**: Messages properly integrate with conversation lifecycle

#### **🎯 COMPLETE: Advanced Chat UI Features**
- **Frontend Chat Integration**: Complete connection between UI and conversation persistence systems ✅
- **In-Place Message Editing**: Full UI for editing message content and thinking sections with save/cancel ✅
- **Edit/Delete Message Actions**: Contextual buttons with existing card styling, positioned in message corners ✅
- **Markdown Rendering**: Real-time markdown parsing for formatted messages with toggle control ✅
- **Chat Options Menu**: Collapsible panel system for markdown toggle and destructive actions ✅
- **Auto-Scroll**: Intelligent scroll-to-bottom for new messages and streaming responses ✅
- **Confirmation Dialogs**: Safety prompts for destructive actions like clearing conversations ✅

#### **Advanced Chat UI Architecture:**
**In-Place Editing System**:
- **Edit Mode Toggle**: Messages become directly editable with textarea inputs
- **Content + Thinking**: Both main message and AI reasoning content can be edited separately
- **Action Buttons**: Edit/delete buttons appear on hover, positioned in message bubble corners
- **Save/Cancel Controls**: Replace edit/delete with save/cancel buttons during editing
- **Database Sync**: All edits immediately persist to database with proper error handling
- **Visual Feedback**: Active editing state with highlighted borders and button state changes

**Markdown Rendering System**:
- **Toggle Control**: User can switch between raw markdown and rendered HTML in real-time
- **Library Integration**: Uses `marked` library with breaks enabled for line break preservation
- **Custom Styling**: Compact markdown CSS designed to match plain text density
- **Scoped Styles**: Uses `:deep()` selectors to penetrate Vue's scoped styles for v-html content
- **Line Break Preservation**: Post-processing to maintain empty lines from original text
- **Conditional Formatting**: `white-space: pre-wrap` only applied to non-markdown content

**Chat Options Panel**:
- **Panel System**: Reuses existing chat controls UI pattern for consistency
- **Dual Purpose**: Settings button opens chat controls, menu button opens chat options
- **Toggle Architecture**: Smart button behavior - same button closes panel if already showing that type
- **Menu Options**: Markdown rendering toggle with checkbox state, clear chat with confirmation
- **Safety Features**: Clear chat requires confirmation dialog warning of permanent deletion
- **Visual Integration**: Matches existing cyberpunk theme with proper hover states

**Auto-Scroll Features**:
- **Smart Triggers**: Scrolls on new messages, during streaming, after sending, and on message updates
- **Reactive Watching**: Deep watches message array and streaming state for automatic scrolling
- **Performance Optimized**: Uses `nextTick()` to ensure DOM updates before scrolling
- **Streaming Integration**: Real-time scroll during AI response streaming
- **User Experience**: Always shows latest content without manual scrolling needed

**Key Implementation Details**:
- **Message Actions**: Edit/delete buttons use existing `card-icon-btn` styles from `@/assets/card.css`
- **Button Positioning**: Positioned in lower right corner of message bubbles with opacity transitions
- **State Management**: Reactive editing state with proper cleanup and error handling
- **Markdown Library**: `marked@16.2.0` with `@types/marked@5.0.2` for TypeScript support
- **CSS Architecture**: `:deep()` selectors for scoped style penetration of dynamically generated content

#### **🧠 COMPLETE: Cognitive Engine - Dynamic System Prompt Architecture**
- **Module Resolution Service**: Core engine for resolving `@module_name` references in templates ✅
- **Template Resolution API**: REST endpoints for template validation and resolution ✅
- **Chat Integration**: Full integration with Ollama/OpenAI providers using resolved system prompts ✅
- **Centralized Provider Architecture**: Abstracted system prompt handling across all AI providers ✅
- **Comprehensive Testing**: 330/330 tests passing including 24 new cognitive engine tests ✅
- **Error Handling**: Proper handling of missing modules, circular dependencies, inactive personas ✅

#### **Cognitive Engine Architecture:**
**Core Innovation - Dynamic System Prompt Architecture**:
The system treats persona templates as **living, modular heads-up displays** that stay persistently visible to AI throughout conversations, solving the fundamental limitations of static system prompts and context rot.

**Module Resolution Pipeline**:
1. **Template Parsing**: Extract `@module_name` references using regex pattern `r'@([a-z][a-z0-9_]{0,49})'`
2. **Database Lookup**: Fetch active modules from database with validation
3. **Recursive Resolution**: Handle nested module references (modules that reference other modules)
4. **Circular Dependency Detection**: Prevent infinite loops with resolution stack tracking
5. **Content Assembly**: Replace all references with resolved content and return final system prompt

**API Endpoints**:
- `POST /api/templates/resolve` - Resolve template with module references and return warnings
- `GET /api/templates/modules/available` - List available modules for autocomplete/validation
- `POST /api/templates/validate` - Validate template without full resolution (fast validation)

**Chat Integration**:
- **Enhanced Chat Models**: Added `persona_id` to requests and `system_prompt` to provider requests
- **Automatic Resolution**: Chat endpoints automatically resolve persona templates before sending to AI
- **Debug Support**: Resolved system prompts returned in responses for development transparency
- **Provider Abstraction**: Centralized system prompt handling in base `AIProvider` class
- **Backward Compatibility**: Legacy `system_or_instructions` still supported

**Key Features**:
- **Strict Naming Policy**: Module names must match `^[a-z][a-z0-9_]*$` (max 50 chars)
- **Missing Module Handling**: Keep @module_name string as is
- **Maximum Recursion Depth**: Prevents infinite resolution with configurable depth limit (10)
- **Active Module Filtering**: Only active modules are resolved, inactive ones treated as missing
- **Comprehensive Warnings**: Detailed warning system for missing modules, circular dependencies, depth limits

**Implementation Highlights**:
- **Test-Driven Development**: All backend features implemented following TDD with comprehensive test coverage
- **Clean Architecture**: Proper separation between template parsing, database access, and provider integration  
- **Future-Ready**: Architecture prepared for advanced modules (Python scripts, dynamic content)
- **Performance Optimized**: Efficient recursive resolution with proper cycle detection
- **Error Resilient**: Graceful handling of all edge cases without breaking chat functionality

### ✅ **COMPLETE: Self-Reflecting AI System**

#### **🧠 COMPLETE: AI Self-Reflection & Introspection**
- **reflect() Function**: AI can analyze its own thoughts, responses, and behavior ✅
- **Comprehensive Safety**: Depth limiting, recursion prevention, timing restrictions ✅
- **Flexible Parameters**: Full control over temperature, max_tokens, and other AI settings ✅
- **Timing Integration**: Works with BEFORE, AFTER, and CUSTOM module timing ✅
- **Cross-Module Reflection**: Modules can safely reflect through other modules ✅
- **Complete Testing**: 461/461 tests passing including comprehensive reflection tests ✅

#### **Self-Reflection Architecture:**
**Core Innovation - AI Self-Awareness**:
The `ctx.reflect()` function enables AI personas to introspect on their own thoughts, responses, and behavior patterns, creating truly self-aware and adaptive AI systems.

**Safety Mechanisms**:
1. **Maximum Reflection Depth**: 3 levels to prevent infinite loops
2. **Module Resolution Stack Tracking**: Prevents direct recursion during nested reflections
3. **Timing Restrictions**: No nested BEFORE timing reflections for stability
4. **Audit Trail**: Complete reflection chain tracking for transparency and debugging
5. **Graceful Fallbacks**: Safe error handling with informative messages

**Usage Examples**:
```python
# Self-assessment after AI response (AFTER timing)
quality = ctx.reflect("Rate this response quality 1-10 and suggest improvements", max_tokens=50)

# Adaptive behavior based on context (BEFORE timing)  
tone = ctx.reflect("What communication style would work best here?", recent_context, temperature=0.1)

# Cross-module analysis with specific provider
analysis = ctx.reflect("openai", "gpt-4", "Analyze this conversation pattern", chat_history)

# Creative self-reflection with custom parameters
idea = ctx.reflect("Generate a creative approach", temperature=0.8, max_tokens=200)
```

**Real-World Applications**:
- **Response Quality Assessment**: AI evaluates and improves its own responses
- **Mood Adaptation**: AI adjusts communication style based on conversation context  
- **Behavior Analysis**: AI reflects on interaction patterns and adjusts accordingly
- **Creative Problem Solving**: AI uses introspection for innovative solutions

### ✅ **COMPLETE: Advanced Modules Implementation**

#### **🎯 COMPLETE: Advanced Modules System**
- **Script Execution Engine**: RestrictedPython sandbox with security validation ✅
- **Plugin Registry**: Auto-discovery decorator system with 15+ built-in functions ✅
- **Execution Context**: Rich context with conversation/database access and plugin injection ✅
- **Trigger System**: Keyword/regex pattern matching for conditional execution ✅
- **Variable Resolution**: `${variable}` system separate from `@module_name` references ✅
- **Module Resolution**: Enhanced module resolver with advanced module support ✅
- **Complete Testing**: 66 new tests added, all 396 tests passing ✅

#### **Advanced Modules Architecture:**
**Core Innovation - Dynamic Script Execution**:
Advanced modules execute Python scripts in secure RestrictedPython sandbox with full access to conversation context, database, and extensible plugin system.

**Script Execution Pipeline**:
1. **Trigger Check**: Pattern matching against conversation context (`last_user_message`)
2. **Security Validation**: RestrictedPython compile with import restrictions and timeout
3. **Plugin Injection**: Auto-discovered functions available via execution context
4. **Script Execution**: Secure execution with conversation and database access
5. **Output Extraction**: Multiple named outputs captured from script globals
6. **Variable Resolution**: `${variable}` patterns replaced with script results

**Plugin System**:
```python
@plugin_registry.register("get_current_time")
def get_current_time(format: str = "%Y-%m-%d %H:%M") -> str:
    return datetime.now().strftime(format)
```

**15+ Built-in Plugin Functions**:
- **AI Generation Functions**: `generate` (flexible AI content generation), `reflect` (self-introspection and analysis)
- **Time Functions**: `get_current_time`, `get_relative_time`, `format_duration`, `is_business_hours`, `get_timezone_info`
- **Conversation Functions**: `get_message_count`, `get_recent_messages`, `get_conversation_summary`, `get_persona_info`
- **Utility Functions**: `generate_uuid`, `log_debug`, `validate_email`, `format_number`, `get_random_choice`

**Example Advanced Module**:
```python
# Module Content:
"Hello! I'm ${name} and it's ${current_time}. Messages: ${msg_count}"

# Module Script:
"""
name = "AVA"
current_time = ctx.get_current_time("%H:%M")
msg_count = ctx.get_message_count()
"""

# Resolved Result:
"Hello! I'm AVA and it's 14:30. Messages: 15"
```

**Implementation Highlights**:
- **Test-Driven Development**: All features implemented with comprehensive test coverage first
- **Security-First**: RestrictedPython with import restrictions, timeouts, and validation
- **Extensible Design**: Plugin system allows easy addition of new script functions
- **Context-Rich**: Scripts receive full conversation context and database session
- **Error-Resilient**: Comprehensive error handling with user-friendly warnings
- **Performance-Optimized**: Efficient recursive resolution with cycle detection

### ✅ **OPERATIONAL STATUS**:
**Advanced Modules are now fully operational in the chat system!** ✅

Users can create advanced modules with Python scripts that:
- Execute securely in RestrictedPython sandbox
- Access 14+ built-in plugin functions (time, conversation data, utilities)
- Use `${variable}` syntax for dynamic content generation
- Support trigger patterns for conditional execution
- Integrate seamlessly with existing `@module_name` system

### 🚀 **Future Development Priorities**:
- **Frontend Integration**: Template editor with @module autocomplete and ${variable} validation
- **Debug Screen**: Visual display of resolved system prompts and script outputs
- **Import/Export System**: JSON and PNG-embedded persona sharing with advanced modules
- **Advanced Chat Features**: File uploads, tool calling, conversation memory
- **Module Marketplace**: Shared library of community-created advanced modules

### 💡 **Key Implementation Notes**:
- **The core innovation** is the dynamic system prompt architecture - both simple and advanced modules fully operational! ✅
- **Self-Reflecting AI System is complete** - full AI introspection with `ctx.reflect()` and comprehensive safety ✅
- **Advanced Modules System is complete** - full Python script execution with RestrictedPython sandbox ✅
- **Cognitive Engine is complete** - full `@module_name` and `${variable}` resolution with recursive support ✅
- **Plugin System is complete** - auto-discovery decorator registry with 15+ built-in functions ✅
- **Complete chat system is working** - full Ollama/OpenAI integration with streaming and persona support ✅
- **Conversation persistence is complete** - full CRUD API with database storage and thinking support ✅
- **Message CRUD system is complete** - full message management with thinking, tokens, and metadata ✅
- **Advanced chat UI is complete** - in-place editing, markdown rendering, auto-scroll, and options menu ✅
- **Provider abstraction is clean** - centralized system prompt handling across all AI providers ✅
- **Frontend-centric architecture** - all settings managed in browser, passed via requests ✅
- **Database models are solid** - UUIDs, proper relationships, cascade deletion working ✅
- **Test coverage is excellent** - 461/461 passing tests, maintain this standard ✅
- **Architecture is well-planned** - follow the existing design patterns ✅
- **UI patterns are consistent** - reuses existing components and styling for cohesive experience ✅

### 🏗️ **Chat Architecture Patterns (FOLLOW THESE)**:
- **Settings Storage**: Frontend localStorage only, never duplicate in backend
- **Request Payload**: Include all necessary settings in each request
- **Stateless Backend**: Backend extracts settings from requests, no session storage
- **Component Sync**: Use same localStorage keys across components
- **Error Handling**: Clear user messages for missing/invalid settings

### 🔄 **Modularity & Coupling Guidelines**:
- **Components Should Be Swappable**: Any module should be replaceable without breaking others
- **Interface-Driven Development**: Define clear contracts between components
- **Avoid Direct Dependencies**: Use dependency injection and configuration
- **Event-Driven Architecture**: Components communicate through events, not direct calls
- **Single Source of Truth**: Each piece of data should have one authoritative source
- **Separation of Concerns**: UI logic ≠ Business logic ≠ Data logic

### 🔍 **Before You Code Checklist**:
```bash
# Run these commands before implementing ANY feature:
1. grep -r "similar_functionality" . --include="*.py" --include="*.vue" --include="*.ts"
2. find . -name "*.py" -o -name "*.vue" | xargs grep -l "related_keyword"
3. Check backend/app/models/ for existing data structures
4. Check frontend/src/components/ for existing UI components  
5. Check backend/app/api/ for existing endpoints
6. Ask: "Can I extend existing code instead of writing new code?"
```

## 📚 Additional Resources

- `docs/architecture/ArchitecturePlan.md` - Complete architectural specification
- `backend/tests/` - Comprehensive test examples
- `backend/app/models/` - Data model reference implementations  
- `frontend/src/components/` - UI component examples