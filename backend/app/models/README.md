# Models Layer

The Models layer defines SQLAlchemy ORM models for all database tables. These models provide the data structures and relationships that form Project 2501's persistence layer.

## 📁 Files Overview

### [base.py](base.py)
**Base model class for all database models**

Provides common functionality for all models:
- Automatic `created_at` and `updated_at` timestamps
- Declarative base for SQLAlchemy ORM
- Common utility methods

```python
class Base:
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

---

### [persona.py](persona.py)
**AI persona configuration model**

Stores persona configurations including system prompt templates, mode, and settings.

**Fields:**
- `id` (UUID): Primary key
- `name` (VARCHAR 255): Persona name
- `description` (TEXT): Optional description
- `template` (TEXT): System prompt template with module placeholders
- `mode` (VARCHAR 20): "reactive" or "autonomous"
- `loop_frequency` (VARCHAR 10): For autonomous mode (e.g., "5.0" seconds)
- `first_message` (TEXT): Optional first message to user
- `image_path` (VARCHAR 500): Path to persona avatar
- `extra_data` (JSONB): Additional metadata
- `is_active` (BOOLEAN): Active status

**Relationships:**
- `conversations`: One-to-many relationship with Conversation

**Methods:**
```python
persona = Persona(name="Assistant", template="You are @greeting_module")
persona.conversations  # Access related conversations
```

---

### [module.py](module.py)
**Cognitive system module model**

Stores both simple (static text) and advanced (Python script) modules for dynamic system prompts.

**Enums:**
```python
class ModuleType(str, enum.Enum):
    SIMPLE = "simple"        # Static text content
    ADVANCED = "advanced"    # Python script execution

class ExecutionContext(str, enum.Enum):
    IMMEDIATE = "IMMEDIATE"          # Stage 1-2: During template resolution
    POST_RESPONSE = "POST_RESPONSE"  # Stage 4-5: After AI response
    ON_DEMAND = "ON_DEMAND"          # Only when explicitly triggered
```

**Fields:**
- `id` (UUID): Primary key
- `name` (VARCHAR 255): Module name
- `description` (TEXT): Optional description
- `content` (TEXT): Static content for simple modules
- `type` (ModuleType): SIMPLE or ADVANCED
- `trigger_pattern` (VARCHAR 500): Regex/keyword for activation
- `script` (TEXT): Python script for advanced modules
- `execution_context` (ExecutionContext): IMMEDIATE, POST_RESPONSE, or ON_DEMAND
- `requires_ai_inference` (BOOLEAN): Auto-detected via script analysis
- `script_analysis_metadata` (JSONB): Analysis results from script_analyzer
- `is_active` (BOOLEAN): Active status

**Methods:**
```python
# Script analysis
module.analyze_script()  # Returns analysis dict, updates requires_ai_inference
module.refresh_ai_analysis(db_session)  # Re-analyze and persist

# Context checking
module.is_immediate_context  # Property: True if IMMEDIATE
module.is_post_response_context  # Property: True if POST_RESPONSE
module.is_on_demand_context  # Property: True if ON_DEMAND

# Stage execution
module.execution_stage_priority  # Integer: 1, 2, 4, 5, or 999
module.get_stage_name()  # Human-readable stage description

# Class methods
Module.get_modules_for_stage(db, stage_number, persona_id)
```

**Stage Priority Logic:**
- **IMMEDIATE + Non-AI**: Stage 1 (priority 1)
- **IMMEDIATE + AI**: Stage 2 (priority 2)
- **POST_RESPONSE + Non-AI**: Stage 4 (priority 4)
- **POST_RESPONSE + AI**: Stage 5 (priority 5)
- **ON_DEMAND**: Priority 999 (manual trigger only)

---

### [conversation.py](conversation.py)
**Conversation and message models**

Stores chat conversations and their associated messages.

#### **Conversation Model**

**Fields:**
- `id` (UUID): Primary key
- `title` (VARCHAR 255): Conversation title
- `persona_id` (UUID FK): Associated persona
- `provider_type` (VARCHAR 50): "ollama", "openai", etc.
- `provider_config` (JSONB): Snapshot of provider configuration
- `created_at`, `updated_at`: Timestamps

**Relationships:**
- `messages`: One-to-many with Message (cascade delete)
- `persona`: Many-to-one with Persona

```python
conversation = Conversation(title="Chat 1", persona_id=persona.id)
conversation.messages  # Access all messages
conversation.persona   # Access persona
```

#### **Message Model**

**Enum:**
```python
class MessageRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
```

**Fields:**
- `id` (UUID): Primary key
- `conversation_id` (UUID FK): Parent conversation (cascade delete)
- `role` (MessageRole): USER, ASSISTANT, or SYSTEM
- `content` (TEXT): Message text
- `thinking` (TEXT): Optional AI reasoning content
- `extra_data` (JSONB): Additional metadata
- `input_tokens` (INTEGER): Token count for input
- `output_tokens` (INTEGER): Token count for output
- `created_at`, `updated_at`: Timestamps

**Relationships:**
- `conversation`: Many-to-one with Conversation

```python
message = Message(
    conversation_id=conv.id,
    role=MessageRole.USER,
    content="Hello!",
    thinking="User is greeting"
)
```

---

### [conversation_state.py](conversation_state.py)
**Module execution state storage**

Stores output variables from POST_RESPONSE modules for use in subsequent conversations.

**Enum:**
```python
class ExecutionStage(str, enum.Enum):
    STAGE4 = "stage4"  # POST_RESPONSE Non-AI
    STAGE5 = "stage5"  # POST_RESPONSE AI
