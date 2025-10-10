# Database Layer

The Database layer manages PostgreSQL connections, connection pooling, session management, and schema migrations. Provides the foundation for all data persistence in Project 2501.

## 📁 Files Overview

### [connection.py](connection.py)
**Database connection management and session handling**

Manages SQLAlchemy engine creation, connection pooling, and database session lifecycle.

**Key Classes:**

#### `DatabaseManager`
Singleton-style manager for database connections and operations.

**Initialization:**
```python
from app.database.connection import db_manager

# Auto-initializes on first use
session = db_manager.get_session()
```

**Configuration:**
- **Pool Size**: 10 connections
- **Max Overflow**: 20 additional connections
- **Pool Pre-Ping**: Validates connections before use
- **Pool Recycle**: Recycles connections every 5 minutes
- **Echo Mode**: SQL logging in debug mode

**Key Methods:**
```python
db_manager.initialize()                # Create engine and session factory
db_manager.get_session()               # Get new database session
db_manager.get_session_context()       # Async context manager
db_manager.test_connection()           # Health check
db_manager.close()                     # Cleanup resources
```

**Connection Health Check:**
```python
status = await db_manager.test_connection()
# Returns:
{
    "status": "success",
    "message": "Database connection successful",
    "database": "project2501",
    "version": "PostgreSQL 14.x",
    "host": "localhost",
    "port": 5432
}
```

**FastAPI Dependency:**
```python
from app.database.connection import get_db

@router.get("/endpoint")
def endpoint(db: Session = Depends(get_db)):
    # Use db session
    # Auto-closes after request
```

---

### [migrations/](migrations/)
**SQL migration scripts for schema evolution**

Chronological database migrations tracking schema changes over time.

#### Migration History

**001_add_thinking_and_persona_relationship.sql**
- Added `thinking` field to messages
- Added persona relationship to conversations

**002_fix_message_cascade_delete.sql**
- Fixed cascade deletion for messages when conversation deleted

**003_convert_messages_to_uuid.sql**
- Converted message IDs from integer to UUID
- Maintained referential integrity

**004_allow_empty_module_content.sql**
- Made module content nullable
- Support for script-only advanced modules

**005_add_cognitive_engine_constraints.sql**
- Added execution timing enum
- Added trigger pattern constraints
- Enhanced module validation

**006_staged_execution_redesign.sql** *(Major)*
- **Added `conversation_states` table** for module state storage
- **Replaced `execution_timing`** with `execution_context` enum (IMMEDIATE, POST_RESPONSE, ON_DEMAND)
- **Added `requires_ai_inference`** boolean field to modules
- **Added `stage_priority`** integer for execution ordering
- Enabled staged execution pipeline (5 stages)

**007_add_conversation_memory.sql**
- Added `conversation_memory` table for episodic memory
- Vector embeddings with pgvector extension
- Importance scoring and decay
- Memory type classification

**008_add_first_message_id.sql**
- Added `first_message_id` to conversation_memory
- Enhanced memory context tracking

---

## 🗄️ Database Schema

### Core Tables

#### **personas**
```sql
id              UUID PRIMARY KEY
name            VARCHAR(255) NOT NULL
description     TEXT
template        TEXT NOT NULL
mode            VARCHAR(50)
loop_frequency  VARCHAR(50)
first_message   TEXT
image_path      VARCHAR(500)
is_active       BOOLEAN DEFAULT TRUE
created_at      TIMESTAMP
updated_at      TIMESTAMP
```

#### **modules**
```sql
id                      UUID PRIMARY KEY
name                    VARCHAR(255) NOT NULL
description             TEXT
content                 TEXT (nullable)
type                    VARCHAR(50) NOT NULL
trigger_pattern         VARCHAR(500)
script                  TEXT
execution_context       VARCHAR(50)  -- IMMEDIATE, POST_RESPONSE, ON_DEMAND
requires_ai_inference   BOOLEAN DEFAULT FALSE
stage_priority          INTEGER DEFAULT 100
is_active               BOOLEAN DEFAULT TRUE
created_at              TIMESTAMP
updated_at              TIMESTAMP
```

#### **conversations**
```sql
id               UUID PRIMARY KEY
title            VARCHAR(255) NOT NULL
persona_id       UUID REFERENCES personas(id)
provider_type    VARCHAR(50)
provider_config  JSONB
created_at       TIMESTAMP
updated_at       TIMESTAMP
```

#### **messages**
```sql
id               UUID PRIMARY KEY
conversation_id  UUID REFERENCES conversations(id) ON DELETE CASCADE
role             VARCHAR(50) NOT NULL
content          TEXT NOT NULL
thinking         TEXT
extra_data       JSONB
input_tokens     INTEGER
output_tokens    INTEGER
created_at       TIMESTAMP
updated_at       TIMESTAMP
```

#### **conversation_states**
```sql
id               UUID PRIMARY KEY
conversation_id  UUID REFERENCES conversations(id) ON DELETE CASCADE
persona_id       UUID REFERENCES personas(id) ON DELETE CASCADE
module_id        UUID REFERENCES modules(id) ON DELETE CASCADE
state_key        VARCHAR(255) NOT NULL
state_value      JSONB NOT NULL
created_at       TIMESTAMP
updated_at       TIMESTAMP

UNIQUE(conversation_id, persona_id, module_id, state_key)
```

