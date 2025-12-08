#!/bin/bash
set -e

# Get channels from environment variable or use defaults
DAEMON_CHANNELS="${SLACK_CHANNELS:-C07FMAQ3485 C08JF2UFCR1}"

echo "=========================================="
echo "🚀 Starting Python AI Agent (Free Tier)"
echo "=========================================="
echo "Monitoring channels: $DAEMON_CHANNELS"
echo "Health endpoint: http://0.0.0.0:${PORT:-10000}/health"
echo "Cron-job.org will ping every 5 minutes to keep alive"
echo "=========================================="

# Start daemon in background
python daemon.py $DAEMON_CHANNELS &

# Start health check server in foreground (required for Render free tier)
exec python health_server.py
