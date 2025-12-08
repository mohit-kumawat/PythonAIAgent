#!/bin/bash
set -e

# Start the Python Daemon in the background
# We assume env vars for Channel IDs are set or defaults are used
# Usage: python daemon.py <CHANNEL_ID_1> <CHANNEL_ID_2> ...
# If env vars are provided (RECOMMENDED), we use them.
# Otherwise, we fallback to hardcoded ones (NOT RECOMMENDED for prod)

DAEMON_CHANNELS="${SLACK_CHANNELS:-C07FMAQ3485 C08JF2UFCR1}"

echo "Starting Python Daemon for channels: $DAEMON_CHANNELS"
python daemon.py $DAEMON_CHANNELS &

# Start the Next.js Dashboard
echo "Starting Next.js Dashboard..."
cd dashboard
npm start