```

**Fields:**
- `id` (UUID): Primary key
- `conversation_id` (UUID): Conversation identifier
- `module_id` (UUID FK): Module that produced this state
- `execution_stage` (VARCHAR 20): "stage4" or "stage5"
- `variables` (JSONB): Output variables from script
- `execution_metadata` (JSONB): Success, timing, errors, etc.
- `executed_at` (DATETIME): Execution timestamp

**Constraints:**
- Unique constraint on (conversation_id, module_id, execution_stage)
- Check constraint: execution_stage IN ('stage4', 'stage5')

**Relationships:**
- `module`: Many-to-one with Module (cascade delete)

**Class Methods:**
```python
# Query methods
ConversationState.get_for_conversation(db, conversation_id)
ConversationState.get_latest_for_module(db, conversation_id, module_id)

# Storage method
ConversationState.store_execution_result(
    db, conversation_id, module_id, execution_stage,
    variables={'greeting': 'Hello!'},
    execution_metadata={'success': True, 'execution_time': 0.5}
)

# Instance methods
state.to_dict()  # Convert to dictionary for API
```

**Usage in Staged Execution:**
1. Stage 4/5 modules execute after AI response
2. Output variables stored in ConversationState
3. Next conversation's Stage 1 retrieves previous state
4. Variables available for template substitution

---

### [conversation_memory.py](conversation_memory.py)
**Long-term conversation memory storage**

Stores AI-compressed summaries of conversation segments from fixed buffer window (messages 25-35).

**Fields:**
- `id` (UUID): Primary key
- `conversation_id` (UUID): Conversation identifier
- `memory_sequence` (INTEGER): Sequential numbering (1, 2, 3...)
- `compressed_content` (TEXT): AI-generated memory summary
- `original_message_range` (VARCHAR 20): "25-35"
- `message_count_at_compression` (INTEGER): Total messages when compressed
- `first_message_id` (VARCHAR 100): ID of first message in range
- `created_at` (DATETIME): Creation timestamp

**Constraints:**
- Unique constraint on (conversation_id, memory_sequence)

**Class Methods:**
```python
# Query methods
ConversationMemory.get_for_conversation(db, conversation_id)
ConversationMemory.get_recent_memories(db, conversation_id, limit=10)
ConversationMemory.get_next_sequence_number(db, conversation_id)

# Storage methods
ConversationMemory.store_memory(
    db, conversation_id, compressed_content,
    message_range="25-35", message_count=35,
    first_message_id=msg_id
)

# Cleanup
ConversationMemory.clear_all_memories(db, conversation_id)
```

**Memory Compression Flow:**
1. Conversation reaches 35+ messages
2. Messages 25-35 extracted as buffer window
3. AI compresses segment into summary
4. Summary stored with sequence number
5. Buffer advances with each compression

---

## 🏗️ Model Relationships

### Entity Relationship Diagram
```
Persona (1) ──────────────────< (N) Conversation
                                       │
                                       │ (1)
                                       │
                                       ├───────< (N) Message
                                       │
                                       └───────< (N) ConversationMemory

Module (1) ───────────< (N) ConversationState
```

### Cascade Behavior
- **Persona → Conversation**: CASCADE DELETE (delete conversations when persona deleted)
- **Conversation → Message**: CASCADE DELETE (delete messages when conversation deleted)
- **Module → ConversationState**: CASCADE DELETE (delete state when module deleted)
- **Conversation → ConversationMemory**: No FK (conversation_id stored for cleanup)

---

## 🔄 Lifecycle Patterns

### Persona Lifecycle
```python
# Create
persona = Persona(name="Assistant", template="Hello @greeting")
db.add(persona)
db.commit()

# Read
persona = db.query(Persona).filter(Persona.id == persona_id).first()

# Update
persona.template = "Updated @greeting"
db.commit()

# Delete (cascades to conversations)
db.delete(persona)
db.commit()
```

### Module Lifecycle with Analysis
```python
# Create advanced module
module = Module(
    name="TimeModule",
    type=ModuleType.ADVANCED,
    execution_context=ExecutionContext.IMMEDIATE,
    script="ctx.set_variable('time', ctx.get_current_time())"
)

