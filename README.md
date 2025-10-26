# Project 2501

`Disclaimer: I am a solo developer and this is still very early in development.`

**Dynamic System Prompt Architecture for AI Conversations**

Project 2501 is a full-stack web application that treats system prompts as living, modular components that stay visible and adapt throughout conversations. It provides a framework for building AI personas with dynamic, state-aware system prompts powered by Python scripts and a staged execution pipeline.

## 🎯 Core Innovation

Traditional AI systems use static system prompts that get lost in token limits. Project 2501 attempts to solve this with:

- **Dynamic Modules**: System prompts composed of simple text templates and Python scripts
- **Staged Execution**: 5-stage pipeline ensures predictable, ordered execution
- **Self-Reflection**: AI can introspect and adapt using `ctx.reflect()` and `ctx.generate()`
- **Persistent State**: Module outputs persist with long conversations
- **Real-time Updates**: System prompts evolve during chat without context rot

## ✨ Key Features

### Module System
- **Simple Modules**: Static text templates with `@module_name` references
- **Advanced Modules**: Python scripts with extensible plugin functions
- **Trigger Patterns**: Execute modules based on keywords, regex, or always
- **Variable Substitution**: `${variable}` outputs from script execution

### Staged Execution Pipeline
- **Stage 1**: Template preparation (simple modules + previous state)
- **Stage 2**: Pre-response AI processing (immediate AI modules)
- **Stage 3**: Main AI response generation
- **Stage 4**: Post-response processing (non-AI modules)
- **Stage 5**: Post-response AI analysis (reflection modules)

### Chat System
- **Provider Support**: Ollama and OpenAI-compatible APIs
- **WebSocket Communication**: Real-time bidirectional messaging (SSE removed)
- **Cancellation**: <100ms latency for stopping AI generation ([Details](WEBSOCKET_CANCELLATION.md))
- **Streaming Responses**: Token-by-token streaming
- **Conversation Persistence**: Full message history with thinking content
- **Memory Compression**: Long-term memory with AI summaries (experimental)

### AI Capabilities
- **Reflection**: AI self-assessment using current system prompt (using `ctx.reflect()`)
- **Generation**: On-demand AI calls from within modules (using `ctx.generate()`)
- **Conversation Access**: Query message history and metadata
- **Time/Date Functions**: Context-aware temporal information
- **Memory Management**: Episodic memory with buffer compression

## 🏗️ Architecture

### Technology Stack

**Frontend**
- Vue 3.5.18 (Composition API)
- TypeScript
- Pinia (state management)
- Vite (build tool)
- CodeMirror (code editor)
- Marked (markdown rendering)

**Backend**
- FastAPI 0.104.1
- Python 3.10+
- SQLAlchemy 2.0.23
- RestrictedPython 7.0 (sandboxed execution)
- PostgreSQL with pgvector

**Database**
- PostgreSQL 12+
- UUID primary keys
- JSONB for flexible metadata
- pgvector for embeddings (future)

### Project Structure

```
project2501/
├── frontend/              # Vue 3 application
│   ├── src/
│   │   ├── components/   # UI components
│   │   ├── views/        # Page views
│   │   ├── stores/       # Pinia stores
│   │   ├── types/        # TypeScript types
│   │   └── router/       # Vue Router config
│   └── package.json
├── backend/              # FastAPI application
│   ├── app/
│   │   ├── api/         # REST endpoints
│   │   ├── core/        # Script engine, plugins
│   │   ├── models/      # Database models
│   │   ├── services/    # Business logic
│   │   ├── plugins/     # Plugin functions
│   │   └── database/    # Connection, migrations
│   └── requirements.txt
├── scripts/             # Installation/run scripts
└── tests/              # Test suite (400+ tests)
```

## 📋 Prerequisites

### Docker Deployment (Recommended)
- Docker Engine 20.10+
- Docker Compose V2
- 2GB free disk space
- *Optional*: Ollama on host for local AI

### Manual Installation
**Backend:**
- Python 3.10+
- Conda or Miniconda
- PostgreSQL 12+

**Frontend:**
- Node.js 20.19.0+ or 22.12.0+
- npm 9+

**AI Provider (at least one):**
- Ollama (local models)
- OpenAI API key
- Any OpenAI-compatible API (LM Studio, etc.)

## 🚀 Installation

### Quick Start with Docker (Recommended)

Docker Compose handles all dependencies and setup.

#### Prerequisites
- Docker Engine 20.10+
- Docker Compose V2
- 2GB free disk space

#### Deploy with Docker Compose

