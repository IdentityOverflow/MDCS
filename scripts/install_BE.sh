#!/bin/bash

# install_BE.sh - Backend installation script for Project 2501
# This script sets up the conda environment and installs dependencies

set -e  # Exit on any error

echo "🔧 Project 2501 Backend Installation Script"
echo "==========================================="

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

echo "✅ Conda found"

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

echo "🔧 Sourced conda initialization"

# Check if environment already exists
if conda env list | grep -q "project2501"; then
    echo "🔄 project2501 environment already exists"
    read -p "Do you want to recreate it? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🗑️  Removing existing environment..."
        conda env remove -n project2501 -y
    else
        echo "ℹ️  Using existing environment"
        conda activate project2501
        echo "📦 Updating dependencies..."
        cd "$BACKEND_DIR"
        pip install -r requirements.txt
        echo "✅ Backend installation completed!"
        exit 0
    fi
fi

# Create conda environment
echo "🔨 Creating conda environment 'project2501'..."
conda create -n project2501 python=3.10 -y

# Activate environment
echo "🔧 Activating environment..."
conda activate project2501

# Install dependencies
echo "📦 Installing Python dependencies..."
cd "$BACKEND_DIR"

if [ ! -f "requirements.txt" ]; then
    echo "❌ Error: requirements.txt not found in $BACKEND_DIR"
    exit 1
fi

pip install -r requirements.txt

echo ""
echo "✅ Backend installation completed successfully!"
echo ""
echo "🚀 Next steps:"
echo "   1. Copy .env.example to .env and configure your database settings:"
echo "      cp $BACKEND_DIR/.env.example $BACKEND_DIR/.env"
echo "   2. Edit the .env file with your database credentials"
echo "   3. Run the backend server:"
echo "      ./scripts/run_BE.sh"
echo ""