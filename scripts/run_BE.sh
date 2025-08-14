#!/bin/bash

# run_BE.sh - Backend run script for Project 2501
# This script starts the FastAPI backend server

set -e  # Exit on any error

echo "🚀 Project 2501 Backend Server"
echo "=============================="

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_ROOT/backend"

echo "📁 Project root: $PROJECT_ROOT"
echo "📁 Backend directory: $BACKEND_DIR"

# Check if conda is available
if ! command -v conda &> /dev/null; then
    echo "❌ Error: conda is not installed or not in PATH"
    echo "Please install Miniconda or Anaconda first"
    exit 1
fi

# Source conda
if [ -f "$HOME/miniforge3/etc/profile.d/conda.sh" ]; then
    source "$HOME/miniforge3/etc/profile.d/conda.sh"
elif [ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]; then
    source "$HOME/miniconda3/etc/profile.d/conda.sh"
elif [ -f "$HOME/anaconda3/etc/profile.d/conda.sh" ]; then
    source "$HOME/anaconda3/etc/profile.d/conda.sh"
else
    echo "❌ Error: Could not find conda initialization script"
    echo "Please make sure conda is properly installed"
    exit 1
fi

# Check if environment exists
if ! conda env list | grep -q "project2501"; then
    echo "❌ Error: project2501 conda environment not found"
    echo "Please run the installation script first:"
    echo "   ./scripts/install_BE.sh"
    exit 1
fi

# Activate environment
echo "🔧 Activating conda environment..."
conda activate project2501

# Change to backend directory
cd "$BACKEND_DIR"

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found"
    echo "Please copy .env.example to .env and configure your database settings:"
    echo "   cp .env.example .env"
    echo ""
    read -p "Do you want to continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Exiting..."
        exit 1
    fi
fi

# Parse command line arguments
HOST="0.0.0.0"
PORT="8000"
RELOAD="--reload"

while [[ $# -gt 0 ]]; do
    case $1 in
        --host)
            HOST="$2"
            shift 2
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --no-reload)
            RELOAD=""
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --host HOST       Bind socket to this host (default: 0.0.0.0)"
            echo "  --port PORT       Bind socket to this port (default: 8000)"
            echo "  --no-reload       Disable auto-reload on code changes"
            echo "  --help, -h        Show this help message"
            echo ""
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo "🔧 Configuration:"
echo "   Host: $HOST"
echo "   Port: $PORT"
echo "   Auto-reload: $([ -n "$RELOAD" ] && echo "enabled" || echo "disabled")"
echo ""

echo "🌐 Starting FastAPI server..."
echo "   Backend API will be available at: http://$HOST:$PORT"
echo "   API documentation at: http://$HOST:$PORT/docs"
echo "   Database test endpoint: http://$HOST:$PORT/api/database/test"
echo ""
echo "📝 Press Ctrl+C to stop the server"
echo ""

# Start the server
python -m uvicorn app.main:app --host "$HOST" --port "$PORT" $RELOAD