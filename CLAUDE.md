# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🎯 Project Vision: Project 2501 - Cognitive Systems Framework

**Core Innovation**: Dynamic System Prompt Architecture that treats the system prompt as a **living, modular heads-up display** that stays persistently visible to AI throughout any conversation length, solving the fundamental limitations of static system prompts and context rot.

### Key Components:
- **Simple Modules**: Static text templates (personalities, instructions, tools)
- **Advanced Modules**: Python scripts that update dynamically (memory, context, time, custom logic)
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

**Template System**: Uses placeholder syntax `{module_name}` - modules resolved at runtime before sending to AI

**Advanced Module Features**:
- **Trigger Words/Phrases**: Modules activate based on conversation content
- **Conditional Logic**: Python scripts implement complex decision making
- **State Management**: Access to conversation history, exchange counts, etc.
- **Execution Timing**: After AI Response, Before AI Response, On demand

**Module Dependencies**: 
- Modules reference other modules using `{module_name}` syntax
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
│   │   │   ├── config.py        # Configuration management
│   │   ├── models/      # Database models (SQLAlchemy)
│   │   │   ├── persona.py       # AI personas
│   │   │   ├── module.py        # Simple & Advanced modules
│   │   │   ├── conversation.py  # Chat conversations & messages
│   │   │   └── base.py          # Base model with common fields
│   │   ├── api/         # REST API endpoints
│   │   │   └── database.py      # Database test/info endpoints
│   │   ├── database/    # Database connection management
│   │   │   └── connection.py    # Connection pooling & testing
│   │   └── services/    # Business logic services (future)
│   ├── tests/          # Comprehensive test suite
│   │   ├── unit/       # Unit tests (55 tests, all passing)
│   │   ├── integration/ # Integration tests with real DB
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
- **Testing**: pytest 7.4.3 with PostgreSQL integration
- **Environment**: conda environment `project2501`

### Frontend (Vue 3)  
- **Framework**: Vue 3.5.18 with TypeScript
- **State**: Pinia 3.0.3
- **Routing**: Vue Router 4.5.1
- **Testing**: Vitest 3.2.4
- **Build**: Vite 7.0.6

### Database
- **Primary**: PostgreSQL with pgvector extension
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
# Run all tests (225+ tests passing)
pytest                    # Run all tests
pytest -v                # Verbose output (RECOMMENDED - shows all test details)

# Run specific test categories
pytest tests/unit/        # Unit tests only (152 tests)
pytest tests/integration/ # Integration tests only (73 tests)

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
- **Unit Tests**: Fast, isolated tests for individual functions (no database)
- **Integration Tests**: Full HTTP API tests using `project2501_test` database with proper cleanup
- **TDD Approach**: Write failing tests first, then implement to make them pass

**Database Isolation**:
- **Frontend**: Connects to main database (`project2501` via backend server)
- **Tests**: Use separate test database (`project2501_test`) with automatic cleanup
- **No Cross-Contamination**: Tests never pollute the main database

**Database**:
- Main DB: `project2501` 
- Test DB: `project2501_test`
- User: `project2501` with password in `.env`
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
- Components: Personas, Modules, Settings, Tools, Files, Scratchpad views

## 🚨 Critical Development Principles (Anti-Technical Debt)

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
- **Template Resolution**: `{module_name}` placeholders get resolved at runtime
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
- **Test Infrastructure**: Comprehensive test suite (**90/90 passing**)
- **Development Environment**: Scripts, conda environment, modern dependencies

#### **🚀 COMPLETE: Full Chat Infrastructure (Phase 2 - DONE)**
- **Chat API Endpoints**: `/api/chat/send` and `/api/chat/stream` with Server-Sent Events ✅
- **Connection Testing**: `/api/connections/ollama/test` and `/api/connections/openai/test` ✅
- **AI Provider Services**: Full Ollama and OpenAI integration with streaming support ✅
- **Provider Type System**: Seamless conversion between API and service layer enums ✅
- **Frontend-Backend Integration**: Complete chat functionality with all controls working ✅
- **Settings Architecture**: Provider settings passed in requests (no backend duplication) ✅
- **Error Handling**: Comprehensive authentication, connection, and validation error handling ✅
- **TDD Coverage**: All 90 integration tests passing, including 14 chat-specific tests ✅

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
Database:     GET  /api/database/test              # Database connection test
Modules:      GET  /api/modules/                   # List modules
              POST /api/modules/                   # Create module
Personas:     GET  /api/personas/                  # List personas  
              POST /api/personas/                  # Create persona
Chat:         POST /api/chat/send                  # Complete chat response
              POST /api/chat/stream                # Streaming chat response
Connections:  POST /api/connections/ollama/test    # Test Ollama connection
              POST /api/connections/openai/test    # Test OpenAI connection
```

**Chat Request Format:**
```json
{
  "message": "Hello!",
  "provider": "ollama" | "openai", 
  "stream": true | false,
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

### 🚧 **Next Development Priorities (Phase 3)**:
- **Cognitive Engine**: Template resolution and module execution system
- **Module Sandbox**: Secure Python script execution for Advanced modules
- **Import/Export System**: JSON and PNG-embedded persona sharing
- **Advanced Chat Features**: File uploads, tool calling, conversation memory

### 💡 **Key Implementation Notes**:
- **The core innovation** is the dynamic system prompt architecture - keep this central
- **Complete chat system is working** - full Ollama/OpenAI integration with streaming
- **Frontend-centric architecture** - all settings managed in browser, passed via requests
- **Database models are solid** - use them as the foundation for conversation storage
- **Test coverage is excellent** - 90/90 passing tests, maintain this standard
- **Architecture is well-planned** - follow the existing design patterns

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