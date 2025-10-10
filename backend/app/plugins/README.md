# Plugins Layer

The Plugins layer provides 15+ plugin functions that advanced modules can call via `ctx.<function_name>()`. These functions enable time/date operations, conversation data access, AI generation/reflection, and utility operations.

## 📁 Files Overview

### [time_plugins.py](time_plugins.py)
**Time and date functions**

Functions for working with timestamps, business hours, and date formatting.

**Functions:**
- `get_current_time(format="%Y-%m-%d %H:%M")` - Current time in format
- `get_relative_time(minutes_offset=0, format="%H:%M")` - Time +/- minutes
- `is_business_hours(start_hour=9, end_hour=17)` - Business hours check
- `get_day_of_week(full_name=True)` - Day name (Monday/Mon)
- `format_timestamp(timestamp, format)` - Unix timestamp → formatted string

**Usage:**
```python
# In advanced module script
current_time = ctx.get_current_time()  # "2025-10-08 14:30"
tomorrow_time = ctx.get_relative_time(1440)  # +24 hours
is_work_hours = ctx.is_business_hours()  # True/False
day = ctx.get_day_of_week()  # "Wednesday"
```

---

### [conversation_plugins.py](conversation_plugins.py)
**Conversation data access and memory functions**

Provides read access to conversation messages, persona info, and compressed memories.

#### **Message Functions**

**`get_message_count(conversation_id=None)`**
- Count total messages in conversation
- Uses current conversation if not specified
- Returns: Integer count

**`get_recent_messages(limit=5)`**
- Get recent messages formatted for AI context
- Returns formatted string: `[HH:MM] Role: Content`
- Chronological order (oldest to newest)

**`get_raw_recent_messages(limit=10)`**
- Get recent messages as raw dictionaries
- Returns list with id, role, content, thinking, tokens, etc.
- Useful for custom formatting

**`get_conversation_history(conversation_id, limit=50, offset=0)`**
- Get message history with pagination
- Chronological order
- Returns list of message dictionaries

**`get_buffer_messages(start_index=25, end_index=35)`**
- Get messages from memory buffer window
- Default: messages 25-35 (overlaps short-term memory)
- Used for memory compression

#### **Conversation Info Functions**

**`get_conversation_summary(conversation_id=None)`**
- Get conversation metadata
- Returns: {id, title, message_count, persona_name, provider, model, created_at, updated_at}

**`get_persona_info(persona_id=None)`**
- Get persona information as `DictObject`
- Supports both `persona.name` and `persona['name']` access
- Returns: {id, name, description, template, is_active, timestamps}

#### **Memory Functions**

**`should_compress_buffer(buffer_size=11, min_total_messages=None)`**
- Check if memory compression should occur
- Based on message count and compression history
- Returns: Boolean

**`should_compress_buffer_by_ids(buffer_message_ids)`**
- Check compression by message IDs (prevents duplicates)
- More accurate than count-based checking
- Returns: Boolean

**`store_memory(compressed_content, message_range="25-35", total_messages=None)`**
- Store AI-compressed memory in database
- Automatic sequence numbering
- Returns: {success, memory_id, memory_sequence, message_range}

**`get_recent_memories(limit=10)`**
- Get recent compressed memories
- Most recent first
- Returns: List of memory dictionaries

**`get_memory_status()`**
- Get comprehensive memory statistics
- Returns: {total_messages, total_memories, buffer_ready_for_compression, etc.}

**`clear_memories(conversation_id=None)`**
- Delete all memories for conversation
- Returns: {success, deleted_count}

**Usage:**
```python
# Message access
msg_count = ctx.get_message_count()
recent = ctx.get_recent_messages(5)  # Formatted string
raw_messages = ctx.get_raw_recent_messages(10)  # Raw data

# Persona info
persona = ctx.get_persona_info()
name = persona.name  # or persona['name']

# Memory compression
if ctx.should_compress_buffer():
    buffer = ctx.get_buffer_messages(25, 35)
    compressed = ctx.generate("Compress these messages", json.dumps(buffer))
    result = ctx.store_memory(compressed, "25-35", 45)

# Memory retrieval
memories = ctx.get_recent_memories(10)
status = ctx.get_memory_status()
```

---

### [ai_plugins.py](ai_plugins.py)
**AI generation and reflection functions**

Enables advanced modules to make AI calls using current session provider/model.

#### **`generate(*args, **kwargs)`**
AI generation with flexible signatures and automatic provider integration.

