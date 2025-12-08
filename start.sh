#!/bin/bash
set -e

# Get channels from environment variable or use defaults
DAEMON_CHANNELS="${SLACK_CHANNELS:-C07FMAQ3485 C08JF2UFCR1}"

echo "Starting Python Daemon for channels: $DAEMON_CHANNELS"
exec python daemon.py $DAEMON_CHANNELS