#### **conversation_memory**
```sql
id               UUID PRIMARY KEY
conversation_id  UUID REFERENCES conversations(id) ON DELETE CASCADE
persona_id       UUID REFERENCES personas(id) ON DELETE SET NULL
first_message_id UUID REFERENCES messages(id) ON DELETE SET NULL
content          TEXT NOT NULL
memory_type      VARCHAR(50)
importance       FLOAT DEFAULT 0.5
embedding        VECTOR(1536)  -- pgvector
metadata         JSONB
last_accessed    TIMESTAMP
access_count     INTEGER DEFAULT 0
created_at       TIMESTAMP
updated_at       TIMESTAMP
```

---

## 🔄 Migration Management

### Running Migrations

**Manual Migration:**
```bash
psql -U project2501 -d project2501 -f backend/app/database/migrations/001_*.sql
```

**All Migrations:**
```bash
cd backend/app/database/migrations
for file in *.sql; do
    psql -U project2501 -d project2501 -f "$file"
done
```

### Creating New Migration

1. **Name Convention**: `NNN_descriptive_name.sql`
2. **Include**:
   - Schema changes (CREATE, ALTER, DROP)
   - Data migrations if needed
   - Rollback notes in comments
3. **Test**: Run on test database first
4. **Document**: Update this README with migration details

**Example Migration:**
```sql
-- Migration 009: Add feature X
-- Created: 2025-XX-XX

BEGIN;

ALTER TABLE modules
ADD COLUMN new_field VARCHAR(255);

COMMIT;

-- Rollback:
-- ALTER TABLE modules DROP COLUMN new_field;
```

---

## 🔌 Connection Pooling

### Pool Configuration

```python
pool_size=10           # Idle connections maintained
max_overflow=20        # Additional connections allowed
pool_pre_ping=True     # Validate before use
pool_recycle=300       # Recycle after 5 minutes
```

### Connection Lifecycle

1. **Request Start**: `get_db()` creates session
2. **Request Processing**: Session used for queries
3. **Request End**: Session closed (connection returned to pool)
4. **Pool Management**: SQLAlchemy manages connection reuse

### Connection Health

**Pre-Ping**: Validates connection before handing to application
```python
# SQLAlchemy automatically pings with:
SELECT 1
```

**Connection Test**:
```python
status = await db_manager.test_connection()
```

---

## 🔐 Database Security

### Connection Security
- **Environment Variables**: Credentials stored in `.env`
- **URL Encoding**: Special characters escaped
- **SSL Support**: Can enable with connection string parameter

### Access Control
- **Database User**: `project2501` with limited permissions
- **Schema Ownership**: project2501 owns all tables
- **RLS (Future)**: Row-level security for multi-tenancy

---

## 📊 Performance Considerations

### Indexing
- **Primary Keys**: UUID indexes on all tables
- **Foreign Keys**: Automatic indexes on relationships
- **Timestamps**: Indexes on created_at for sorting
- **Vector Search**: pgvector HNSW index on embeddings

### Query Optimization
- **Connection Pooling**: Reduces connection overhead
- **Prepared Statements**: SQLAlchemy uses parameterized queries
- **Lazy Loading**: Relationships loaded on-demand
- **Eager Loading**: Use `joinedload()` for known relationships

---

## 🧪 Testing

### Test Database
```bash
# Create test database
createdb -U project2501 project2501_test

# Run migrations
cd backend/app/database/migrations
for file in *.sql; do
    psql -U project2501 -d project2501_test -f "$file"
done
```

### Database Fixtures
```python
import pytest
from app.database.connection import db_manager

@pytest.fixture
def db_session():
    session = db_manager.get_session()
    yield session
    session.rollback()
    session.close()
```

---

## 🐛 Troubleshooting

### Connection Issues

**Problem**: `OperationalError: connection refused`
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Check connection settings
psql -U project2501 -d project2501 -h localhost
```

**Problem**: `OperationalError: too many connections`
```python
# Reduce pool size
db_manager.engine = create_engine(url, pool_size=5, max_overflow=10)
```

**Problem**: `TimeoutError: connection pool exhausted`
- Check for unclosed sessions
- Ensure FastAPI dependency closes sessions
- Monitor connection usage

### Migration Issues

**Problem**: Migration fails halfway
```bash
# Check database state
psql -U project2501 -d project2501 -c "\d"

# Manual rollback if needed
psql -U project2501 -d project2501 -c "ROLLBACK;"
```

**Problem**: Migration already applied
- Add idempotency checks: `IF NOT EXISTS`
- Track applied migrations in table (future)

---

## 📝 Notes

- Database connections automatically managed by connection pool
- Sessions must be closed after use (handled by FastAPI dependency)
- Migrations are forward-only (no automatic rollback)
- UUID primary keys used for all tables (security + distributed systems)
- PostgreSQL 12+ required for all features
- pgvector extension required for conversation memory
