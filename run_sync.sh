#!/bin/bash

# Navigate to the directory where this script resides
cd "$(dirname "$0")"

# Activate the virtual environment
# If your virtual environment is named differently, update the path below.
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
else
    echo "Error: Virtual environment not found at .venv/bin/activate"
    exit 1
fi

# Execute the sync command
# REPLACE 'YOUR_SLACK_CHANNEL_ID_HERE' with your actual Slack Channel ID
python main.py sync --channels C08JF2UFCR1 C07FMAQ3485 --todo-sync
