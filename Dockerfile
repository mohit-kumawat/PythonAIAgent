# Optimized build for Python daemon only (no dashboard)
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code (excluding files in .dockerignore)
COPY . .

# Make start script executable
RUN chmod +x start.sh

# No port exposure needed for daemon-only mode
# CMD runs the daemon directly
CMD ["python", "daemon.py", "${SLACK_CHANNELS}"]
