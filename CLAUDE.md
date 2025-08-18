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
conda activate project2501
cd backend
pytest                    # Run all tests (55 tests)
pytest tests/unit/        # Unit tests only
pytest tests/integration/ # Integration tests only
pytest -v                # Verbose output
```

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
- **Current Status**: 55/55 tests passing, 100% pass rate
- **Model Tests**: All database models fully tested and working (17/17)
- **API Tests**: All database API endpoints working (7/7)  
- **Integration Tests**: Use real `project2501_test` database
- **Avoid Complex Mocking**: Prefer integration tests for database operations

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
- **Test Infrastructure**: Comprehensive test suite (55/55 passing)
- **Development Environment**: Scripts, conda environment, modern dependencies

### 🚧 **Next Development Priorities**:
- **Cognitive Engine**: Template resolution and module execution system
- **Module Sandbox**: Secure Python script execution for Advanced modules
- **AI Provider Integration**: OpenAI, Anthropic, local model interfaces
- **WebSocket Integration**: Real-time chat updates
- **Persona/Module CRUD**: Full create, read, update, delete operations
- **Import/Export System**: JSON and PNG-embedded persona sharing

### 💡 **Key Implementation Notes**:
- **The core innovation** is the dynamic system prompt architecture - keep this central
- **All critical infrastructure is working** - focus on feature development
- **Database models are solid** - use them as the foundation
- **Test coverage is excellent** - maintain this standard
- **Architecture is well-planned** - follow the existing design

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