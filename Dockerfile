# Optimized build for Python daemon only (no dashboard)
# This is a BACKGROUND WORKER service - does not expose HTTP ports
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

# Expose port for Render Web Service health checks
EXPOSE 10000

# Use start.sh to run both health server and daemon
CMD ["./start.sh"]
