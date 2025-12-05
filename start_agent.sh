#!/bin/bash

# Interactive PM Agent Startup Script
# Just run this and tell the agent what you want!

cd "$(dirname "$0")"

# Activate virtual environment
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
else
    echo "❌ Error: Virtual environment not found at .venv/bin/activate"
    exit 1
fi

# Run the interactive agent
python agent.py
