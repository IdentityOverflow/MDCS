# Services Layer Refactoring Plan

## 🎯 **Goal: Clean & Modular Backend Architecture**

Transform the current monolithic service files into a clean, maintainable, modular architecture following domain-driven design principles.

## 📊 **Current State Analysis (2025-01-09)**

### **File Size Issues**
- `staged_module_resolver_base.py`: **1,073 lines** 😱
- `staged_module_resolver.py`: **640 lines** 
- `openai_service_base.py`: **573 lines**
- `system_prompt_debug.py`: **469 lines**
- `ollama_service_base.py`: **430 lines**
- Plus inheritance duplication patterns

### **Current Problems**
1. **Massive monoliths** - Single files handling too many concerns
2. **Base + Enhanced duplication** - Inheritance creating complexity
3. **Mixed concerns** - Protocol handling, session management, template resolution all mixed together
4. **Hard to maintain** - Large files difficult to understand and modify
5. **Testing challenges** - Monolithic files make unit testing complex

### **Current Services Directory**
```
app/services/
├── ai_providers.py              (170 lines) - Factory pattern
├── chat_session_manager.py      (310 lines) - Session management  
├── exceptions.py                (20 lines) - Shared exceptions
├── ollama_service.py            (331 lines) - Enhanced Ollama with cancellation
├── ollama_service_base.py       (430 lines) - Base Ollama implementation
├── openai_service.py            (333 lines) - Enhanced OpenAI with cancellation
├── openai_service_base.py       (573 lines) - Base OpenAI implementation
├── staged_module_resolver.py    (640 lines) - Enhanced resolver with cancellation
├── staged_module_resolver_base.py (1,073 lines) - Base resolver implementation
├── streaming_accumulator.py     (318 lines) - Stream conversion
├── system_prompt_debug.py       (469 lines) - Debug utilities
└── system_prompt_state.py       (371 lines) - State management
```

## 🏗️ **Target Architecture - REVISED**

### **Incremental Refactoring Within Existing Structure**

```
backend/app/
├── api/           # FastAPI endpoints - KEEP AS IS ✅
├── core/          # Script engine, config, analysis - KEEP AS IS ✅  
├── database/      # Database connections, migrations - KEEP AS IS ✅
├── models/        # SQLAlchemy models - KEEP AS IS ✅
├── plugins/       # Advanced module plugins - KEEP AS IS ✅
├── services/      # 🎯 TARGET FOR MODULAR REFACTORING
│   ├── providers/ # NEW - AI Provider implementations
│   │   ├── base/          # Shared provider functionality
│   │   │   ├── http_client.py      # HTTP client abstraction
│   │   │   ├── request_builder.py  # Request formatting utilities
│   │   │   └── response_parser.py  # Response parsing utilities
│   │   ├── ollama/        # Ollama-specific implementation
│   │   │   ├── client.py           # Ollama HTTP client (~150 lines)
│   │   │   ├── models.py           # Ollama-specific models
│   │   │   └── streaming.py        # Ollama streaming handler
│   │   ├── openai/        # OpenAI-specific implementation
│   │   │   ├── client.py           # OpenAI HTTP client (~150 lines)
│   │   │   ├── models.py           # OpenAI-specific models
│   │   │   └── streaming.py        # OpenAI streaming handler
│   │   └── factory.py     # Provider factory (refactored from ai_providers.py)
│   ├── session/   # NEW - Session management domain
│   │   ├── manager.py              # Core session lifecycle (from chat_session_manager.py)
│   │   ├── cancellation.py         # Cancellation logic extraction
│   │   └── tracking.py             # Session state tracking
│   ├── modules/   # NEW - Module resolution system
│   │   ├── resolver.py             # Main resolver (simplified from staged_module_resolver.py)
│   │   ├── template_parser.py      # Template parsing logic
│   │   ├── execution/      # Module execution engines
│   │   │   ├── simple_executor.py  # Simple text module execution
│   │   │   ├── script_executor.py  # Advanced Python script execution
│   │   │   └── ai_executor.py      # AI-powered module execution
│   │   └── stages/         # Stage implementations (extracted from base)
│   │       ├── stage1.py           # Template preparation stage
│   │       ├── stage2.py           # Pre-response AI stage
│   │       ├── stage4.py           # Post-response processing stage
│   │       └── stage5.py           # Post-response AI stage
│   ├── streaming.py       # Stream utilities (from streaming_accumulator.py)
│   ├── exceptions.py      # KEEP AS IS ✅
│   ├── system_prompt_debug.py # KEEP AS IS ✅ (until we optimize)
│   └── system_prompt_state.py # KEEP AS IS ✅
├── utils/         # EXPAND - Cross-cutting utilities
│   ├── validation.py           # Input validation helpers
│   ├── error_handling.py       # Centralized error handling
│   └── async_helpers.py        # Async/await utilities
└── main.py        # FastAPI app entry point - KEEP AS IS ✅
```

