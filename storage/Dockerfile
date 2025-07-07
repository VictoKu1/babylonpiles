FROM python:3.11-slim

# Install only essential system dependencies
RUN apt-get update && apt-get install -y \
    rsync \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies with optimizations
RUN pip install --no-cache-dir --no-deps -r requirements.txt

# Copy application code
COPY . .

# Configure storage paths directly in Dockerfile
# Change these paths to your desired storage locations
ENV PRIMARY_STORAGE_PATH=/mnt/hdd1
ENV PILES_STORAGE_PATH=/mnt/babylonpiles/piles

# Create directories in one RUN command
RUN mkdir -p /mnt/hdd1 /app/data/chunks /app/data/metadata /app/data/logs

EXPOSE 8001

# Simplified health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=2 \
    CMD python -c "import requests; requests.get('http://localhost:8001/health', timeout=5)" || exit 1

CMD ["python", "storage_service.py"] 