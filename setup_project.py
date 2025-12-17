import os
from pathlib import Path

# --- PROJE İSMİ ---
PROJECT_NAME = "cinemind-ai"

# Klasör Yapısı
DIRECTORIES = [
    "src",
    "src/api",
    "src/services",
    "src/domain",
    "src/infrastructure",
    "src/scripts",
    "tests/unit",
    "tests/integration",
    "data/raw/scripts",
    "data/processed",
    "logs",
]

# Dosyalar ve İçerikleri
FILES = {
    # .gitignore ÇOK ÖNEMLİ (Sanal ortamı ve gizli dosyaları gizler)
    ".gitignore": """venv/
__pycache__/
.env
.DS_Store
data/
logs/
*.pyc
""",
    # Environment Variables
    ".env": """TMDB_API_KEY=buraya_api_key_yapistir
DEBUG=True
SENTIMENT_SERVICE_URL=http://localhost:8001
""",
    # Gerekli Kütüphaneler
    "requirements.txt": """fastapi
uvicorn
httpx
pydantic-settings
python-dotenv
beautifulsoup4
pytest
pytest-asyncio
""",
    "README.md": f"# {PROJECT_NAME}\n\nMulti-Source Cinema RAG Platform\n",
    
    # Python Paket Dosyaları
    "src/__init__.py": "",
    "src/api/__init__.py": "",
    "src/services/__init__.py": "",
    "src/domain/__init__.py": "",
    "src/infrastructure/__init__.py": "",
    "src/scripts/__init__.py": "",
    "tests/__init__.py": "",

    # Ana Uygulama
    "src/main.py": """from fastapi import FastAPI
from src.infrastructure.config import get_settings

settings = get_settings()
app = FastAPI(title="CineMind AI", debug=settings.DEBUG)

@app.get("/health")
async def health_check():
    return {"status": "active", "app": settings.APP_NAME}
""",

    # Config Dosyası
    "src/infrastructure/config.py": """import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "CineMind AI"
    DEBUG: bool = True
    TMDB_API_KEY: str
    TMDB_BASE_URL: str = "https://api.themoviedb.org/3"
    SENTIMENT_SERVICE_URL: str = "http://localhost:8001"

    model_config = SettingsConfigDict(env_file=".env")

@lru_cache()
def get_settings():
    return Settings()
""",
    
    # Taslak Kod Dosyaları
    "src/domain/models.py": "# Domain Entities\n",
    "src/services/tmdb_service.py": "# TMDb Logic\n",
    "src/services/imdb_scraper_service.py": "# IMDb Logic\n",
    "src/services/pdf_parser_service.py": "# PDF Logic\n",
    "src/services/ingestion_coordinator.py": "# Coordinator Logic\n",
    "src/services/sentiment_client.py": "# Sentiment Client\n",
}

def create_structure():
    base_path = Path.cwd()
    print(f"🚀 Kurulum Başlıyor: {base_path}")

    for directory in DIRECTORIES:
        dir_path = base_path / directory
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"✅ Klasör: {directory}")

    for file_path_str, content in FILES.items():
        file_path = base_path / file_path_str
        if not file_path.exists():
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"📄 Dosya: {file_path_str}")

    print("\n✨ İSKELET HAZIR! ✨")

if __name__ == "__main__":
    create_structure()