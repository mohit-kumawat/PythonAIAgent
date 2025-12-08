# Optimized build for Python daemon - Render Free Tier Web Service
# Runs health server + daemon for cron-job.org compatibility
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

# Expose port for Render Web Service (required for free tier)
EXPOSE 10000

# Run health server + daemon
CMD ["./start.sh"]
