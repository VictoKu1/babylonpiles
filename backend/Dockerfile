FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install only essential system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies with optimizations
RUN pip install --no-cache-dir --no-deps -r requirements.txt

# Copy application code
COPY . .

# Configure storage paths directly in Dockerfile
# Change these paths to your desired storage locations
ENV DATA_DIR=/mnt/babylonpiles/data
ENV PILES_DIR=/mnt/babylonpiles/piles
ENV STORAGE_URL=http://storage:8001

# Create necessary directories in one RUN command
RUN mkdir -p /mnt/babylonpiles/data /mnt/babylonpiles/piles /tmp/babylonpiles

# Expose port
EXPOSE 8080

# Simplified health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=15s --retries=2 \
    CMD curl -f --max-time 10 http://localhost:8080/health || exit 1

# Run the application
CMD ["python", "main.py"] 