**Signatures:**
```python
# Use current session provider/model
ctx.generate('Instructions')
ctx.generate('Instructions', 'input_text')

# Use specific provider/model
ctx.generate('ollama', 'llama3.2:3b', 'Instructions')
ctx.generate('openai', 'gpt-4', 'Instructions', 'input_text')

# With custom parameters
ctx.generate('Instructions', temperature=0.8, max_tokens=500)
```

**Features:**
- Auto-uses current chat session provider/model if not specified
- State-aware system prompt integration
- Cancellation support via StreamingAccumulator
- Streaming mode for responsiveness
- Flexible parameter overrides (temperature, max_tokens, etc.)

**Examples:**
```python
# Simple generation
summary = ctx.generate("Summarize the key points")

# With input text
analysis = ctx.generate("Analyze this text", long_document)

# Specific provider/model
quick = ctx.generate("ollama", "llama3.2:3b", "Quick response")

# Custom parameters
creative = ctx.generate("Write a story", temperature=0.9, max_tokens=800)
```

#### **`reflect(instructions, **kwargs)`**
Self-reflective AI processing using current system prompt.

**Features:**
- Uses fully resolved system prompt from current execution stage
- Comprehensive safety mechanisms:
  - Maximum reflection depth: 3 levels
  - Direct module recursion prevention
  - Execution context restrictions (no nested IMMEDIATE)
  - Audit trail for debugging
- Cancellation support
- Moderate default temperature (0.3) for balanced reflection

**Examples:**
```python
# Self-assessment
quality = ctx.reflect("Rate my last response quality 1-10 and suggest improvements")

# Adaptive behavior
tone = ctx.reflect("What communication style would work best for this user?")

# Creative reflection
idea = ctx.reflect("Generate a creative solution", temperature=0.8, max_tokens=300)
```

**Safety Checks:**
1. Verify script context available
2. Validate instructions non-empty
3. Check `can_reflect()` safety method
4. Enter/exit reflection tracking
5. Audit trail logging

**Internal Implementation:**
- `_sync_ollama_call()`: Direct HTTP call to Ollama
- `_sync_openai_call()`: Direct HTTP call to OpenAI
- `_run_cancellable_ai_call()`: Streaming with cancellation
- `_get_state_aware_system_prompt()`: Get current stage system prompt

---

### [core_plugins.py](core_plugins.py)
**Core utility functions**

Basic utility functions for JSON, strings, and data manipulation.

**Functions:**
- `to_json(data, indent=None)` - Convert to JSON string
- `from_json(json_str)` - Parse JSON string
- `join_strings(strings, separator=", ")` - Join list of strings
- `split_string(text, separator=None, max_splits=-1)` - Split string
- `count_words(text)` - Count words in text

**Usage:**
```python
# JSON operations
json_str = ctx.to_json({"key": "value"}, indent=2)
data = ctx.from_json(json_str)

# String operations
combined = ctx.join_strings(["a", "b", "c"], " | ")  # "a | b | c"
parts = ctx.split_string("a,b,c", ",")  # ["a", "b", "c"]
word_count = ctx.count_words("hello world")  # 2
```

---

### [__init__.py](__init__.py)
**Plugin package initialization**

Auto-imports all plugin modules to trigger `@plugin_registry.register()` decorators.

---

## 🔌 Plugin System Architecture

### Registration Flow
```
1. App startup
2. ScriptContext.__init__() calls plugin_registry.load_all_plugins()
3. Registry walks app/plugins/ package
4. Imports all *_plugins.py modules
5. @register decorators execute, adding functions to registry
6. ScriptContext.__getattr__() provides ctx.function_name() access
7. Auto-injects db_session and _script_context parameters
```

### Function Access
```python
# In advanced module script
ctx.get_current_time()

# ScriptContext.__getattr__ intercepts
# Creates wrapper that injects db_session and _script_context
# Calls actual plugin function with injected params
```

### Parameter Injection
```python
@plugin_registry.register("get_message_count")
def get_message_count(conversation_id=None, db_session=None, _script_context=None):
    # db_session auto-injected from ScriptContext
    # _script_context auto-injected from ScriptContext
    # conversation_id from user or defaults to current conversation
```

---

## 📊 Plugin Categories

### Time/Date (5 functions)
- Current time, relative time, business hours
- Day of week, timestamp formatting

### Conversation Access (9 functions)
- Message counting and retrieval
- Conversation summaries and metadata
- Persona information access

