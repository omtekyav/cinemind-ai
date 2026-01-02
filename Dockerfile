# =============================================================================
# CineMind API Dockerfile
# Multi-stage build ile optimize edilmiş image
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Base image
# -----------------------------------------------------------------------------
FROM python:3.11-slim as base

# Çalışma dizini
WORKDIR /app

# Python optimizasyonları
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# -----------------------------------------------------------------------------
# Stage 2: Dependencies
# -----------------------------------------------------------------------------
FROM base as dependencies

# Sistem bağımlılıkları (build için gerekli)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Requirements dosyasını kopyala
COPY requirements.txt .

# Python bağımlılıklarını yükle
RUN pip install --no-cache-dir -r requirements.txt

# -----------------------------------------------------------------------------
# Stage 3: Production
# -----------------------------------------------------------------------------
FROM base as production

# Dependencies stage'den yüklü paketleri kopyala
COPY --from=dependencies /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=dependencies /usr/local/bin /usr/local/bin

# Uygulama kodunu kopyala
COPY src/ ./src/

# .env.docker dosyasını container içine .env olarak kopyala
COPY .env.docker ./.env

# Data klasörünü oluştur (volume mount edilecek)
RUN mkdir -p /app/data/vector_store /app/data/scripts /app/logs

# Port
EXPOSE 8000

# Healthcheck (stdlib - harici bağımlılık yok)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health', timeout=5)" || exit 1

# Başlat
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]