# =============================================================================
# CineMind UI Dockerfile (Streamlit)
# Lightweight frontend container
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Base
# -----------------------------------------------------------------------------
FROM python:3.11-slim as base

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# -----------------------------------------------------------------------------
# Stage 2: Production
# -----------------------------------------------------------------------------
FROM base as production

# Sadece Streamlit ve gerekli minimal bağımlılıklar
RUN pip install --no-cache-dir \
    streamlit==1.45.0 \
    httpx==0.28.1 \
    pydantic==2.11.4

# UI kodlarını kopyala
COPY app.py .
COPY api_client.py .

# Streamlit config (opsiyonel - headless mode için)
RUN mkdir -p /root/.streamlit
RUN echo '[server]\nheadless = true\naddress = "0.0.0.0"\nport = 8502\n\n[browser]\ngatherUsageStats = false' > /root/.streamlit/config.toml

# Port
EXPOSE 8502

# Healthcheck (stdlib ile)
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8502/_stcore/health', timeout=5)" || exit 1

# Başlat
CMD ["streamlit", "run", "app.py", "--server.port=8502", "--server.address=0.0.0.0"]