# Automatic analysis on save
module.analyze_script()  # Sets requires_ai_inference automatically

db.add(module)
db.commit()

# Later: re-analyze after script changes
module.script = "ctx.generate('Say hello')"
module.refresh_ai_analysis(db)  # Updates requires_ai_inference to True
db.commit()
```

### Conversation + Messages Pattern
```python
# Create conversation
conv = Conversation(title="Chat 1", persona_id=persona.id)
db.add(conv)
db.commit()

# Add messages
user_msg = Message(conversation_id=conv.id, role=MessageRole.USER, content="Hi")
db.add(user_msg)

assistant_msg = Message(
    conversation_id=conv.id,
    role=MessageRole.ASSISTANT,
    content="Hello!",
    thinking="User greeting detected"
)
db.add(assistant_msg)
db.commit()

# Query messages
messages = db.query(Message).filter(
    Message.conversation_id == conv.id
).order_by(Message.created_at).all()
```

### ConversationState Pattern
```python
# Store module execution result
ConversationState.store_execution_result(
    db,
    conversation_id=conv_id,
    module_id=module_id,
    execution_stage="stage4",
    variables={'count': 5, 'status': 'ready'},
    execution_metadata={'success': True, 'duration_ms': 150}
)

# Retrieve in next conversation
previous_state = ConversationState.get_latest_for_module(
    db, conv_id, module_id
)
if previous_state:
    variables = previous_state.variables  # {'count': 5, 'status': 'ready'}
```

---

## 🔍 Query Patterns

### Active Personas
```python
personas = db.query(Persona).filter(
    Persona.is_active == True
).order_by(Persona.created_at.desc()).all()
```

### Modules by Stage
```python
stage2_modules = db.query(Module).filter(
    Module.is_active == True,
    Module.execution_context == ExecutionContext.IMMEDIATE,
    Module.requires_ai_inference == True
).all()
```

### Recent Messages
```python
recent_messages = db.query(Message).filter(
    Message.conversation_id == conv_id
).order_by(Message.created_at.desc()).limit(20).all()
```

### Conversation State History
```python
states = ConversationState.get_for_conversation(db, conv_id).all()
```

---

## 🧪 Testing Patterns

### Model Creation
```python
def test_persona_creation(db_session):
    persona = Persona(name="Test", template="Test @module")
    db_session.add(persona)
    db_session.commit()

    assert persona.id is not None
    assert persona.created_at is not None
```

### Relationship Testing
```python
def test_conversation_messages(db_session):
    persona = Persona(name="Test", template="Test")
    db_session.add(persona)

    conv = Conversation(title="Test Chat", persona_id=persona.id)
    db_session.add(conv)

    msg = Message(conversation_id=conv.id, role=MessageRole.USER, content="Hi")
    db_session.add(msg)
    db_session.commit()

    assert len(conv.messages) == 1
    assert conv.messages[0].content == "Hi"
```

### Cascade Deletion
```python
def test_conversation_cascade_delete(db_session):
    conv = Conversation(title="Test")
    db_session.add(conv)

    msg = Message(conversation_id=conv.id, role=MessageRole.USER, content="Test")
    db_session.add(msg)
    db_session.commit()

    db_session.delete(conv)
    db_session.commit()

    # Message should be deleted too
    assert db_session.query(Message).filter(Message.id == msg.id).first() is None
```

---

## 📊 Performance Considerations

### Indexing
- All UUID primary keys indexed automatically
- Foreign keys indexed for join performance
- `created_at` indexed for time-based queries
- `is_active` + `execution_context` for module queries

### Query Optimization
```python
# Use joinedload for known relationships
from sqlalchemy.orm import joinedload

conv = db.query(Conversation).options(
    joinedload(Conversation.messages),
    joinedload(Conversation.persona)
).filter(Conversation.id == conv_id).first()

# Avoid N+1 queries
conversations = db.query(Conversation).options(
    joinedload(Conversation.messages)
).all()
```

### Bulk Operations
```python
# Bulk insert
messages = [Message(conversation_id=conv_id, role=MessageRole.USER, content=f"Msg {i}")
            for i in range(100)]
db.bulk_save_objects(messages)
db.commit()

# Bulk update
db.query(Module).filter(Module.type == ModuleType.SIMPLE).update({
    "execution_context": ExecutionContext.IMMEDIATE
})
db.commit()
```

---

## 📝 Notes

- All models use UUID primary keys for security and distributed systems
- Timestamps automatically managed by Base class
- JSONB columns for flexible metadata storage
- Enum types ensure data integrity
- Cascade deletes configured for proper cleanup
- Script analysis runs automatically on module create/update
- ConversationState provides stateful module execution
- ConversationMemory enables long-term context retention
