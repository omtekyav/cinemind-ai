"""
API Routes
FastAPI endpoint tanımları.
Single Responsibility: Her endpoint tek bir iş yapar.
"""
import logging
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import Optional

from src.api.schemas import (
    QueryRequest, QueryResponse, SourceDocument, TokenUsage,
    IngestRequest, IngestResponse,
    MovieResponse,
    HealthResponse,
    ErrorResponse,
    SourceTypeEnum
)
# ESKİ: RAGPipeline importunu kaldırdık
# YENİ: LangGraph ajanını import ediyoruz
from src.services.rag.graph import query_agent
from src.infrastructure.vector_store import VectorStoreService

logger = logging.getLogger(__name__)

# =============================================================================
# ROUTER INSTANCE
# =============================================================================

router = APIRouter(prefix="/api/v1", tags=["CineMind API"])


# =============================================================================
# DEPENDENCY INJECTION
# =============================================================================

# NOT: get_rag_pipeline artık kullanılmadığı için kaldırıldı.

def get_vector_store() -> VectorStoreService:
    """Vector Store singleton."""
    if not hasattr(get_vector_store, "_instance"):
        get_vector_store._instance = VectorStoreService()
    return get_vector_store._instance


# =============================================================================
# QUERY ENDPOINT (GÜNCELLENDİ 🚀)
# =============================================================================

@router.post(
    "/query",
    response_model=QueryResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Geçersiz istek"},
        500: {"model": ErrorResponse, "description": "Sunucu hatası"}
    },
    summary="Agentic RAG Sorgusu",
    description="LangGraph agent ile sinema veritabanında arama yapar ve cevap üretir."
)
async def query(request: QueryRequest) -> QueryResponse:
    """
    Agentic RAG Query Endpoint.
    
    Flow:
    1. Kullanıcı sorusu alınır
    2. LangGraph agent çağrılır (Tools: TMDb, VectorDB)
    3. Agent düşünür, araçları kullanır ve cevap üretir
    """
    logger.info(f"📨 Query request: {request.question[:50]}...")
    
    try:
        # Agentic RAG - LangGraph Çağrısı
        # query_agent fonksiyonu graph'ı derler, çalıştırır ve son cevabı döner
        answer = query_agent(request.question)
        
        # Response Mapping
        # Not: Şimdilik 'sources' boş dönüyor çünkü Agent'tan kaynakları ayrıştırmak
        # ekstra işlem gerektirir (metadata parsing). MVP için bu yeterli.
        return QueryResponse(
            answer=answer,
            sources=[], 
            query=request.question,
            source_count=0,
            token_usage=None
        )
        
    except Exception as e:
        logger.error(f"❌ Query hatası: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Sorgu işlenirken hata oluştu: {str(e)}"
        )


# =============================================================================
# INGEST ENDPOINT (DEĞİŞMEDİ)
# =============================================================================

@router.post(
    "/ingest",
    response_model=IngestResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Geçersiz kaynak"},
        500: {"model": ErrorResponse, "description": "Ingestion hatası"}
    },
    summary="Veri Yükleme",
    description="Belirtilen kaynaktan veri çeker ve veritabanına yükler."
)
async def ingest(
    request: IngestRequest,
    background_tasks: BackgroundTasks
) -> IngestResponse:
    """
    Ingestion Endpoint.
    """
    logger.info(f"📥 Ingest request: {request.source.value}, limit={request.limit}")
    
    # Background task olarak çalıştır
    background_tasks.add_task(
        _run_ingestion,
        source=request.source.value,
        limit=request.limit
    )
    
    return IngestResponse(
        status="accepted",
        source=request.source.value,
        message=f"Ingestion başlatıldı: {request.limit} öğe işlenecek"
    )


async def _run_ingestion(source: str, limit: int):
    """Background ingestion task."""
    # Lazy import to avoid circular dependencies
    from src.services.ingestion_coordinator import IngestionCoordinator
    
    logger.info(f"🔄 Background ingestion başladı: {source}")
    
    try:
        coordinator = IngestionCoordinator()
        
        if source == "tmdb":
            await coordinator.run_tmdb_batch(limit=limit)
        elif source == "imdb":
            await coordinator.run_imdb_pipeline(limit=limit)
        elif source == "script":
            await coordinator.run_script_pipeline()
        elif source == "all":
            await coordinator.run_tmdb_batch(limit=limit)
            await coordinator.run_imdb_pipeline(limit=limit)
            await coordinator.run_script_pipeline()
        
        coordinator.close()
        logger.info(f"✅ Background ingestion tamamlandı: {source}")
        
    except Exception as e:
        logger.error(f"❌ Background ingestion hatası: {e}")


# =============================================================================
# MOVIE ENDPOINT (DEĞİŞMEDİ)
# =============================================================================

@router.get(
    "/movies/{movie_id}",
    response_model=MovieResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Film bulunamadı"}
    },
    summary="Film Detayları",
    description="Belirtilen ID'ye sahip filmin detaylarını getirir."
)
async def get_movie(
    movie_id: str,
    vector_store: VectorStoreService = Depends(get_vector_store)
) -> MovieResponse:
    """
    Movie Detail Endpoint.
    """
    logger.info(f"🎬 Movie request: {movie_id}")
    
    results = vector_store.collection.get(
        where={"movie_id": movie_id},
        limit=1
    )
    
    if not results or not results.get("metadatas"):
        raise HTTPException(
            status_code=404,
            detail=f"Film bulunamadı: {movie_id}"
        )
    
    metadata = results["metadatas"][0]
    
    all_docs = vector_store.collection.get(
        where={"movie_id": movie_id}
    )
    source_count = len(all_docs.get("ids", []))
    
    return MovieResponse(
        movie_id=movie_id,
        title=metadata.get("movie_title", "Unknown"),
        year=metadata.get("year"),
        director=metadata.get("director"),
        genres=metadata.get("genres", "").split(",") if metadata.get("genres") else [],
        rating=metadata.get("rating"),
        synopsis=metadata.get("synopsis"),
        source_count=source_count
    )


# =============================================================================
# HEALTH ENDPOINT (DEĞİŞMEDİ)
# =============================================================================

@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Sistem Sağlığı",
    description="API ve alt servislerin durumunu kontrol eder."
)
async def health_check(
    vector_store: VectorStoreService = Depends(get_vector_store)
) -> HealthResponse:
    """
    Health Check Endpoint.
    """
    services = {}
    
    try:
        count = vector_store.count()
        services["vector_store"] = f"ok ({count} documents)"
    except Exception as e:
        services["vector_store"] = f"error: {str(e)}"
    
    try:
        from src.domain.embeddings import EmbeddingService
        emb = EmbeddingService()
        services["embedding"] = "ok"
    except Exception as e:
        services["embedding"] = f"error: {str(e)}"
    
    try:
        from src.infrastructure.config import get_settings
        settings = get_settings()
        if settings.GOOGLE_API_KEY:
            services["llm"] = "ok (configured)"
        else:
            services["llm"] = "error: API key missing"
    except Exception as e:
        services["llm"] = f"error: {str(e)}"
    
    all_ok = all("ok" in str(v) for v in services.values())
    status = "healthy" if all_ok else "degraded"
    
    return HealthResponse(
        status=status,
        version="1.0.0",
        services=services
    )