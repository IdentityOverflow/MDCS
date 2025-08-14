# Project 2501 Backend

A FastAPI-based backend service for the Project 2501 Cognitive Systems Framework, providing database connectivity, AI provider integration, and conversation management.

## 🏗️ Architecture

The backend follows a clean, modular architecture based on the project's ArchitecturePlan.md:

```
backend/
├── app/
│   ├── api/                 # API route handlers
│   │   ├── database.py      # Database connection endpoints
│   │   └── __init__.py
│   ├── core/                # Core configuration and settings
│   │   ├── config.py        # Environment-based configuration
│   │   └── __init__.py
│   ├── database/            # Database connection management
│   │   ├── connection.py    # SQLAlchemy connection manager
│   │   ├── migrations/      # Database migrations (future)
│   │   └── __init__.py
│   ├── models/              # Database models
│   │   ├── base.py          # Base model with common fields
│   │   ├── conversation.py  # Conversation and Message models
│   │   ├── persona.py       # AI Persona configurations
│   │   ├── module.py        # Cognitive system modules
│   │   └── __init__.py
│   ├── services/            # Business logic services (future)
│   ├── utils/               # Utility functions (future)
│   └── main.py              # FastAPI application entry point
├── tests/                   # Comprehensive test suite
│   ├── unit/                # Unit tests for all components
│   └── integration/         # Integration tests (future)
├── requirements.txt         # Python dependencies
├── requirements-dev.txt     # Development dependencies
├── pyproject.toml          # Project configuration
├── .env.example            # Environment variables template
└── README.md               # This file
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- PostgreSQL database
- Conda (Miniconda/Anaconda/Miniforge)

### Installation

1. **Run the installation script:**
   ```bash
   ./scripts/install_BE.sh
   ```

2. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials
   ```

3. **Start the server:**
   ```bash
   ./scripts/run_BE.sh
   ```

The backend will be available at:
- **API**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **OpenAPI Schema**: http://localhost:8000/openapi.json

## ⚙️ Configuration

The backend uses environment-based configuration via `.env` file:

### Required Environment Variables

```bash
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=project2501
DB_USER=your_username
DB_PASSWORD=your_password

# Application Configuration (Optional)
APP_NAME=Project 2501 Backend
DEBUG=false
```

Configuration is managed through `app/core/config.py` using pydantic-settings for type-safe environment variable loading.

## 🗄️ Database Models

### Base Model
All models inherit from `Base` which provides:
- `id`: UUID primary key
- `created_at`: Automatic timestamp
- `updated_at`: Automatic timestamp
- `to_dict()`: Serialization method

### Core Models

#### Conversation
Represents chat sessions between users and AI personas.
```python
class Conversation(Base):
    title: str
    provider_type: str  # "openai", "ollama", etc.
    provider_config: dict  # Provider configuration snapshot
    messages: List[Message]  # Related messages
```

#### Message  
Individual messages within conversations.
```python
class Message(Base):
    conversation_id: UUID
    role: MessageRole  # USER, ASSISTANT, SYSTEM
    content: str
    extra_data: dict  # Additional message metadata
    input_tokens: int  # Token usage tracking
    output_tokens: int
```

#### Persona
AI persona configurations and templates.
```python
class Persona(Base):
    name: str
    description: str
    model: str  # AI model identifier
    template: str  # Persona prompt template
    mode: str  # "reactive" or "autonomous"
    first_message: str
    image_path: str
    extra_data: dict
    is_active: bool
```

#### Module
Cognitive system modules for extending AI capabilities.
```python
class Module(Base):
    name: str
    description: str
    content: str  # Static content or Python code
    type: ModuleType  # SIMPLE or ADVANCED
    trigger_pattern: str  # Activation pattern
    script: str  # Python script for advanced modules
    timing: ExecutionTiming  # BEFORE, AFTER, CUSTOM
    extra_data: dict
    is_active: bool
```

## 🛠️ API Endpoints

