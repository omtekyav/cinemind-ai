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
from src.services.rag import RAGPipeline, SourceType
from src.infrastructure.vector_store import VectorStoreService

logger = logging.getLogger(__name__)

# =============================================================================
# ROUTER INSTANCE
# =============================================================================

router = APIRouter(prefix="/api/v1", tags=["CineMind API"])


# =============================================================================
# DEPENDENCY INJECTION
# =============================================================================

def get_rag_pipeline() -> RAGPipeline:
    """
    RAG Pipeline singleton.
    
    Neden singleton?
    - Her request'te yeni pipeline oluşturmak pahalı (model yükleme)
    - Bellek verimliliği
    - Connection pooling
    """
    if not hasattr(get_rag_pipeline, "_instance"):
        logger.info("🚀 RAG Pipeline oluşturuluyor (singleton)")
        get_rag_pipeline._instance = RAGPipeline()
    return get_rag_pipeline._instance


def get_vector_store() -> VectorStoreService:
    """Vector Store singleton."""
    if not hasattr(get_vector_store, "_instance"):
        get_vector_store._instance = VectorStoreService()
    return get_vector_store._instance


# =============================================================================
# QUERY ENDPOINT
# =============================================================================

@router.post(
    "/query",
    response_model=QueryResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Geçersiz istek"},
        500: {"model": ErrorResponse, "description": "Sunucu hatası"}
    },
    summary="RAG Sorgusu",
    description="Sinema veritabanında semantik arama yapar ve LLM ile cevap üretir."
)
async def query(
    request: QueryRequest,
    pipeline: RAGPipeline = Depends(get_rag_pipeline)
) -> QueryResponse:
    """
    RAG Query Endpoint.
    
    Flow:
    1. Request validation (Pydantic otomatik yapar)
    2. Source filter mapping (API enum → Internal enum)
    3. Pipeline çağrısı
    4. Response mapping (Internal DTO → API schema)
    """
    logger.info(f"📨 Query request: {request.question[:50]}...")
    
    try:
        # Source filter mapping: API enum → RAG enum
        source_filter = None
        if request.source_filter:
            source_filter = SourceType(request.source_filter.value)
        
        # RAG Pipeline çağrısı
        result = pipeline.query(
            question=request.question,
            limit=request.limit,
            source_filter=source_filter
        )
        
        # Response mapping: Internal DTO → API Schema
        sources = [
            SourceDocument(
                content=src.content[:500],  # Truncate for response size
                source=SourceTypeEnum(src.source.value),
                movie_title=src.movie_title,
                distance=round(src.distance, 4)
            )
            for src in result.sources
        ]
        
        return QueryResponse(
            answer=result.answer,
            sources=sources,
            query=result.query,
            source_count=len(sources),
            token_usage=TokenUsage(
                input_tokens=result.tokens_used,  # TODO: Detaylı token tracking
                output_tokens=0,
                total_tokens=result.tokens_used
            ) if result.tokens_used else None
        )
        
    except Exception as e:
        logger.error(f"❌ Query hatası: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Sorgu işlenirken hata oluştu: {str(e)}"
        )


# =============================================================================
# INGEST ENDPOINT
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
    
    Neden BackgroundTasks?
    - Ingestion uzun sürer (API timeout'a düşmesin)
    - Client hemen cevap alır, işlem arka planda devam eder
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
# MOVIE ENDPOINT
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
    
    Neden GET?
    - Idempotent: Aynı ID her zaman aynı sonucu verir
    - Cacheable: CDN/Browser cache yapılabilir
    - Safe: Sunucu state'ini değiştirmez
    """
    logger.info(f"🎬 Movie request: {movie_id}")
    
    # Vector store'dan film metadata'sı ara
    # TODO: Dedicated movie service eklenebilir
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
    
    # Document count for this movie
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
# HEALTH ENDPOINT
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
    
    Neden önemli?
    - Kubernetes/Docker liveness probe
    - Load balancer health check
    - Monitoring sistemleri
    """
    services = {}
    
    # Vector Store check
    try:
        count = vector_store.count()
        services["vector_store"] = f"ok ({count} documents)"
    except Exception as e:
        services["vector_store"] = f"error: {str(e)}"
    
    # Embedding service check
    try:
        from src.domain.embeddings import EmbeddingService
        emb = EmbeddingService()
        services["embedding"] = "ok"
    except Exception as e:
        services["embedding"] = f"error: {str(e)}"
    
    # LLM check (sadece config, actual call pahalı)
    try:
        from src.infrastructure.config import get_settings
        settings = get_settings()
        if settings.GOOGLE_API_KEY:
            services["llm"] = "ok (configured)"
        else:
            services["llm"] = "error: API key missing"
    except Exception as e:
        services["llm"] = f"error: {str(e)}"
    
    # Overall status
    all_ok = all("ok" in str(v) for v in services.values())
    status = "healthy" if all_ok else "degraded"
    
    return HealthResponse(
        status=status,
        version="1.0.0",
        services=services
    )