FROM python:3.11-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends bash curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY mirrorer/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY mirrorer /app
COPY backend/app/core/secrets.py /app/service_secrets.py
COPY vendor/EmergencyStorage /vendor/EmergencyStorage

# Windows checkouts may give the vendored Bash scripts CRLF line endings.
RUN sed -i 's/\r$//' /vendor/EmergencyStorage/emergency_storage.sh /vendor/EmergencyStorage/scripts/*.sh \
    && chmod +x /vendor/EmergencyStorage/emergency_storage.sh \
    && chmod +x /vendor/EmergencyStorage/scripts/*.sh

ENV PYTHONUNBUFFERED=1
ENV MIRROR_ROOT=/mnt/babylonpiles/piles
ENV MIRROR_LOG_DIR=/mnt/babylonpiles/data/mirror_logs
ENV EMERGENCY_STORAGE_ROOT=/vendor/EmergencyStorage

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8002"]
