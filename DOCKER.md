# Docker Deployment Guide

Complete guide for deploying Project 2501 using Docker Compose.

## Quick Start

```bash
# Clone and setup
git clone https://github.com/IdentityOverflow/project2501.git
cd project2501

# Configure environment
cp .env.docker .env
nano .env  # Update DB_PASSWORD

# Deploy
docker compose up -d

# Access
# Frontend: http://localhost:5173
# Backend: http://localhost:8000/docs
```

## Architecture

### Services

**Database (PostgreSQL 14)**
- Container: `project2501-db`
- Internal port: 5432 (not exposed to host)
- Volume: `postgres_data` for persistence
- Initialization: Automatic schema creation via `init_db.sql`

**Backend (FastAPI)**
- Container: `project2501-backend`
- Port: `8000:8000`
- Volume: `./backend/static` for uploads
- Features: Health checks, host Ollama connectivity

**Frontend (Vue + Nginx)**
- Container: `project2501-frontend`
- Port: `5173:80`
- Features: API proxy to backend, gzip compression

### Network

- Bridge network: `project2501_network`
- Service DNS: Containers communicate via service names
- Host access: Backend can reach `host.docker.internal` for Ollama

### Volumes

**Named volume:**
- `postgres_data` - Database persistence across restarts

**Bind mounts:**
- `./backend/static` - Persona images and uploads

## Configuration

### Environment Variables

Edit `.env` file:

```bash
# Database credentials
DB_NAME=project2501
DB_USER=project2501
DB_PASSWORD=your_strong_password_here  # CHANGE THIS!
```

### Ollama Integration

**Running Ollama on host machine:**

1. Install Ollama: `curl -fsSL https://ollama.com/install.sh | sh`
2. Pull model: `ollama pull llama3.2:3b`
3. Backend connects via: `http://host.docker.internal:11434`
4. Frontend users configure in UI: `http://localhost:11434`

**Running Ollama in Docker:**

Add to `docker-compose.yml`:

```yaml
services:
  ollama:
    image: ollama/ollama:latest
    container_name: project2501-ollama
    volumes:
      - ollama_data:/root/.ollama
    ports:
      - "11434:11434"
    networks:
      - project2501_network

volumes:
  ollama_data:
    name: project2501_ollama_data
```

Then configure both backend and frontend to use: `http://ollama:11434`

## Management Commands

### Viewing Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f db

# Last 50 lines
docker compose logs --tail=50 backend
```

### Service Control

```bash
# Start all services
docker compose up -d

# Stop all services (keeps data)
docker compose stop

# Start stopped services
docker compose start

# Restart services
docker compose restart

# Restart specific service
docker compose restart backend

# Stop and remove containers (keeps volumes)
docker compose down

# Stop and remove everything including volumes
docker compose down -v
```

### Rebuilding

```bash
# Rebuild all services
docker compose up -d --build

# Rebuild specific service
docker compose up -d --build backend

# Force recreation of containers
docker compose up -d --force-recreate
```

### Database Operations

```bash
# Access PostgreSQL shell
docker compose exec db psql -U project2501 -d project2501

# Backup database
docker compose exec db pg_dump -U project2501 project2501 > backup.sql

# Restore database
cat backup.sql | docker compose exec -T db psql -U project2501 -d project2501

# Reinitialize database (WARNING: destroys data)
docker compose down -v
docker compose up -d
```

### Health Checks

```bash
# Check service status
docker compose ps

# Test backend health
curl http://localhost:8000/health

# Test frontend health
curl http://localhost:5173/health

# Test database connection
docker compose exec backend python -c "
from app.database.connection import get_db_manager
import asyncio
manager = get_db_manager()
manager.initialize()
result = asyncio.run(manager.test_connection())
print(result)
"
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs for errors
docker compose logs backend

# Check for port conflicts
sudo netstat -tulpn | grep -E '5173|8000|5432'

# Verify Docker daemon is running
docker ps
```

### Database Issues

```bash
# Check database logs
docker compose logs db

# Verify schema initialization
docker compose exec db psql -U project2501 -d project2501 -c "\dt"

# Manually run initialization
docker compose exec db psql -U project2501 -d project2501 -f /docker-entrypoint-initdb.d/init_db.sql

# Reset database (WARNING: destroys all data)
docker compose down
docker volume rm project2501_postgres_data
docker compose up -d
```

### Backend Connection Issues

```bash
# Test database connectivity from backend
docker compose exec backend pg_isready -h db -p 5432 -U project2501

# Check environment variables
docker compose exec backend env | grep DB_

# Test Ollama connectivity
docker compose exec backend curl http://host.docker.internal:11434/api/tags
```

### Frontend Issues

```bash
# Check nginx configuration
docker compose exec frontend cat /etc/nginx/conf.d/default.conf

# Test backend connectivity from frontend
docker compose exec frontend wget -O- http://backend:8000/health

# Verify static files
docker compose exec frontend ls -la /usr/share/nginx/html
```

### Permission Issues

```bash
# Fix static volume permissions
sudo chown -R $USER:$USER backend/static
docker compose restart backend

# Check volume mounts
docker compose exec backend ls -la /app/static
```

## Production Considerations

### Security Hardening

1. **Change default credentials:**
   ```bash
   # Use strong random password for DB_PASSWORD
   openssl rand -base64 32
   ```

2. **Restrict exposed ports:**
   - Only expose frontend (5173) to internet
   - Backend (8000) should be internal only
   - Database (5432) should never be exposed

3. **Use secrets management:**
   - Consider Docker secrets or external secrets manager
   - Never commit `.env` to version control

### Resource Limits

Add to `docker-compose.yml`:

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
```

### Monitoring

```bash
# Resource usage
docker stats

# Container health
docker compose ps

# Disk usage
docker system df
docker volume ls
```

### Backup Strategy

```bash
#!/bin/bash
# backup.sh - Daily backup script

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="./backups"

mkdir -p $BACKUP_DIR

# Backup database
docker compose exec -T db pg_dump -U project2501 project2501 > "$BACKUP_DIR/db_$DATE.sql"

# Backup static files
tar -czf "$BACKUP_DIR/static_$DATE.tar.gz" backend/static

# Keep only last 7 days
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete
```

### Updates

```bash
# Pull latest code
git pull origin main

# Rebuild and restart
docker compose down
docker compose up -d --build

# Check for issues
docker compose logs -f
```

## Development Workflow

### Local Development with Hot Reload

```bash
# Backend with code mounting
docker compose -f docker-compose.yml -f docker-compose.dev.yml up

# Or run backend locally, db in Docker
docker compose up db -d
cd backend
source ~/miniforge3/etc/profile.d/conda.sh
conda activate project2501
python -m uvicorn app.main:app --reload
```

### Running Tests

```bash
# Backend tests
docker compose exec backend pytest -v

# Frontend tests
docker compose exec frontend npm test
```

## Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Reference](https://docs.docker.com/compose/compose-file/)
- [Project 2501 README](README.md)
- [API Documentation](http://localhost:8000/docs)
