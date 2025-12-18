import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "CineMind AI"
    DEBUG: bool = True
    TMDB_API_KEY: str 
    TMDB_BASE_URL: str = "https://api.themoviedb.org/3"

    #sentiment service config
    SENTIMENT_SERVICE_URL: str = "http://localhost:8001"
    #env dosyası okuma aracı
    model_config = SettingsConfigDict(env_file=".env")

@lru_cache()
def get_settings():
    return Settings()