## 📊 **File Migration Mapping**

### **KEEP AS IS (No Changes):**
- `app/api/*` - All FastAPI endpoints ✅
- `app/core/*` - Script engine, config, analysis ✅  
- `app/database/*` - Database connections, migrations ✅
- `app/models/*` - SQLAlchemy models ✅
- `app/plugins/*` - Advanced module plugins ✅
- `app/services/exceptions.py` - Shared exceptions ✅
- `app/services/system_prompt_debug.py` - Debug utilities ✅
- `app/services/system_prompt_state.py` - State management ✅
- `app/main.py` - FastAPI app entry point ✅

### **REFACTOR/SPLIT:**

#### **Provider Files → `services/providers/`**
- `ollama_service_base.py` (430 lines) → Split into:
  - `providers/ollama/client.py` (~150 lines)
  - `providers/ollama/models.py` (~100 lines) 
  - `providers/ollama/streaming.py` (~100 lines)
  - `providers/base/http_client.py` (~80 lines shared)

- `openai_service_base.py` (573 lines) → Split into:
  - `providers/openai/client.py` (~200 lines)
  - `providers/openai/models.py` (~150 lines)
  - `providers/openai/streaming.py` (~150 lines)
  - `providers/base/request_builder.py` (~70 lines shared)

- `ollama_service.py` + `openai_service.py` → Merge into unified clients
- `ai_providers.py` → `providers/factory.py` (simplified)

#### **Session Files → `services/session/`**
- `chat_session_manager.py` (310 lines) → Split into:
  - `session/manager.py` (~200 lines)
  - `session/cancellation.py` (~70 lines)
  - `session/tracking.py` (~40 lines)

#### **Module Resolution → `services/modules/`**
- `staged_module_resolver_base.py` (1,073 lines) → Split into:
  - `modules/resolver.py` (~300 lines - main orchestration)
  - `modules/template_parser.py` (~150 lines)
  - `modules/stages/stage1.py` (~150 lines)
  - `modules/stages/stage2.py` (~150 lines)
  - `modules/stages/stage4.py` (~150 lines)
  - `modules/stages/stage5.py` (~150 lines)
  - `modules/execution/simple_executor.py` (~50 lines)
  - `modules/execution/script_executor.py` (~100 lines)
  - `modules/execution/ai_executor.py` (~100 lines)

- `staged_module_resolver.py` (640 lines) → Integrate into unified modules structure

#### **Utilities → `services/` & `utils/`**
- `streaming_accumulator.py` → `services/streaming.py` (refactored)
- NEW `utils/validation.py` - Extract validation logic
- NEW `utils/error_handling.py` - Centralize error handling
- NEW `utils/async_helpers.py` - Async utilities
├── providers/              # AI Provider implementations
│   ├── base/              # Shared provider functionality
│   │   ├── http_client.py      # HTTP client abstraction
│   │   ├── request_builder.py  # Request formatting utilities
│   │   ├── response_parser.py  # Response parsing utilities
│   │   └── streaming_handler.py # Base streaming implementation
│   ├── ollama/            # Ollama-specific implementation
│   │   ├── client.py           # Ollama HTTP client (~150 lines)
│   │   ├── models.py           # Ollama-specific request/response models
│   │   ├── streaming.py        # Ollama streaming handler
│   │   └── session_handler.py  # Ollama session management
│   ├── openai/            # OpenAI-specific implementation
│   │   ├── client.py           # OpenAI HTTP client (~150 lines)
│   │   ├── models.py           # OpenAI-specific models
│   │   ├── streaming.py        # OpenAI streaming handler
│   │   └── session_handler.py  # OpenAI session management
│   └── factory.py         # Simplified provider factory
├── session/               # Session management domain
│   ├── manager.py              # Core session lifecycle management
│   ├── cancellation.py         # Cancellation logic & token handling
│   ├── tracking.py             # Session state tracking
│   └── models.py               # Session-related models
├── modules/               # Module resolution system
│   ├── resolver/          # Core resolution orchestration
│   │   ├── template_parser.py  # Template parsing logic
│   │   ├── stage_coordinator.py # Stage orchestration
│   │   └── context_builder.py  # Execution context creation
│   ├── execution/         # Module execution engines
│   │   ├── simple_executor.py  # Simple text module execution
│   │   ├── script_executor.py  # Advanced Python script execution
│   │   └── ai_executor.py      # AI-powered module execution
│   ├── stages/            # Individual stage implementations
│   │   ├── stage1.py           # Template preparation stage
│   │   ├── stage2.py           # Pre-response AI stage
│   │   ├── stage4.py           # Post-response processing stage
│   │   └── stage5.py           # Post-response AI stage
│   └── models.py               # Module resolution models
├── utils/                 # Cross-cutting utilities
│   ├── streaming.py            # Stream conversion utilities
│   ├── validation.py           # Input validation helpers
│   ├── error_handling.py       # Centralized error handling
│   └── async_helpers.py        # Async/await utilities
└── legacy/                # Temporary migration folder
    └── (old files during migration)
