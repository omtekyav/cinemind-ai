"""
CineMind AI - FastAPI Application
Ana uygulama giriş noktası.
"""
from fastapi import FastAPI
from src.infrastructure.config import get_settings
from src.api.routes import router

settings = get_settings()

app = FastAPI(
    title="CineMind AI",
    description="Sinema Analiz Asistanı - RAG Tabanlı API",
    version="1.0.0",
    debug=settings.DEBUG
)

# API Router'ı bağla
app.include_router(router)


# Root endpoint (basit health check)
@app.get("/", tags=["Root"])
async def root():
    """API kök endpoint'i."""
    return {
        "app": settings.APP_NAME,
        "version": "1.0.0",
        "docs": "/docs"
    }