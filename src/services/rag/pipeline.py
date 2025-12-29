"""
RAG Pipeline
Orchestrator: Tüm bileşenleri koordine eder.
Kendisi iş yapmaz, delegasyon yapar (Facade Pattern).
"""
import logging
from typing import Optional

from src.domain.embeddings import EmbeddingService
from src.infrastructure.vector_store import VectorStoreService
from src.infrastructure.config import get_settings

from .dtos import RAGResponse, SourceType
from .retriever import Retriever
from .context_builder import ContextBuilder
from .generator import Generator

logger = logging.getLogger(__name__)


class RAGPipeline:
    """
    RAG Orchestrator.
    
    Dependency Injection destekli:
    - Test'te mock nesneler geçebilirsin
    - Production'da gerçek servisler kullanılır
    """
    
    def __init__(
        self,
        retriever: Optional[Retriever] = None,
        context_builder: Optional[ContextBuilder] = None,
        generator: Optional[Generator] = None
    ):
        """
        Args:
            retriever: Doküman getirici (None ise default oluşturulur)
            context_builder: Context formatlayıcı (None ise default)
            generator: LLM cevap üretici (None ise default)
        """
        settings = get_settings()
        
        # Default implementations (DI yoksa)
        if retriever is None:
            embedding_service = EmbeddingService()
            vector_store = VectorStoreService()
            retriever = Retriever(embedding_service, vector_store)
        
        if context_builder is None:
            context_builder = ContextBuilder(max_tokens=3000)
        
        if generator is None:
            generator = Generator(
                api_key=settings.GOOGLE_API_KEY,
                model="models/gemini-2.5-flash"
            )
        
        self._retriever = retriever
        self._context_builder = context_builder
        self._generator = generator
        
        logger.info("🧠 RAG Pipeline başlatıldı")
    
    def query(
        self,
        question: str,
        limit: int = 10,
        source_filter: Optional[SourceType] = None
    ) -> RAGResponse:
        """
        Ana RAG akışı.
        
        Args:
            question: Kullanıcı sorusu
            limit: Maksimum doküman sayısı
            source_filter: Belirli kaynaktan çek (opsiyonel)
            
        Returns:
            RAGResponse: Cevap + kaynaklar + orijinal soru
        """
        logger.info(f"🎯 Query: {question[:50]}...")
        
        # 1. Retrieve - Dokümanları getir
        documents = self._retriever.retrieve(
            query=question,
            limit=limit,
            source_filter=source_filter
        )
        
        # Boş sonuç kontrolü
        if not documents:
            return RAGResponse(
                answer="Bu konuda veritabanımda bilgi bulamadım.",
                sources=[],
                query=question
            )
        
        # 2. Build Context - Formatla
        context = self._context_builder.build(documents)
        
        # 3. Generate - Cevap üret
        answer = self._generator.generate(question, context)
        
        return RAGResponse(
            answer=answer,
            sources=documents[:5],  # İlk 5 kaynağı döndür
            query=question
        )
    
    def query_movie(self, movie_title: str, question: str) -> RAGResponse:
        """
        Belirli bir film hakkında soru sor.
        
        Args:
            movie_title: Film adı (örn: "The Dark Knight")
            question: Soru (örn: "Joker'in motivasyonu nedir?")
        """
        enhanced_query = f"{movie_title}: {question}"
        return self.query(enhanced_query)