# Multi-stage build for faster deployments
FROM python:3.11-slim as base

# Install system dependencies in one layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gnupg \
    build-essential \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

WORKDIR /app

# Stage 1: Install Python dependencies
FROM base as python-deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Build Dashboard
FROM base as dashboard-builder
COPY dashboard/package.json dashboard/package-lock.json ./dashboard/
WORKDIR /app/dashboard
RUN npm ci --only=production
COPY dashboard/ .
RUN npm run build

# Final stage: Combine everything
FROM base as final
WORKDIR /app

# Copy Python dependencies from stage 1
COPY --from=python-deps /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=python-deps /usr/local/bin /usr/local/bin

# Copy built dashboard from stage 2
COPY --from=dashboard-builder /app/dashboard/.next ./dashboard/.next
COPY --from=dashboard-builder /app/dashboard/node_modules ./dashboard/node_modules
COPY --from=dashboard-builder /app/dashboard/package.json ./dashboard/

# Copy application code (excluding files in .dockerignore)
COPY . .

# Make start script executable
RUN chmod +x start.sh

EXPOSE 3000

CMD ["./start.sh"]