### Memory Management (6 functions)
- Buffer compression checking
- Memory storage and retrieval
- Memory status and cleanup

### AI Operations (2 functions)
- `generate()`: Flexible AI generation
- `reflect()`: Self-reflective AI processing

### Utilities (5 functions)
- JSON conversion
- String operations
- Word counting

---

## 🔐 Security & Safety

### Plugin Execution Safety
- All plugins run in RestrictedPython sandbox
- Database access read-only (no write operations)
- Script context isolates conversation data
- No file system or network access (except AI calls)

### AI Function Safety
- Reflection depth limiting (max 3 levels)
- Circular module detection
- Context restrictions (IMMEDIATE can't nest)
- Audit trail for debugging
- Cancellation support

### Parameter Validation
- UUID format validation for conversation/persona IDs
- Empty/None checking for required parameters
- Type validation for user inputs
- Graceful error handling and logging

---

## 🧪 Testing Patterns

### Plugin Function Testing
```python
def test_plugin_function(db_session):
    from app.core.script_context import ScriptExecutionContext

    ctx = ScriptExecutionContext(
        conversation_id=conv_id,
        persona_id=persona_id,
        db_session=db_session
    )

    # Test function call
    result = ctx.get_message_count()
    assert isinstance(result, int)
```

### AI Function Testing
```python
def test_generate_function():
    # Mock script context with provider settings
    ctx = Mock()
    ctx.current_provider = "ollama"
    ctx.current_provider_settings = {"host": "...", "model": "..."}
    ctx.current_chat_controls = {"temperature": 0.7}

    # Test generation
    result = generate("Test prompt", _script_context=ctx)
    assert isinstance(result, str)
```

---

## 📝 Plugin Development Guidelines

### Creating New Plugins

**1. Create Plugin File**
```python
# backend/app/plugins/my_plugins.py
from app.core.script_plugins import plugin_registry

@plugin_registry.register("my_function")
def my_function(param1: str, db_session=None, _script_context=None) -> str:
    """
    Function description.

    Args:
        param1: User-provided parameter
        db_session: Database session (auto-injected)
        _script_context: Script context (auto-injected)

    Returns:
        Result string
    """
    # Implementation
    return result
```

**2. Auto-Loading**
Plugin automatically loaded on app startup via `plugin_registry.load_all_plugins()`.

**3. Usage in Scripts**
```python
# In advanced module script
result = ctx.my_function("test")
```

### Best Practices
- Clear, descriptive function names
- Comprehensive docstrings with examples
- Proper error handling and logging
- Type hints for parameters and returns
- Default values for optional parameters
- Graceful None/empty handling
- Return simple, JSON-serializable types

### Parameter Injection
- `db_session`: Auto-injected database session
- `_script_context`: Auto-injected ScriptExecutionContext
- Optional parameters: Use defaults like `conversation_id=None`

---

## 🔄 Plugin Lifecycle

### Initialization
1. App starts → FastAPI loads
2. First chat request → ScriptExecutionContext created
3. Context init → `plugin_registry.load_all_plugins()`
4. Registry scans `app/plugins/` package
5. Imports all `*_plugins.py` files
6. Decorator registration executes
7. Plugins available via `ctx.function_name()`

### Runtime Access
1. Script calls `ctx.function_name(param)`
2. ScriptContext.__getattr__ intercepts
3. Wrapper function created with auto-injection
4. db_session and _script_context injected
5. Plugin function executes
6. Result returned to script

### Cleanup
- No explicit cleanup needed
- Database sessions managed by FastAPI dependency injection
- Plugin registry persists for app lifetime

---

## 📊 Performance Considerations

### AI Functions
- Streaming mode enabled by default (cancellable)
- Cancellation support via StreamingAccumulator
- Session ID tracking for interrupt capability
- Default timeouts: 30 seconds

### Database Queries
- Efficient queries with proper indexing
- Pagination support for large result sets
- Limit defaults to prevent excessive data loading
- UUID validation before queries

### Memory Management
- Compressed memories stored separately from messages
- Buffer window design (messages 25-35) prevents unbounded growth
- Pagination for history retrieval
- Lazy loading of relationships

---

## 📝 Notes

- All plugins automatically registered on first use
- Functions accessible via `ctx.<function_name>()`
- Database session auto-injected from ScriptContext
- Conversation/persona IDs default to current context
- AI functions use current chat session provider/model
- Reflection safety prevents infinite loops
- Memory compression uses fixed buffer window (25-35)
- All functions return JSON-serializable types
