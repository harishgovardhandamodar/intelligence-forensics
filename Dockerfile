FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY iforensics/ ./iforensics/
COPY dashboard.py cli.py ./
COPY design/ ./design/
COPY static/ ./static/
# Shipped so the trust-boundary self-audit (T1/T5/T7) sees the same config
# inside the container as on the host. No secrets in either file.
COPY docker-compose.yml README.md ./

RUN mkdir -p /app/evidence /app/reconstructions

ENV PYTHONUNBUFFERED=1 \
    FOX_URL=http://host.docker.internal:8210 \
    OLLAMA_URL=http://host.docker.internal:11434 \
    IF_MODEL=qwen3.8:27b \
    IF_PORT=8211 \
    FOX_SERVICES_DB=/fox-data/fox_services.db

EXPOSE 8211

HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD curl -f http://localhost:8211/health || exit 1

CMD ["uvicorn", "dashboard:app", "--host", "0.0.0.0", "--port", "8211", "--workers", "1"]
