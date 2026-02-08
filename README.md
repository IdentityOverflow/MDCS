> NOTE: The progress on this project has been halted. The main goals I had in mind for this system has already been achieved by [OpenClaw](https://github.com/openclaw/openclaw), so I've moved on to other projects.
Check out my other recent work: 
> - [Recursive Observer Framework](https://github.com/IdentityOverflow/idea_drawer/blob/main/ro_framework/ro_framework.md)
> - [Organic Cognitive Architecture (OCA)](https://github.com/IdentityOverflow/idea_drawer/blob/main/organic_cognitive_architecture_oca.md)

# Modular Dynamic Context System
A full-stack web application for managing AI conversations with dynamic, modular system prompts. The system allows system prompts to be composed from reusable modules that can execute Python scripts, call AI models, and maintain state across conversations.

## Overview

MDCS addresses the problem of system prompts becoming lost or diluted in long conversations by treating them as executable, stateful components rather than static text. System prompts are built from modules that can:

- Execute sandboxed Python scripts with access to conversation data
- Call AI models for self-reflection or generation tasks
- Persist state between conversations
- Execute conditionally based on triggers or keywords

The system uses a 5-stage execution pipeline to control when modules run relative to the main AI response, enabling pre-processing, post-processing, and background analysis.

## Web Interface Screenshots 

![Chat Interface](screenshots/Screenshot%20from%202026-01-22%2012-50-00.png)
*Golden ration layout with 4 areas, the main chat interface with markdown rendering, a navigation/management area connected to the control panel area, and an additional smaller information display area*

![Module Editor](screenshots/Screenshot%20from%202026-01-22%2012-45-39.png)
*Alternate expanded display for navigation/management + control panel areas, currently showing the advanced module editor with Python scripting, trigger patterns, and test functionality*

![Persona Editor](screenshots/Screenshot%20from%202026-01-22%2012-48-13.png)
*Same alternate display, currently showing persona configuration with template system and available modules suggest box*

![Modules Overview](screenshots/Screenshot%20from%202026-01-22%2012-56-21.png)
*Module management (on the right), chat controls, and expandable thinking process from reasoning models (on the left)*

## Architecture

### Backend (Python + FastAPI)

- **API Layer**: REST endpoints and WebSocket for real-time chat
- **Module System**: Simple (text) and Advanced (Python script) modules
- **Plugin System**: ~60 functions available to module scripts (`ctx.*`)
- **Execution Pipeline**: 5-stage system for controlled module execution
- **Script Engine**: RestrictedPython sandbox for safe script execution
- **Provider Abstraction**: Support for Ollama and OpenAI-compatible APIs
- **Database**: PostgreSQL with SQLAlchemy ORM

### Frontend (Vue 3 + TypeScript)

- **Chat Interface**: Real-time streaming with WebSocket
- **Module Editor**: Create and edit modules with Python scripting
- **Persona Management**: Configure AI personalities with modular templates
- **Code Editor**: CodeMirror integration for script editing
- **Markdown Rendering**: Full GFM support with custom styling

### Technology Stack

**Backend:**
- FastAPI 0.104.1
- Python 3.10+
- SQLAlchemy 2.0.23
- PostgreSQL 12+
- RestrictedPython 7.0
- uvicorn (ASGI server)

**Frontend:**
- Vue 3.5.18 (Composition API)
- TypeScript 5.8
- Vite 7.0.6 (build tool)
- Pinia (state management)
- CodeMirror 6 (code editor)
- marked 16.2.0 (markdown parser)

**Deployment:**
- Docker + Docker Compose
- Nginx (frontend reverse proxy)
- PostgreSQL 14

## Key Features

### Module System

**Simple Modules**: Static text that gets inserted into the system prompt.

**Advanced Modules**: Python scripts with access to:
- Conversation history and metadata
- Time/date functions
- AI generation and reflection capabilities
- Memory storage and retrieval
- JSON manipulation utilities

**Execution Contexts:**
- `IMMEDIATE`: Executes before the main AI response
- `POST_RESPONSE`: Executes after the main AI response
- `ON_DEMAND`: Only executes when explicitly referenced

**Trigger Patterns**: Modules can execute based on keywords, regex patterns, or always (`*`).

### 5-Stage Execution Pipeline

1. **Stage 1 - Template Preparation**: Load persona template, resolve module references, execute simple modules and non-AI immediate modules
2. **Stage 2 - Pre-response AI**: Execute immediate modules that require AI inference
3. **Stage 3 - Main Response**: AI generates the response using the resolved system prompt
4. **Stage 4 - Post-response Non-AI**: Fast post-processing modules (logging, analytics)
5. **Stage 5 - Post-response AI**: Background AI analysis and reflection

Stages 4 and 5 save their outputs to the database, which are then injected into Stage 1 of the next conversation. This enables persistent, evolving context.

### Chat System

- **WebSocket Communication**: Bidirectional real-time messaging
- **Streaming**: Token-by-token response streaming
- **Cancellation**: Sub-100ms cancellation latency
- **Provider Support**: Ollama (local models) and OpenAI-compatible APIs
- **Reasoning Models**: Support for models with thinking/reasoning output (e.g., gpt-oss)
- **Message Editing**: Edit and regenerate messages
- **Markdown Rendering**: Full GitHub Flavored Markdown support

### Plugin Functions

Modules have access to plugin functions via the `ctx` object:

**Time:**
- `ctx.get_current_time(format)` - Current time with formatting
- `ctx.get_relative_time(offset)` - Time with offset
- `ctx.is_business_hours()` - Business hours check
- `ctx.get_day_of_week()` - Day name

**Conversation:**
- `ctx.get_message_count()` - Total messages
- `ctx.get_recent_messages(limit)` - Message history
- `ctx.get_conversation_summary()` - Metadata
- `ctx.get_persona_info()` - Persona details

**AI:**
- `ctx.generate(instructions)` - On-demand AI generation
- `ctx.reflect(instructions)` - AI self-reflection with current system prompt

**Memory:**
- `ctx.should_compress_buffer()` - Check if compression needed
- `ctx.get_buffer_messages(start, end)` - Message window
- `ctx.store_memory(content)` - Save compressed memory
- `ctx.get_recent_memories(limit)` - Retrieve memories

**Utilities:**
- `ctx.to_json()`, `ctx.from_json()` - JSON operations
- `ctx.join_strings()`, `ctx.count_words()` - String utilities

### Security

- **RestrictedPython Sandbox**: No file system or network access from modules
- **Whitelisted Imports**: Only safe modules (datetime, math, json, re)
- **Reflection Depth Limiting**: Maximum 3 levels to prevent infinite nesting
- **Circular Reference Detection**: Prevents infinite module loops
- **SQL Injection Prevention**: Parameterized queries via SQLAlchemy
- **External Link Security**: Automatic `rel="noopener noreferrer"` on links

## Installation

### Docker Deployment (Recommended)

**Prerequisites:**
- Docker Engine 20.10+
- Docker Compose V2
- 2GB free disk space

**Steps:**
```bash
# Clone repository
git clone https://github.com/IdentityOverflow/MDCS.git
cd MDCS

# Configure environment
cp .env.docker .env
# Edit .env and set a strong DB_PASSWORD

# Start services
docker compose up -d

# View logs
docker compose logs -f
```

**Access:**
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

**Using Ollama on Host (Linux):**

For the Docker backend to connect to Ollama running on your host machine, you need to configure Ollama to listen on all network interfaces:

1. Edit the Ollama systemd service:
   ```bash
   sudo systemctl edit ollama.service
   ```

2. Add the following configuration:
   ```ini
   [Service]
   Environment="OLLAMA_HOST=0.0.0.0:11434"
   ```

3. Reload and restart Ollama:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl restart ollama
   ```

4. Verify Ollama is listening on all interfaces:
   ```bash
   ss -tlnp | grep 11434
   # Should show: 0.0.0.0:11434
   ```

Once configured, you can use this connection URL in the settings for accessing Ollama:
`http://host.docker.internal:11434`

### Manual Installation

**Backend:**
```bash
# Install PostgreSQL
sudo apt install postgresql postgresql-contrib

# Create database
sudo -u postgres psql
CREATE USER mdcs WITH PASSWORD 'password';
CREATE DATABASE mdcs OWNER mdcs;
GRANT ALL PRIVILEGES ON DATABASE mdcs TO mdcs;
\q

# Initialize schema
psql -U mdcs -d mdcs -f backend/init_db.sql

# Install backend
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with database credentials

# Run
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

**AI Provider:**
- Install Ollama: `curl -fsSL https://ollama.com/install.sh | sh`
- Or use OpenAI API / LM Studio / compatible API

## Usage

### Set connection to AI provider

1. Navigate to **Settings** → **Ollama connection** or **OpenAI connection**
2. Ensure the connection enpoint is available and set correctly, primarily **BASE URL** and **API KEY** (this can be a random string in case of local providers like LM Studio)

### Creating a Persona

1. Navigate to **Personas** → **+ NEW**
2. Set name and description
3. Write template with module references:
   ```
   You are a helpful assistant. @greeting_module

   Current time: @time_module

   Conversation context:
   ${conversation_history}
   ```
4. Select mode: **REACTIVE** (chat) or **AUTONOMOUS** (experimental)
5. Optionally upload avatar image

### Creating Modules

**Simple Module:**
1. Navigate to **Modules** → **+ NEW**
2. Select Type: **Simple**
3. Enter static text content
4. Set execution context: **IMMEDIATE**

**Advanced Module:**
1. Select Type: **Advanced**
2. Write Python script:
   ```python
   conversation_history = ctx.get_recent_messages(30)
   ```
3. Set trigger pattern (optional): keyword, regex, or `*` for always
4. Set execution context **IMMEDIATE** or **POST_RESPONSE**
5. Test script with **TEST SCRIPT** button

The script analyzer automatically detects if the module requires AI inference based on calls to `ctx.generate()` or `ctx.reflect()`.

### Template Syntax

- `@module_name` - Insert module output
- `${variable}` - Insert variable from module script

### Chat Interface

- Select persona from sidebar
- Choose AI provider and model in chat controls
- Adjust temperature, top-p, max tokens as needed
- Enable markdown rendering for formatted output
- Reasoning models show expandable "Thinking Process" section
- Edit messages by hovering and clicking edit icon
- Debug panel shows resolved system prompts and execution stages

## Project Structure

```
mdcs/
├── backend/
│   ├── app/
│   │   ├── api/           # REST and WebSocket endpoints
│   │   ├── core/          # Script engine, plugins, analyzers
│   │   ├── models/        # SQLAlchemy database models
│   │   ├── services/      # Business logic, providers
│   │   ├── plugins/       # Plugin function implementations
│   │   └── database/      # Connection and migrations
│   ├── tests/             # Backend tests
│   ├── init_db.sql        # Database schema
│   └── requirements.txt   # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── components/    # Vue components
│   │   ├── views/         # Page views
│   │   ├── composables/   # Vue composables (logic)
│   │   ├── types/         # TypeScript type definitions
│   │   └── assets/        # CSS, images
│   └── package.json       # Node dependencies
├── docker-compose.yml     # Docker orchestration
└── screenshots/           # UI screenshots
```

## Development

**Backend Type Checking:**
```bash
cd backend
mypy app/
```

**Frontend Type Checking:**
```bash
cd frontend
npm run type-check
```

**Run Tests:**
```bash
cd backend
pytest -v
```

**Database Migrations:**
Migrations are SQL files in `backend/app/database/migrations/`. Apply them manually:
```bash
psql -U mdcs -d mdcs -f backend/app/database/migrations/NNN_migration.sql
```

**Adding Plugin Functions:**
1. Create file in `backend/app/plugins/`
2. Use decorator:
   ```python
   from app.core.script_plugins import plugin_registry

   @plugin_registry.register("my_function")
   def my_function(param: str, db_session=None, _script_context=None):
       """Function description."""
       return result
   ```
3. Function auto-loads on startup
4. Available as `ctx.my_function()` in module scripts

## Limitations/Ongoing work

- Memory compression is functional but still experimental and higly dependatnt on the model
- Autonomous mode is not fully implemented
- Vector database / semantic search planned but not yet implemented
- No multi-modal support yet (images, audio, video)
- Tool use/MCP support not fully impemented
- Chat rooms not implemented
- No rate limiting
- No user authentication system (single-user)

## Docker Commands

```bash
# View logs
docker compose logs -f
docker compose logs -f backend
docker compose logs -f frontend

# Restart services
docker compose restart

# Rebuild after code changes
docker compose up -d --build

# Stop and remove (keeps data)
docker compose down

# Stop and remove including data
docker compose down -v

# Check health
docker compose ps
```

## Configuration

**Environment Variables (.env):**
```bash
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=mdcs
DB_USER=mdcs
DB_PASSWORD=your_password
DATABASE_URL=postgresql://mdcs:your_password@localhost:5432/mdcs

# Application
# Add other config as needed
```

**AI Provider Settings (stored in browser localStorage):**
- Ollama: host URL, model
- OpenAI: API key, model, base URL

## License

MIT License - see LICENSE file for details.

Copyright (c) 2025 Paul Panțiru

## Contributing

This is a solo development project in early stages. Contributions are welcome but please note:
- Follow existing code style
- Write tests for new features
- Update documentation
- Keep commits focused

## Acknowledgments

- FastAPI for the backend framework
- Vue.js team for the frontend framework
- Marked.js for markdown parsing
- RestrictedPython for safe script execution
- Anthropic, Google, Mistral and OpenAI for the AI models / coding agents
- Ollama and LM Studio for local inference
