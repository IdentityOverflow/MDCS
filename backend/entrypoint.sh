#!/bin/bash
# ============================================
# Project 2501 Backend Entrypoint Script
# Handles database initialization and startup
# ============================================

set -e

echo "=== Project 2501 Backend Starting ==="

# Database connection parameters from environment
DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-project2501}"
DB_USER="${DB_USER:-project2501}"

echo "Waiting for PostgreSQL at $DB_HOST:$DB_PORT..."

# Wait for PostgreSQL to be ready
max_retries=30
retry_count=0

until pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" > /dev/null 2>&1; do
    retry_count=$((retry_count + 1))
    if [ $retry_count -ge $max_retries ]; then
        echo "ERROR: PostgreSQL did not become ready after $max_retries attempts"
        exit 1
    fi
    echo "PostgreSQL is unavailable - attempt $retry_count/$max_retries - sleeping..."
    sleep 2
done

echo "✓ PostgreSQL is ready!"

# Check if database is initialized (check for personas table)
echo "Checking if database is initialized..."
TABLE_EXISTS=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -tAc \
    "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='personas');")

if [ "$TABLE_EXISTS" = "f" ]; then
    echo "Database not initialized. Running initialization script..."
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f /app/init_db.sql
    echo "✓ Database initialized successfully"
else
    echo "✓ Database already initialized"
fi

echo "=== Starting FastAPI Application ==="

# Execute the main command (passed as arguments to this script)
exec "$@"