```

## 📋 **Migration Strategy**

### **Phase 1: Foundation & Base Abstractions** 🏗️
**Status:** Not Started  
**Estimated Effort:** 2-3 hours

**Tasks:**
- [ ] Create `services/providers/base/` shared functionality
- [ ] Extract common HTTP client logic into base classes
- [ ] Create `services/utils/` for cross-cutting concerns
- [ ] Set up base streaming handlers
- [ ] Create shared request/response utilities

**Files to Create:**
- `services/providers/base/http_client.py` - Shared HTTP client abstraction
- `services/providers/base/request_builder.py` - Request formatting utilities
- `services/providers/base/response_parser.py` - Response parsing utilities
- `services/providers/base/streaming_handler.py` - Base streaming implementation
- `services/utils/validation.py` - Input validation helpers
- `services/utils/error_handling.py` - Centralized error handling
- `services/utils/async_helpers.py` - Async/await utilities

### **Phase 2: Provider Modularization** 🔌
**Status:** Not Started  
**Estimated Effort:** 3-4 hours

**Tasks:**
- [ ] Create `services/providers/ollama/` directory structure
- [ ] Create `services/providers/openai/` directory structure  
- [ ] Split `ollama_service_base.py` (430 lines) into focused modules
- [ ] Split `openai_service_base.py` (573 lines) into focused modules
- [ ] Merge enhanced service logic into unified implementations
- [ ] Eliminate base/enhanced inheritance duplication
- [ ] Update imports across codebase

**Files to Split:**
- `ollama_service_base.py` → `providers/ollama/client.py`, `models.py`, `streaming.py`
- `openai_service_base.py` → `providers/openai/client.py`, `models.py`, `streaming.py`
- Merge: `ollama_service.py` + base → unified `providers/ollama/client.py`
- Merge: `openai_service.py` + base → unified `providers/openai/client.py`
- Update: `ai_providers.py` → `providers/factory.py` (refactored)

### **Phase 3: Module Resolution Breakdown** 📦
**Status:** Not Started  
**Estimated Effort:** 4-5 hours

**Tasks:**
- [ ] Create `services/modules/` directory structure
- [ ] Split `staged_module_resolver_base.py` (1,073 lines) into focused components
- [ ] Extract template parsing logic into dedicated module
- [ ] Separate execution engines by stage and type
- [ ] Create individual stage implementations
- [ ] Merge enhanced resolver logic into unified implementation
- [ ] Eliminate base/enhanced inheritance pattern

**Files to Split:**
- `staged_module_resolver_base.py` → Multiple focused modules:
  - `modules/resolver.py` (~300 lines - main orchestration)
  - `modules/template_parser.py` (~150 lines)
  - `modules/stages/stage1.py` (~150 lines)
  - `modules/stages/stage2.py` (~150 lines) 
  - `modules/stages/stage4.py` (~150 lines)
  - `modules/stages/stage5.py` (~150 lines)
  - `modules/execution/simple_executor.py` (~50 lines)
  - `modules/execution/script_executor.py` (~100 lines)
  - `modules/execution/ai_executor.py` (~100 lines)
- Merge: `staged_module_resolver.py` + base → unified `modules/resolver.py`

### **Phase 4: Session Management Consolidation** 🔄
**Status:** Not Started  
**Estimated Effort:** 2-3 hours

**Tasks:**
- [ ] Create `services/session/` directory structure
- [ ] Split `chat_session_manager.py` (310 lines) into focused components
- [ ] Extract cancellation logic into dedicated module
- [ ] Refactor `streaming_accumulator.py` into utilities
- [ ] Consolidate session-related functionality
- [ ] Update session integration across providers

**Files to Refactor:**
- Split: `chat_session_manager.py` → Multiple focused modules:
  - `session/manager.py` (~200 lines - core session lifecycle)
  - `session/cancellation.py` (~70 lines - cancellation token logic)
  - `session/tracking.py` (~40 lines - session state tracking)
- Move: `streaming_accumulator.py` → `utils/streaming.py` (refactored)
- Update: Provider integrations to use modular session components

### **Phase 5: Legacy Cleanup & Testing** 🧹
**Status:** Not Started  
**Estimated Effort:** 2-3 hours

**Tasks:**
- [ ] Remove inheritance-based duplication patterns
- [ ] Delete old monolithic service files
- [ ] Update all imports across entire codebase
- [ ] Run comprehensive test suite (627+ tests)
- [ ] Fix any broken tests due to refactoring
- [ ] Update documentation and examples

**Files to Remove:**
- `ollama_service_base.py` (430 lines) - merged into modular structure
- `openai_service_base.py` (573 lines) - merged into modular structure  
- `staged_module_resolver_base.py` (1,073 lines) - merged into modular structure
- `ollama_service.py` (331 lines) - merged into unified implementation
- `openai_service.py` (333 lines) - merged into unified implementation
- `staged_module_resolver.py` (640 lines) - merged into unified implementation

**Import Updates Required:**
- Update all API endpoints that import from old service files
- Update provider factory references
- Update test imports to use new modular structure
- Verify no broken references remain across codebase

## 🎯 **Key Design Principles**

### **1. Single Responsibility Principle**
Each file should have one clear, well-defined purpose
- `providers/ollama/client.py` - Only Ollama HTTP communication
- `session/cancellation.py` - Only cancellation token logic
- `modules/stages/stage1.py` - Only Stage 1 execution

### **2. Dependency Inversion**
Depend on abstractions, not concretions
- Use protocols in `core/protocols/` for interfaces
- Implementations depend on protocols, not other implementations
- Easy to mock and test

### **3. Composition over Inheritance**
Avoid complex inheritance hierarchies
- Use composition to combine functionality
- Inject dependencies rather than inheriting behavior
- Cleaner and more flexible than base/enhanced pattern

### **4. Domain-Driven Organization**
Group by business domain, not technical patterns
- `providers/` - Everything about AI providers
- `session/` - Everything about session management  
- `modules/` - Everything about module resolution

## 📈 **Expected Benefits**

### **Maintainability**
- **Smaller files** - Easy to understand and modify
- **Clear separation** - Know exactly where to find/change code
- **Focused responsibility** - Each component has one job

### **Testability** 
- **Isolated components** - Test each piece independently
- **Mockable interfaces** - Use protocols for clean mocking
- **Reduced complexity** - Smaller units are easier to test

### **Extensibility**
- **Plugin architecture** - Easy to add new providers
- **Modular stages** - Easy to modify resolution pipeline  
- **Clean interfaces** - Well-defined extension points

### **Performance**
- **Selective imports** - Only load what you need
- **Cleaner memory** - No large monolithic objects
- **Better caching** - More granular caching opportunities

## 🚨 **Migration Risks & Mitigation**

### **Breaking Changes**
- **Risk:** Imports will change across codebase
- **Mitigation:** Maintain backwards-compatible imports during migration
- **Strategy:** Use `__init__.py` files to provide old import paths

### **Complexity During Migration**
- **Risk:** Temporary increased complexity while both systems exist
- **Mitigation:** Migrate one domain at a time, keep working system
- **Strategy:** Use `legacy/` folder to temporarily hold old files

### **Integration Issues**
- **Risk:** New modular components may not integrate properly
- **Mitigation:** Comprehensive integration testing at each phase
- **Strategy:** Keep comprehensive test suite running throughout

## 📝 **Session Notes**

### **2025-01-09 - Initial Planning**
- Analyzed current service file sizes and complexity  
- Identified inheritance-based duplication as major issue (base + enhanced patterns)
- User corrected initial approach: respect existing backend structure
- Designed incremental refactoring plan focused on services/ directory only
- Created 5-phase migration strategy with realistic file mappings
- Completed comprehensive analysis: 6 monolithic files totaling 3,247 lines
- **Status:** Planning phase complete, ready for implementation

### **Key Architecture Decisions**
- **Preserve existing structure**: Keep app/api/, app/core/, app/database/, app/models/, app/plugins/ unchanged
- **Focus on services/ only**: Incremental modularization within services directory
- **Eliminate inheritance duplication**: Replace base/enhanced pattern with composition
- **Domain-driven organization**: Group by business domain (providers/, session/, modules/)
- **Piece-by-piece transition**: 5 phases to maintain working system throughout migration

### **Next Session Goals**
1. Begin Phase 1: Foundation & Base Abstractions
2. Create services/providers/base/ shared functionality
3. Set up services/utils/ cross-cutting utilities  
4. Extract common HTTP client and streaming logic
5. Prepare foundation for Phase 2 provider modularization

---

**Last Updated:** 2025-01-09  
**Status:** Planning Complete, Ready for Implementation  
**Next Phase:** Phase 1 - Foundation & Protocols