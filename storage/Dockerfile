FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    rsync \
    hdparm \
    smartmontools \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for better caching
COPY storage/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY storage/storage_service.py /app/storage_service.py
COPY backend/app/core/secrets.py /app/service_secrets.py

# Create directory for HDD mount (only hdd1 by default)
RUN mkdir -p /mnt/hdd1

# Create data directories
RUN mkdir -p /app/data/chunks /app/data/metadata /app/data/logs /run/babylonpiles/secrets

EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/health', timeout=5)" || exit 1

CMD ["python", "storage_service.py"]
