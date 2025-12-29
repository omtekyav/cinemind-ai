"""
Retriever
Tek sorumluluk: Vector store'dan ilgili dokümanları getirmek.
"""
import logging
from typing import List, Optional, Protocol

from .dtos import RetrievedDocument, SourceType

logger = logging.getLogger(__name__)


class EmbeddingProvider(Protocol):
    """Embedding servisi interface'i (Dependency Inversion)."""
    def embed_query(self, text: str) -> Optional[List[float]]: ...


class VectorStoreProvider(Protocol):
    """Vector store interface'i (Dependency Inversion)."""
    def search(
        self,
        query_vector: List[float],
        limit: int,
        filter: Optional[dict]
    ) -> List[dict]: ...


class Retriever:
    """
    Doküman getirme servisi.
    
    Protocol'lere bağımlı olduğu için:
    - Unit test'te mock geçebilirsin
    - Farklı embedding/vector store ile çalışabilir
    """
    
    SOURCE_WEIGHTS = {
        SourceType.SCRIPT: 1.0,   # Senaryo en güvenilir
        SourceType.IMDB: 0.9,     # IMDb yorumları
        SourceType.TMDB: 0.8,     # TMDb yorumları
    }
    
    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStoreProvider
    ):
        self._embedding = embedding_provider
        self._vector_store = vector_store
    
    def retrieve(
        self,
        query: str,
        limit: int = 10,
        source_filter: Optional[SourceType] = None
    ) -> List[RetrievedDocument]:
        """
        Sorguya en yakın dokümanları getir.
        
        Args:
            query: Kullanıcı sorusu
            limit: Maksimum sonuç sayısı
            source_filter: Belirli kaynaktan çek (opsiyonel)
            
        Returns:
            Ağırlıklı skora göre sıralı dokümanlar
        """
        # 1. Query → Vector
        query_vector = self._embedding.embed_query(query)
        if not query_vector:
            logger.error("❌ Query embedding başarısız")
            return []
        
        # 2. Vector Search
        where_filter = {"source": source_filter.value} if source_filter else None
        
        results = self._vector_store.search(
            query_vector=query_vector,
            limit=limit,
            filter=where_filter
        )
        
        # 3. Parse & Weight
        documents = self._parse_results(results)
        documents = self._apply_weights(documents)
        
        logger.info(f"🔍 {len(documents)} doküman bulundu")
        return documents
    
    def _parse_results(self, results: List[dict]) -> List[RetrievedDocument]:
        """Raw sonuçları RetrievedDocument'e çevir."""
        documents = []
        
        for r in results:
            meta = r.get("metadata", {})
            source_str = meta.get("source", "tmdb")
            
            try:
                source = SourceType(source_str)
            except ValueError:
                source = SourceType.TMDB
            
            doc = RetrievedDocument(
                content=r.get("document", ""),
                source=source,
                movie_title=meta.get("movie_title", "Unknown"),
                distance=r.get("distance", 1.0),
                metadata=meta
            )
            documents.append(doc)
        
        return documents
    
    def _apply_weights(
        self,
        documents: List[RetrievedDocument]
    ) -> List[RetrievedDocument]:
        """Kaynak ağırlıklarını uygula ve sırala."""
        for doc in documents:
            weight = self.SOURCE_WEIGHTS.get(doc.source, 0.5)
            doc.weighted_score = doc.distance * (1 / weight)
        
        documents.sort(key=lambda x: x.weighted_score)
        return documents