### Core Endpoints

- **GET /** - Service information and status
- **GET /health** - Health check endpoint

### Database Endpoints

- **GET /api/database/test** - Test database connection
  ```json
  {
    "status": "success",
    "message": "Database connection successful", 
    "database": "project2501",
    "version": "PostgreSQL 16.9",
    "host": "localhost",
    "port": 5432,
    "error_type": null
  }
  ```

- **GET /api/database/info** - Get database information and table list

## 🧪 Testing

The backend includes a comprehensive test suite covering all components:

### Test Structure
```
tests/
├── unit/
│   ├── test_config.py           # Configuration management tests
│   ├── test_database_connection.py  # Database connection tests
│   ├── test_models.py           # Database model tests
│   ├── test_main.py             # FastAPI application tests
│   └── test_database_api.py     # API endpoint tests
└── fixtures/                    # Test fixtures and utilities
```

### Running Tests
```bash
# Activate environment
conda activate project2501

# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/unit/test_models.py -v
```

### Test Coverage
- **Configuration Management**: Environment loading, validation, defaults
- **Database Connection**: Connection pooling, error handling, testing
- **Models**: CRUD operations, relationships, validation
- **API Endpoints**: Success/error responses, data validation
- **FastAPI Application**: CORS, lifecycle management, routing

## 🔧 Development

### Code Quality Tools

The project includes development dependencies for code quality:
```bash
pip install -r requirements-dev.txt
```

### Database Migrations

Database schema changes are managed through SQLAlchemy. The models automatically create tables on startup via:
```python
Base.metadata.create_all(bind=engine)
```

For production deployments, consider using Alembic for proper migration management.

## 🚢 Deployment

### Production Configuration

1. **Set production environment variables:**
   ```bash
   DEBUG=false
   DB_HOST=your_production_host
   # ... other production values
   ```

2. **Run without auto-reload:**
   ```bash
   ./scripts/run_BE.sh --no-reload
   ```

3. **Use a production WSGI server like Gunicorn:**
   ```bash
   pip install gunicorn
   gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
   ```

## 🔗 Integration

### Frontend Integration

The backend is designed to work with the Vue.js frontend:

- **CORS Configuration**: Allows requests from `localhost:3000` and `localhost:5173`
- **Database Test Integration**: Frontend Test Connection button calls `/api/database/test`
- **Stateless Architecture**: AI provider configurations sent with each request

### Future Integrations

The architecture supports future integration of:
- AI Provider Services (OpenAI, Ollama, Anthropic)
- Conversation Management APIs
- Real-time Chat via WebSocket
- Authentication and Authorization
- File Upload and Management

## 📋 Implementation Status

### ✅ Completed Features

- [x] Complete FastAPI application structure
- [x] Environment-based configuration management
- [x] PostgreSQL database connection with SQLAlchemy
- [x] Core database models (Conversation, Message, Persona, Module)
- [x] Database connection test API endpoint
- [x] CORS configuration for frontend integration
- [x] Comprehensive test suite (90%+ coverage)
- [x] Installation and run scripts
- [x] Error handling and logging
- [x] Frontend Test Connection integration

### 🔄 Next Steps

- [ ] AI Provider Integration (OpenAI-compatible, Ollama)
- [ ] Chat API endpoints with streaming support
- [ ] Conversation management (CRUD operations)
- [ ] Persona and Module management APIs
- [ ] Authentication and user management
- [ ] WebSocket support for real-time chat
- [ ] File upload and management
- [ ] Advanced logging and monitoring
- [ ] Database migration system
- [ ] API rate limiting and caching

## 🤝 Contributing

1. Follow the existing code structure and patterns
2. Write tests for new functionality
3. Update this README when adding new features
4. Use type hints throughout the codebase
5. Follow FastAPI and SQLAlchemy best practices

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Project 2501 Backend** - Built with FastAPI, SQLAlchemy, and PostgreSQL for the Cognitive Systems Framework.