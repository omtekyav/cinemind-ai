"""
API Schemas (Pydantic Models)
Contract-First Design: API'nin input/output sözleşmeleri.
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum
from datetime import datetime, timezone


# =============================================================================
# ENUMS
# =============================================================================

class SourceTypeEnum(str, Enum):
    """API'de kullanılacak kaynak tipleri."""
    TMDB = "tmdb"
    IMDB = "imdb"
    SCRIPT = "script"


class IngestSourceEnum(str, Enum):
    """Ingestion için kaynak seçenekleri."""
    TMDB = "tmdb"
    IMDB = "imdb"
    SCRIPT = "script"
    ALL = "all"


# =============================================================================
# NESTED MODELS (Response içinde kullanılan)
# =============================================================================

class SourceDocument(BaseModel):
    """RAG cevabındaki tek bir kaynak doküman."""
    content: str = Field(..., description="Doküman içeriği")
    source: SourceTypeEnum = Field(..., description="Kaynak tipi")
    movie_title: str = Field(..., description="Film adı")
    distance: float = Field(..., ge=0, le=2, description="Vektör uzaklığı (0=identical)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "content": "Joker, Gotham'ın ruhunu test etmek istiyor...",
                "source": "script",
                "movie_title": "The Dark Knight",
                "distance": 0.234
            }
        }


class TokenUsage(BaseModel):
    """Token kullanım detayları."""
    input_tokens: int = Field(0, description="Giriş token sayısı")
    output_tokens: int = Field(0, description="Çıkış token sayısı")
    total_tokens: int = Field(0, description="Toplam token sayısı")


# =============================================================================
# QUERY (RAG Sorgusu)
# =============================================================================

class QueryRequest(BaseModel):
    """RAG sorgusu için input."""
    question: str = Field(
        ..., 
        min_length=3, 
        max_length=500,
        description="Kullanıcının sorusu"
    )
    source_filter: Optional[SourceTypeEnum] = Field(
        None, 
        description="Belirli kaynaktan ara (boş=tümü)"
    )
    limit: int = Field(
        default=10, 
        ge=1, 
        le=50,
        description="Maksimum kaynak sayısı"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "question": "The Dark Knight filminde Joker'in planı neydi?",
                "source_filter": None,
                "limit": 10
            }
        }


class QueryResponse(BaseModel):
    """RAG sorgusu için output."""
    answer: str = Field(..., description="LLM tarafından üretilen cevap")
    sources: List[SourceDocument] = Field(
        default_factory=list,
        description="Cevabın dayandığı kaynaklar"
    )
    query: str = Field(..., description="Orijinal soru")
    source_count: int = Field(..., description="Kullanılan kaynak sayısı")
    token_usage: Optional[TokenUsage] = Field(
        default=None,
        description="Token kullanım detayları"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "answer": "Senaryoya göre, Joker'in planı...",
                "sources": [],
                "query": "The Dark Knight filminde Joker'in planı neydi?",
                "source_count": 5,
                "token_usage": {
                    "input_tokens": 1200,
                    "output_tokens": 350,
                    "total_tokens": 1550
                }
            }
        }


# =============================================================================
# INGEST (Veri Yükleme)
# =============================================================================

class IngestRequest(BaseModel):
    """Ingestion tetikleme için input."""
    source: IngestSourceEnum = Field(
        ..., 
        description="Hangi kaynaktan veri çekilecek"
    )
    limit: int = Field(
        default=5, 
        ge=1, 
        le=50,
        description="Kaç film/doküman işlenecek"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "source": "tmdb",
                "limit": 5
            }
        }


class IngestResponse(BaseModel):
    """Ingestion sonucu için output."""
    status: str = Field(..., description="İşlem durumu")
    source: str = Field(..., description="İşlenen kaynak")
    message: str = Field(..., description="Detay mesajı")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="İşlem zamanı"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "source": "tmdb",
                "message": "5 film başarıyla işlendi",
                "timestamp": "2025-01-15T10:30:00Z"
            }
        }


# =============================================================================
# MOVIE (Film Detayları)
# =============================================================================

class MovieResponse(BaseModel):
    """Film detayları için output."""
    movie_id: str = Field(..., description="Film ID (slug)")
    title: str = Field(..., description="Film adı")
    year: Optional[int] = Field(None, description="Yapım yılı")
    director: Optional[str] = Field(None, description="Yönetmen")
    genres: List[str] = Field(default_factory=list, description="Türler")
    rating: Optional[float] = Field(None, ge=0, le=10, description="Puan")
    synopsis: Optional[str] = Field(None, description="Özet")
    source_count: int = Field(
        default=0, 
        description="Bu filme ait kaynak sayısı"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "movie_id": "the-dark-knight-2008",
                "title": "The Dark Knight",
                "year": 2008,
                "director": "Christopher Nolan",
                "genres": ["Action", "Crime", "Drama"],
                "rating": 9.0,
                "synopsis": "When the menace known as the Joker...",
                "source_count": 25
            }
        }


# =============================================================================
# HEALTH (Sistem Sağlığı)
# =============================================================================

class HealthResponse(BaseModel):
    """Sistem sağlık kontrolü için output."""
    status: str = Field(..., description="Genel durum")
    version: str = Field(default="1.0.0", description="API versiyonu")
    services: dict = Field(
        default_factory=dict, 
        description="Alt servis durumları"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "services": {
                    "vector_store": "ok",
                    "embedding": "ok",
                    "llm": "ok"
                }
            }
        }


# =============================================================================
# ERROR (Hata Formatı)
# =============================================================================

class ErrorResponse(BaseModel):
    """Standart hata formatı."""
    error: str = Field(..., description="Hata tipi")
    message: str = Field(..., description="Hata mesajı")
    detail: Optional[str] = Field(None, description="Ek detay")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "ValidationError",
                "message": "Geçersiz istek formatı",
                "detail": "question alanı zorunludur"
            }
        }