```bash
# 1. Clone repository
git clone https://github.com/IdentityOverflow/project2501.git
cd project2501

# 2. Configure environment
cp .env.docker .env
nano .env  # Change DB_PASSWORD to a strong password

# 3. Start all services
docker compose up -d

# 4. Verify deployment
docker compose ps
docker compose logs -f  # View startup logs
```

**Access:**
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

**Ollama on host:**
- Backend: `http://host.docker.internal:11434`
- Frontend: `http://localhost:11434` (configured in UI)

#### Docker Management Commands

```bash
# View logs
docker compose logs -f             # All services
docker compose logs -f backend     # Backend only
docker compose logs -f frontend    # Frontend only

# Stop services (keeps data)
docker compose stop

# Start stopped services
docker compose start

# Restart services
docker compose restart

# Stop and remove containers (keeps volumes)
docker compose down

# Stop and remove everything including data volumes
docker compose down -v

# Rebuild after code changes
docker compose up -d --build

# Check service health
docker compose ps
```

#### Docker Architecture

**Services:**
- **db**: PostgreSQL 14 with automatic schema initialization
- **backend**: FastAPI application on port 8000
- **frontend**: Vue 3 app served by Nginx on port 5173

**Volumes:**
- `postgres_data`: Database persistence
- `./backend/static`: Persona images and uploads

**Network:**
- Custom bridge network `project2501_network` for service communication
- Backend has host network access for Ollama connectivity

---

### Manual Installation (Development)

For local development without Docker:

### 1. Clone Repository

```bash
git clone https://github.com/IdentityOverflow/project2501.git
cd project2501
```

### 2. Database Setup

#### Install PostgreSQL

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

**macOS:**
```bash
brew install postgresql@14
brew services start postgresql@14
```

