"""
Domain Layer: Core Business Models
Unified models for 3 data sources: TMDb API, IMDb Scraping, PDF Scripts
"""
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Literal, Dict, Any
from datetime import datetime, timezone
from enum import Enum

# ============================================================================
# HELPERS
# ============================================================================

def get_utc_now() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)

# ============================================================================
# ENUMS
# ============================================================================

class DataSource(str, Enum):
    """Enum for data source identification."""
    TMDB = "tmdb"
    IMDB = "imdb"
    SCRIPT = "script"

# ============================================================================
# SENTIMENT
# ============================================================================

class SentimentResult(BaseModel):
    """Result from sentiment analysis microservice."""
    label: str = Field(..., description="POSITIVE, NEGATIVE, or NEUTRAL")
    score: float = Field(..., ge=0.0, le=1.0, description="Confidence score")

# ============================================================================
# MOVIE METADATA
# ============================================================================

class Movie(BaseModel):
    """Universal movie metadata model."""
    movie_id: str = Field(..., description="Unique ID (slug format: 'the-dark-knight-2008')")
    title: str = Field(..., min_length=1)
    director: Optional[str] = None
    year: Optional[int] = Field(None, ge=1800, le=2100)
    genres: List[str] = Field(default_factory=list)
    rating: Optional[float] = Field(None, ge=0.0, le=10.0)
    synopsis: Optional[str] = None
    poster_url: Optional[HttpUrl] = None
    runtime: Optional[int] = Field(None, description="Runtime in minutes")
    created_at: datetime = Field(default_factory=get_utc_now)

    #**Swagger UI** (API Dokümantasyonu) oluşturur
    class Config:
        json_schema_extra = {
            "example": {
                "movie_id": "the-dark-knight-2008",
                "title": "The Dark Knight",
                "director": "Christopher Nolan",
                "year": 2008,
                "genres": ["Action", "Crime", "Drama"],
                "rating": 9.0,
                "synopsis": "When the menace known as the Joker...",
                "poster_url": "https://example.com/poster.jpg",
                "runtime": 152
            }
        }


# ============================================================================
# DATA SOURCES
# ============================================================================

class TMDbReview(BaseModel):
    """User review from TMDb API."""
    review_id: str
    movie_id: str
    author: str
    rating: Optional[float] = Field(None, ge=0.0, le=10.0)
    text: str = Field(..., min_length=1)
    date: Optional[datetime] = None
    source: Literal[DataSource.TMDB] = DataSource.TMDB
    sentiment: Optional[SentimentResult] = None
    created_at: datetime = Field(default_factory=get_utc_now)

class IMDbReview(BaseModel):
    """User review scraped from IMDb."""
    review_id: str
    movie_id: str
    author: str
    rating: Optional[float] = Field(None, ge=0.0, le=10.0)
    text: str = Field(..., min_length=1)
    date: Optional[datetime] = None
    helpful_count: int = Field(default=0, ge=0)
    source: Literal[DataSource.IMDB] = DataSource.IMDB
    sentiment: Optional[SentimentResult] = None
    created_at: datetime = Field(default_factory=get_utc_now)

class ScriptScene(BaseModel):
    """A scene from a movie script (PDF)."""
    scene_id: str
    movie_id: str
    scene_number: int = Field(..., ge=1)
    heading: str
    dialogue: str
    page_number: Optional[int] = None
    source: Literal[DataSource.SCRIPT] = DataSource.SCRIPT
    created_at: datetime = Field(default_factory=get_utc_now)

# ============================================================================
# UNIFIED DOCUMENT (VECTOR STORE)
# ============================================================================

class CinemaDocument(BaseModel):
    """
    Unified document model for ChromaDB.
    Represents one embeddable unit from any source.
    """
    #huni mantığı farklı yapıları tek bir standart pakete çeviren kutudur 3 farklı yerden veri geliyor.


    doc_id: str = Field(..., description="Unique document ID")
    movie: Movie
    content: str = Field(..., description="Text content to embed")
    source: DataSource
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Day 4 için hazırlık: Vektör alanı
    embedding: Optional[List[float]] = Field(None, description="Vector representation")
    
    sentiment: Optional[SentimentResult] = None
    created_at: datetime = Field(default_factory=get_utc_now)
    
    def to_chroma_format(self) -> tuple[str, str, dict, Optional[List[float]]]:
        """Returns: (doc_id, content, metadata, embedding)"""
        meta = {
            "movie_id": self.movie.movie_id,
            "movie_title": self.movie.title,
            "source": self.source.value,
            "created_at": self.created_at.isoformat(),
            **self.metadata
        }
        if self.sentiment:
            meta["sentiment_label"] = self.sentiment.label
            meta["sentiment_score"] = self.sentiment.score
        
        return self.doc_id, self.content, meta, self.embedding

    # --- FACTORY METHODS (TERCÜMANLAR) ---
    #`CinemaDocument` sınıfına diyoruz ki: **"Sen kendini TMDb verisinden nasıl yaratacağını bil."**
    # çünkü cinemadocument farklı
    #Elimizde bir `TMDbReview` objesi var (TMDb dili konuşuyor).
    #Bize `CinemaDocument` objesi lazım (Vektör dili konuşuyor).

    @classmethod
    def from_tmdb_review(cls, movie: Movie, review: TMDbReview) -> "CinemaDocument": #dönüşüm aşaması
        """TMDb yorumunu CinemaDocument formatına çevirir."""
        content = f"Title: {movie.title} ({movie.year})\n"
        content += f"User Review by {review.author}"
        if review.rating:
            content += f" (Rating: {review.rating}/10)"
        content += f"\nReview: {review.text}"
        
        return cls(
            doc_id=f"tmdb-{review.review_id}",
            movie=movie,
            content=content,
            source=DataSource.TMDB,
            metadata={
                "review_id": review.review_id,
                "author": review.author,
                "rating": review.rating,
                "date": review.date.isoformat() if review.date else None
            },
            sentiment=review.sentiment
        )

    @classmethod
    def from_imdb_review(cls, movie: Movie, review: IMDbReview) -> "CinemaDocument":
        """IMDb yorumunu CinemaDocument formatına çevirir."""
        content = f"Title: {movie.title} ({movie.year})\n"
        content += f"IMDb Review by {review.author}"
        if review.rating:
            content += f" (Rating: {review.rating}/10)"
        content += f"\nReview: {review.text}"
        
        return cls(
            doc_id=f"imdb-{review.review_id}",
            movie=movie,
            content=content,
            source=DataSource.IMDB,
            metadata={
                "review_id": review.review_id,
                "author": review.author,
                "rating": review.rating,
                "helpful_count": review.helpful_count,
                "date": review.date.isoformat() if review.date else None
            },
            sentiment=review.sentiment
        )

    @classmethod
    def from_script_scene(cls, movie: Movie, scene: ScriptScene) -> "CinemaDocument":
        """Senaryo sahnesini CinemaDocument formatına çevirir."""
        content = f"Movie: {movie.title} ({movie.year})\n"
        content += f"Scene {scene.scene_number}: {scene.heading}\n"
        content += f"Dialogue:\n{scene.dialogue}"
        
        return cls(
            doc_id=f"script-{scene.scene_id}",
            movie=movie,
            content=content,
            source=DataSource.SCRIPT,
            metadata={
                "scene_id": scene.scene_id,
                "scene_number": scene.scene_number,
                "heading": scene.heading,
                "page_number": scene.page_number
            },
            sentiment=None  # Senaryoda duygu analizi yapmıyoruz (şimdilik)
        )

    class Config:
        use_enum_values = True