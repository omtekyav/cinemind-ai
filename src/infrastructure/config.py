import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    APP_NAME: str = "CineMind AI"
    DEBUG: bool = True
    
    # TMDb
    TMDB_API_KEY: str 
    TMDB_BASE_URL: str = "https://api.themoviedb.org/3"

    # Sentiment Service
    SENTIMENT_SERVICE_URL: str = "http://localhost:8001"
    
    # Google Gemini (Embedding) - EKLENDİ ✅
    GOOGLE_API_KEY: Optional[str] = None

    # .env dosyasındaki ekstra değişkenlere izin ver (extra='ignore')
    # veya sadece tanımladıklarımızı oku.
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"  # Tanımlanmamış değişkenler varsa hata verme, görmezden gel
    )

@lru_cache()
def get_settings():
    return Settings()