**Windows:**
Download and install from [postgresql.org](https://www.postgresql.org/download/windows/)

#### Create Database and User

```bash
# Access PostgreSQL as postgres user
sudo -u postgres psql

# In PostgreSQL shell:
CREATE USER project2501 WITH PASSWORD 'yourStrongPasswordHere';
CREATE DATABASE project2501 OWNER project2501;
GRANT ALL PRIVILEGES ON DATABASE project2501 TO project2501;
\q

# Initialize database schema
psql -U project2501 -d project2501 -f backend/init_db.sql
```

### 3. Backend Setup

#### Install Conda Environment

```bash
# Make installation script executable
chmod +x scripts/install_BE.sh

# Run installation
./scripts/install_BE.sh
```

This will:
- Create a conda environment named `project2501`
- Install Python 3.10
- Install all Python dependencies from `requirements.txt`

#### Configure Environment

```bash
# Copy environment template
cp backend/.env.example backend/.env

# Edit configuration
nano backend/.env
```

**backend/.env** should contain:
```bash
# Database connection
DB_HOST=localhost
DB_PORT=5432
DB_NAME=project2501
DB_USER=project2501
DB_PASSWORD=yourStrongPasswordHere

# Database URL (alternative format)
DATABASE_URL=postgresql://project2501:yourStrongPasswordHere@localhost:5432/project2501
```

#### Verify Installation

```bash
# Activate environment
source ~/miniforge3/etc/profile.d/conda.sh
conda activate project2501

# Run tests
cd backend
pytest -v

# Should show: 400+ tests passing
```

### 4. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Verify installation
npm run type-check
```

### 5. AI Provider Setup

#### Option A: Ollama (Local Models)

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull a model (example: Llama 3.2)
ollama pull llama3.2:3b

# Verify Ollama is running
curl http://localhost:11434/api/tags
```

#### Option B: OpenAI API

1. Get API key from [platform.openai.com](https://platform.openai.com)
2. No installation needed - configure in frontend settings

#### Option C: LM Studio (Local with OpenAI API)

1. Download [LM Studio](https://lmstudio.ai/)
2. Download a model (e.g., Mistral, Llama)
3. Start local server on port 1234
4. Configure frontend to use `http://localhost:1234/v1`

## 🎮 Running the Application

### Start Backend Server

```bash
# Using the provided script (recommended)
./scripts/run_BE.sh

# Or manually
source ~/miniforge3/etc/profile.d/conda.sh
conda activate project2501
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Backend will be available at:
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Database Test**: http://localhost:8000/api/database/test

### Start Frontend Development Server

```bash
cd frontend
npm run dev
```

Frontend will be available at:
- **Application**: http://localhost:5173

### Production Build

```bash
# Frontend production build
cd frontend
npm run build
npm run preview  # Preview production build

# Backend production mode
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000  # No --reload
```

## 📖 Usage Guide

### Creating a Persona

1. Navigate to **Personas**
2. Click **New Persona**
3. Configure:
   - **Name**: Display name for the persona
   - **Description**: Optional description
   - **Template**: System prompt with module references
   - **Mode**: Reactive (chat) or Autonomous (experimental)
   - **Image**: Optional avatar

**Example Template:**
```
You are a helpful AI assistant. @greeting_module

Current time: @time_module

Recent conversation context:
@memory_module
```

### Creating Modules

#### Simple Module (Static Text)

1. Navigate to **Modules**
2. Click **New Module**
3. Select **Type**: Simple
4. Enter **Content**: Your static text
5. Set **Execution Context**: When to execute

**Example Simple Module:**
```
Name: greeting_module
Type: Simple
Content: Hello! I'm here to assist you with any questions you have.
Execution Context: IMMEDIATE
```

#### Advanced Module (Python Script)

1. Select **Type**: Advanced
2. Write Python script using `ctx` context object
3. Trigger Pattern: When to execute (keyword, regex, or `*` for always)
4. Execution Context: IMMEDIATE or POST_RESPONSE

**Example Advanced Module:**
```python
Name: time_module
Type: Advanced
Trigger: leave empty
Execution Context: IMMEDIATE

Script:
current_time = ctx.get_current_time("%H:%M")
day = ctx.get_day_of_week()
is_business = ctx.is_business_hours()

status = "during business hours" if is_business else "outside business hours"
ctx.set_variable("time_info", f"{day} at {current_time} ({status})")
```

Template reference: `${time_info}`

### Available Plugin Functions

#### Time Functions
- `ctx.get_current_time(format)` - Current time
- `ctx.get_relative_time(minutes_offset)` - Time +/- offset
- `ctx.is_business_hours()` - Business hours check
- `ctx.get_day_of_week()` - Day name

#### Conversation Functions
- `ctx.get_message_count()` - Total messages
- `ctx.get_recent_messages(limit)` - Formatted message history
- `ctx.get_conversation_summary()` - Metadata and statistics
- `ctx.get_persona_info()` - Current persona details

#### AI Functions
- `ctx.generate(instructions)` - AI generation
- `ctx.generate(instructions, input_text)` - Generation with input
- `ctx.reflect(instructions)` - Self-reflective AI processing

#### Memory Functions
- `ctx.should_compress_buffer()` - Check compression trigger
- `ctx.get_buffer_messages(start, end)` - Buffer window messages
- `ctx.store_memory(compressed_content)` - Save compressed memory
- `ctx.get_recent_memories(limit)` - Retrieve memories

#### Utility Functions
- `ctx.to_json(data)` - Convert to JSON
- `ctx.from_json(json_str)` - Parse JSON
- `ctx.join_strings(list)` - Join strings
- `ctx.count_words(text)` - Word count

### Chat Configuration

**Provider Settings** (stored in browser localStorage):
- **Ollama**: Host URL, model selection
- **OpenAI**: API key, model, base URL

**Chat Controls**:
- **Temperature**: 0.0-1.0 (creativity vs consistency)
- **Max Tokens**: Response length limit
- **Streaming**: Enable/disable real-time output

## 🧪 Testing

### Backend Tests

```bash
cd backend

# Run all tests
pytest -v

# Run specific test file
pytest tests/unit/test_module_resolver.py -v

# Run with coverage
pytest --cov=app --cov-report=html
```

**Test Coverage:**
- Unit tests: Core functionality, models, services
- Integration tests: API endpoints, database
- Total: 400+ tests

### Frontend Tests

```bash
cd frontend

# Run unit tests
npm run test:unit

# Run with watch mode
npm run test:unit -- --watch
```

## 🔧 Development

### Code Quality

**Backend:**
```bash
cd backend

# Type checking
mypy app/

# Linting
flake8 app/

# Formatting
black app/
```

**Frontend:**
```bash
cd frontend

# Type checking
npm run type-check

# Linting
npm run lint

# Formatting
npm run format
```

### Database Migrations

Creating a new migration:
```bash
cd backend/app/database/migrations

# Create new migration file
# Name format: NNN_descriptive_name.sql
nano 009_your_new_migration.sql

# Test migration
psql -U project2501 -d project2501 -f 009_your_new_migration.sql
```

### Adding Plugin Functions

1. Create/edit file in `backend/app/plugins/`
2. Use decorator to register:

```python
from app.core.script_plugins import plugin_registry

@plugin_registry.register("my_function")
def my_function(param: str, db_session=None, _script_context=None):
    """Function description."""
    # Implementation
    return result
```

3. Function auto-loaded on app startup
4. Available as `ctx.my_function()` in scripts

## 🔐 Security Considerations

### Script Execution Safety
- **RestrictedPython Sandbox**: No file system or network access
- **Whitelisted Imports**: Safe modules only (datetime, math, json)
- **Reflection Depth Limiting**: Max 3 levels to prevent infinite nesting
- **Circular Reference Detection**: Prevents infinite module loops

### Database Security
- **UUID Primary Keys**: Non-enumerable IDs
- **Prepared Statements**: SQLAlchemy prevents SQL injection
- **Environment Variables**: Credentials in .env files

### API Security
- **CORS Configuration**: Configurable origins
- **Request Validation**: Pydantic models
- **Error Sanitization**: No sensitive data in responses
- **Rate Limiting**: Not yet implemented

## 🐛 Troubleshooting

### Docker Issues

**Issue**: Containers won't start
```bash
# Check Docker service is running
docker ps

# View container logs
docker compose logs -f

# Check for port conflicts
sudo netstat -tulpn | grep -E '5173|8000|5432'
```

**Issue**: Database initialization fails
```bash
# Check database logs
docker compose logs db

# Manually run initialization
docker compose exec db psql -U project2501 -d project2501 -f /docker-entrypoint-initdb.d/init_db.sql

# Recreate database volume if corrupted
docker compose down -v
docker compose up -d
```

**Issue**: Backend can't connect to host Ollama
```bash
# Verify Ollama is running on host
curl http://localhost:11434/api/tags

# Check Docker host gateway
docker compose exec backend ping host.docker.internal

# On Linux, you may need to use host IP instead:
# Find host IP: ip addr show docker0
# Update backend connection to: http://<host-ip>:11434
```

**Issue**: Permission denied on static volume
```bash
# Fix volume permissions
sudo chown -R $USER:$USER backend/static
docker compose restart backend
```

**Issue**: Frontend shows API connection errors
```bash
# Check backend is accessible
curl http://localhost:8000/health

# Verify nginx proxy configuration
docker compose exec frontend cat /etc/nginx/conf.d/default.conf

# Check backend logs for errors
docker compose logs backend
```

---

### Manual Installation Issues

### Backend Won't Start

**Issue**: `conda: command not found`
```bash
# Source conda initialization
source ~/miniforge3/etc/profile.d/conda.sh  # or ~/miniconda3/...
conda activate project2501
```

**Issue**: `ImportError: No module named 'app'`
```bash
# Make sure you're in the backend directory
cd backend
python -m uvicorn app.main:app
```

**Issue**: Database connection failed
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Test connection manually
psql -U project2501 -d project2501 -h localhost

# Verify .env file has correct credentials
cat backend/.env

# Initialize database if not done
psql -U project2501 -d project2501 -f backend/init_db.sql
```

### Frontend Issues

**Issue**: `Module not found` errors
```bash
# Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install
```

**Issue**: TypeScript errors
```bash
# Regenerate TypeScript cache
npm run type-check
```

## 🗺️ Roadmap

### Completed
- ✅ Dynamic system prompt architecture
- ✅ 5-stage execution pipeline with AI dependency detection
- ✅ Advanced modules with sandboxed Python scripts
- ✅ AI self-reflection and on-demand generation
- ✅ WebSocket-based chat with <100ms cancellation
- ✅ Conversation memory with AI compression (experimental)
- ✅ Ollama and OpenAI provider support

### Planned
- ⏳ Tool integration framework
- ⏳ Multi-modal support (images, audio)
- ⏳ Import/export for personas and modules
- ⏳ Vector-based memory retrieval
- ⏳ Rate limiting
- ⏳ User authentication

## 📚 Documentation

### Architecture Documentation
- [API Layer](backend/app/api/README.md) - REST and WebSocket endpoints
- [Core Layer](backend/app/core/README.md) - Script engine and plugins
- [Services Layer](backend/app/services/README.md) - Business logic
- [Models Layer](backend/app/models/README.md) - Database models
- [Plugins Layer](backend/app/plugins/README.md) - Module plugin functions

### API Reference
- Interactive API Docs: http://localhost:8000/docs (backend must be running)
- OpenAPI Schema: http://localhost:8000/openapi.json

## 🤝 Contributing

Contributions welcome:

1. Fork the repository
2. Create a feature branch
3. Run tests (`pytest` for backend, `npm test` for frontend)
4. Commit changes
5. Push and open a Pull Request

### Guidelines
- Write tests for new features
- Follow existing code style
- Update documentation
- Keep commits atomic
- Add docstrings to Python functions
- Use TypeScript types

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

Copyright (c) 2025 Paul Panțiru

---