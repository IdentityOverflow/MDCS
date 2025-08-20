# Project 2501 - Cognitive Systems Framework
## Design Collaboration Scratchpad

*"Building dynamic cognitive architectures through scriptable modules"*

---

## 🎯 Project Vision

**Project 2501** is a cognitive systems framework that revolutionizes how we interact with AI by solving the fundamental limitations of static system prompts and context rot.

### The Problem
Traditional LLM interactions use static system prompts that get buried or lost as conversations grow, leading to:
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
- **Simple Modules**: Static text templates (personality, static instructions, persisten information, etc.).
- **Advanced Modules**: Can laverage python scripts that update the module content dynamically (memory, context, time, adaptive reasoning, etc.).
- **Self-Modifying**: AI can update some of its own modules, creating evolving **personas**.

### Key Innovation
This enables **infinite conversations with adaptive memory**, **composable AI personas**, and **self-evolving cognitive architectures** - essentially creating a framework for building any type of AI agent or interactive system imaginable.

### Vision
A model-agnostic platform where users can design, share, and evolve sophisticated AI personas through an intuitive web interface, powered by a modular Python backend.

---

## 📐 Architecture Overview

### System Architecture Layers

**Data Layer**
- **Database**: PostgreSQL (with pgvector extension)
  - **Relational data**: personas, modules, templates, conversations
  - **Vector storage**: Semantic search capabilities (future plans)
  - **ACID compliance** for data integrity
  - **Excellent Python ecosystem support**

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
- Unified interface for AI providers (OpenAI, Anthropic, local models)
- Token counting and rate limiting
- Response streaming and error handling
- Model-specific optimizations

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
- Python scripted content with dynamic behavior
- Conditional trigger system (keyword-based activation)
- Multiple execution timing options:
  - After AI Response
  - Before AI Response  
  - On demand
- Access to conversation state, history, and helper functions
- Use case examples: Memory management, dynamic context, self-modifying behavior

### Template System
- Uses placeholder syntax: `{module_name}` (will be change to @module_name )
- Template defines how modules are arranged in final prompt
- Modules are resolved at runtime before sending to AI
- Available modules shown as a list of drag-and-drop insetable items (will be cahanged to a suggestion system based on available modules)
- Support for saved/loaded template presets

### Module Features Observed
- **Trigger Words/Phrases**: Modules can activate based on conversation content
- **Conditional Logic**: Python scripts can implement complex decision making
- **State Management**: Access to conversation history, exchange counts, etc.
- **Helper Functions**: Built-in utilities for common operations
- **Execution Control**: Fine-grained control over when modules update

### Module Dependencies & Execution
- Modules can reference other modules using `{module_name}` syntax (will be @module_name )
- Recursive call detection prevents infinite loops
- Missing dependency validation with user warnings
- User responsibility for architectural coherence

### Performance & Timing
- Background execution for post-response modules (e.g., memory updates)
- Fast modules (time, static data) vs AI-dependent modules
- Execution timing options provide performance optimization opportunities

---

## 📁 Project Structure

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

## 🏗️ Development Approach
*Learning from previous technical debt issues*

### Core Problem Identified
Previous implementation suffered from **AI context loss during development** - each Claude Code session lost architectural awareness, leading to:
- Unnecessary reimplementation
- Tight coupling between modules
- Frontend solutions to backend problems
- Architectural drift over time

### Proposed Solutions

**Test-Driven Development (TDD)**
- Write tests first to define expected behavior
- Comprehensive test coverage prevents regression
- Tests serve as living documentation of system behavior
- Forces modular, testable design

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
