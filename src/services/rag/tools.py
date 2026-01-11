"""
Agent Tools
Mevcut servisleri (Retriever, TMDb) LLM'in kullanabileceği 'Tool'lara dönüştürür.
"""
import logging
from typing import Optional
from langchain_core.tools import tool

# Servisleri import et
from src.infrastructure.vector_store import VectorStoreService
from src.domain.embeddings import EmbeddingService
from src.services.rag.retriever import Retriever
from src.services.rag.dtos import SourceType
from src.services.tmdb_service import tmdb_service

logger = logging.getLogger(__name__)

# --- BAĞIMLILIKLARI HAZIRLA ---
_retriever = None

def _get_retriever():
    """Lazy initialization for retriever."""
    global _retriever
    if _retriever is None:
        embedding_service = EmbeddingService()
        vector_store = VectorStoreService()
        _retriever = Retriever(embedding_service, vector_store)
    return _retriever


# --- TOOL 1: VEKTÖR ARAMA ---
@tool
def search_vector_db(query: str, source: Optional[str] = None) -> str:
    """
    Sinema veritabanında (Senaryolar, IMDb yorumları, TMDb incelemeleri) semantik arama yapar.
    
    Kullanım Senaryoları:
    - Bir filmin senaryosundaki detaylar (diyaloglar, sahneler).
    - İzleyici yorumları ve duyguları.
    - Filmin konusu hakkındaki derinlemesine analizler.
    
    Args:
        query: Aranacak soru veya anahtar kelimeler.
        source: Kaynak filtresi ('script', 'imdb', 'tmdb'). Boş bırakılırsa tümünde arar.
    """
    retriever = _get_retriever()
    
    # Enum dönüşümü
    source_enum = None
    if source:
        try:
            source_enum = SourceType(source.lower())
        except ValueError:
            pass  # Geçersiz source gelirse filtresiz ara

    results = retriever.retrieve(query, limit=5, source_filter=source_enum)
    
    if not results:
        return "Veritabanında ilgili kayıt bulunamadı."

    # Sonuçları LLM'in okuyabileceği metne dönüştür
    formatted_results = []
    for doc in results:
        formatted_results.append(
            f"Kaynak: {doc.source.value.upper()} | Film: {doc.movie_title}\n"
            f"İçerik: {doc.content[:500]}\n---"
        )
    
    return "\n".join(formatted_results)


# --- TOOL 2: TMDB API ARAMA ---
@tool
async def search_tmdb_metadata(query: str) -> str:
    """
    TMDb üzerinden güncel film bilgilerini (Yönetmen, Oyuncular, Yıl, Puan) getirir.
    Senaryo veya yorum analizi İÇERMEZ. Sadece künye bilgileri içindir.
    
    Args:
        query: Film adı (örn: "Inception", "The Dark Knight").
    """
    # 1. Filmi Ara (ID bul)
    movie_id = await tmdb_service.search_movie(query)
    if not movie_id:
        return f"'{query}' adında bir film bulunamadı."
    
    # 2. Detayları Çek
    movie = await tmdb_service.get_movie(movie_id)
    if not movie:
        return "Film detayları çekilemedi."
    
    # 3. Metne Dönüştür
    return (
        f"Film: {movie.title} ({movie.year})\n"
        f"Yönetmen: {movie.director}\n"
        f"Türler: {', '.join(movie.genres)}\n"
        f"Puan: {movie.rating}/10\n"
        f"Özet: {movie.synopsis}"
    )


# Ajanın kullanacağı tool listesi
ALL_TOOLS = [search_vector_db, search_tmdb_metadata]