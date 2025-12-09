#!/bin/bash
set -e

# Get channels from environment variable or use defaults
export SLACK_CHANNELS="${SLACK_CHANNELS:-C07FMAQ3485,C08JF2UFCR1}"

echo "=========================================="
echo "🚀 Starting Python AI Agent (Free Tier)"
echo "=========================================="
echo "Monitoring channels: $SLACK_CHANNELS"
echo "Health endpoint: http://0.0.0.0:${PORT:-10000}/health"
echo "Cron-job.org will ping every 5 minutes to keep alive"
echo "=========================================="

# Set Python to unbuffered mode to see logs in Render
export PYTHONUNBUFFERED=1

# Start health check server (which internally starts the daemon thread)
exec python health_server.py
