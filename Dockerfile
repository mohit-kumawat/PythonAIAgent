# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Install system dependencies
# We need curl to install Node.js, and build-essential for compiling native modules (like better-sqlite3)
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js (LTS version)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs

# Set the working directory
WORKDIR /app

# 1. Install Python Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2. Install Dashboard Dependencies
# We copy just the package files first to leverage Docker cache
COPY dashboard/package.json dashboard/package-lock.json ./dashboard/
WORKDIR /app/dashboard
RUN npm install

# 3. Copy the rest of the application
WORKDIR /app
COPY . .

# 4. Build the Dashboard
WORKDIR /app/dashboard
RUN npm run build

# 5. Setup the start script
WORKDIR /app
COPY start.sh .
RUN chmod +x start.sh

# Expose the port the app runs on (Next.js defaults to 3000)
EXPOSE 3000

# Run the start script
CMD ["./start.sh"]
