from fastapi import FastAPI
from src.infrastructure.config import get_settings

settings = get_settings()
app = FastAPI(title="CineMind AI", debug=settings.DEBUG)

@app.get("/health")
async def health_check():
    return {"status": "active", "app": settings.APP_NAME}
