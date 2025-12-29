"""
Context Builder
Tek sorumluluk: Retrieved dokümanları LLM context'ine formatlamak.
"""
import logging
from typing import List

from .dtos import RetrievedDocument, SourceType

logger = logging.getLogger(__name__)


class ContextBuilder:
    """
    Dokümanları LLM için hazırlar.
    
    Token limiti aşılırsa erken keser,
    böylece context window taşmaz.
    """
    
    SOURCE_LABELS = {
        SourceType.SCRIPT: "📜 SENARYO",
        SourceType.IMDB: "🎬 IMDB YORUM",
        SourceType.TMDB: "🎥 TMDB YORUM",
    }
    
    def __init__(self, max_tokens: int = 3000):
        self._max_tokens = max_tokens
    
    def build(self, documents: List[RetrievedDocument]) -> str:
        """
        Dokümanları context string'e dönüştür.
        
        Args:
            documents: Sıralı doküman listesi
            
        Returns:
            Formatlanmış context string
        """
        if not documents:
            return "İlgili bilgi bulunamadı."
        
        context_parts = []
        current_tokens = 0
        
        for doc in documents:
            doc_tokens = self._estimate_tokens(doc.content)
            
            if current_tokens + doc_tokens > self._max_tokens:
                logger.warning(
                    f"⚠️ Token limit ({self._max_tokens}), "
                    f"{len(context_parts)} doküman kullanılıyor"
                )
                break
            
            formatted = self._format_document(doc)
            context_parts.append(formatted)
            current_tokens += doc_tokens
        
        context = "\n".join(context_parts)
        
        logger.info(
            f"📝 Context: ~{current_tokens} token, "
            f"{len(context_parts)} kaynak"
        )
        
        return context
    
    def _format_document(self, doc: RetrievedDocument) -> str:
        """Tek dokümanı formatla."""
        label = self.SOURCE_LABELS.get(doc.source, "📄 DOKÜMAN")
        
        return f"[{label}] {doc.movie_title}\n---\n{doc.content}"
    
    def _estimate_tokens(self, text: str) -> int:
        """Kaba token tahmini (4 karakter ≈ 1 token)."""
        return len(text) // 4