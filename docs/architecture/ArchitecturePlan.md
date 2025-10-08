# Project 2501 - Cognitive Systems Framework
*"Building dynamic cognitive architectures through scriptable modules"*

---

## 🎯 Project Vision

**Project 2501** is a model-agnostic platform where users can design, share, and evolve sophisticated AI personas through an intuitive web interface, powered by a modular Python backend.
The platform is a cognitive systems framework that reimagines how we interact with AI by solving some common limitations of static system prompts and context rot.

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
- **Debug System**: AI provider request/response inspector for system prompt state analysis
- **Settings Storage**: Frontend localStorage (no backend duplication)

**Backend Layer (FastAPI 0.104.1)**
- **Framework**: FastAPI with SQLAlchemy 2.0.23 ORM
- **Core Engine**: 5-Stage Staged Execution Pipeline (see below)
- **AI Providers**: Ollama + OpenAI compatible API with streaming support
- **Script Sandbox**: RestrictedPython 7.0 with extendable plugin functions
- **API Endpoints**: Complete REST API with streaming chat support

**Database Layer (PostgreSQL + pgvector)**
- **Models**: Persona, Module, Conversation, Message, ConversationState
- **Primary Keys**: UUID-based for all entities
- **State Persistence**: ConversationState table for POST_RESPONSE module results
- **Cascade Deletion**: Proper cleanup on conversation/message deletion

### 🚀 5-Stage Staged Execution Pipeline

**Stage 1: Template Preparation**
- Simple modules (static text)
- IMMEDIATE Non-AI modules  
- Previous POST_RESPONSE results retrieval
- Module: `StagedModuleResolver._execute_stage1()`

**Stage 2: Pre-Response AI Processing**
- IMMEDIATE AI-powered modules
- Uses `ctx.reflect()` or `ctx.generate()` for AI introspection
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
- Uses `ctx.reflect()` or `ctx.generate()` for AI introspection
- Results stored for next conversation's Stage 1

### 🧩 Advanced Module System

**Simple Modules:**
- Static text content with `@module_name` references
- Recursive module resolution supported

**Advanced Modules:**
- Python scripts with RestrictedPython 7.0 sandbox
- built-in plugin functions
- Variable outputs using `${variable}` syntax
- Execution contexts: IMMEDIATE, POST_RESPONSE, ON_DEMAND
  - **IMMEDIATE**: Execute in Stage 1 (non-AI) or Stage 2 (AI-powered)
  - **POST_RESPONSE**: Execute in Stage 4 (non-AI) or Stage 5 (AI-powered) 
  - **ON_DEMAND**: Execute only when explicitly triggered
- Trigger pattern support (regex/keyword matching)
- Automatic AI inference detection and stage assignment

**Plugin Functions: ✅ 15+ Implemented**
- **Time Functions**: `ctx.get_current_time()`, `ctx.get_relative_time()`, business hours
- **Conversation Functions**: `ctx.get_message_count()`, `ctx.get_recent_messages()`, history access
- **AI Reflection**: `ctx.reflect()` function for AI introspection with and `ctx.generate()` generation without full context.
- **Utilities**: String manipulation, data processing, custom logic
- **Auto-Discovery**: Decorator-based plugin registration system

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
- Unified interface for Ollama and OpenAI compatible APIs
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



### 🌟 Advanced Module Examples

**Example 1: AI Self-Assessment Module (POST_RESPONSE)**
```python
# Script: response_assessor (ExecutionContext: POST_RESPONSE, AI: Required)
last_response = ctx.get_recent_messages(1)
quality_rating = ctx.reflect(
    "Rate this response quality from 1-10 and suggest improvements, in less than 150 tokens. Be short and concise.", 
    last_response, 
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