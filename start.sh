#!/bin/bash
set -e

# Get channels from environment variable or use defaults
DAEMON_CHANNELS="${SLACK_CHANNELS:-C07FMAQ3485 C08JF2UFCR1}"

echo "Starting Python Daemon in background for channels: $DAEMON_CHANNELS"
python daemon.py $DAEMON_CHANNELS &

echo "Starting Health Check Server on port ${PORT:-10000}"
exec python health_server.py
