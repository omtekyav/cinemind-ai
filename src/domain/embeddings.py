import os
import time
import logging
from typing import List, Optional
from functools import lru_cache
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class EmbeddingService:
    """
    Google Gemini Embedding Service.
    Kullanıcı sorularını ve dokümanları vektöre çevirir.
    """
    
    DEFAULT_MODEL = "models/text-embedding-004"
    MAX_BATCH_SIZE = 100  # Gemini API limiti
    
    def __init__(self, model_name: Optional[str] = None):
        """
        Args:
            model_name: Kullanılacak embedding modeli (default: text-embedding-004)
        
        Raises:
            ValueError: GOOGLE_API_KEY bulunamazsa
        """
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError(
                "❌ GOOGLE_API_KEY bulunamadı! "
                ".env dosyasında GOOGLE_API_KEY=your_key_here ekleyin"
            )
        
        genai.configure(api_key=api_key)
        self.model_name = model_name or self.DEFAULT_MODEL
        logger.info(f"✨ Embedding Service başlatıldı (Model: {self.model_name})")
    
    def embed_query(self, text: str) -> Optional[List[float]]:
        """
        Kullanıcı sorgusunu vektöre çevirir.
        
        Args:
            text: Kullanıcı sorusu
        
        Returns:
            768 boyutlu embedding vektörü veya hata durumunda None
        """
        if not text or not text.strip():
            logger.warning("⚠️ Boş text embed edilmeye çalışıldı")
            return None
        
        try:
            result = genai.embed_content(
                model=self.model_name,
                content=text,
                task_type="retrieval_query"
            )
            
            embedding = result.get('embedding')
            if embedding:
                logger.debug(f"✅ Query embedding: {len(embedding)} boyut")
                return embedding
            else:
                logger.error("❌ API'den embedding dönmedi")
                return None
                
        except Exception as e:
            logger.error(f"❌ Embedding hatası (Query): {str(e)}")
            return None
    
    def embed_documents(
        self, 
        texts: List[str], 
        batch_size: int = 20
    ) -> List[Optional[List[float]]]:
        """
        Doküman listesini batch'ler halinde vektöre çevirir.
        
        Args:
            texts: Embed edilecek text listesi
            batch_size: Her batch'teki text sayısı (max: 100)
        
        Returns:
            Her text için embedding vektörü (başarısızsa None)
        """
        if not texts:
            return []
        
        # Batch size kontrolü
        batch_size = min(batch_size, self.MAX_BATCH_SIZE)
        
        all_embeddings: List[Optional[List[float]]] = []
        total_batches = (len(texts) + batch_size - 1) // batch_size
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            batch_num = (i // batch_size) + 1
            
            try:
                result = genai.embed_content(
                    model=self.model_name,
                    content=batch,
                    task_type="retrieval_document"
                )
                
                # API response parsing
                embeddings = result.get('embedding', [])
                
                # Tek text için API List[float] döner, çok text için List[List[float]]
                if len(batch) == 1:
                    # Tek elemanlı batch
                    if isinstance(embeddings, list) and isinstance(embeddings[0], float):
                        all_embeddings.append(embeddings)
                    else:
                        # API yapısı değişmişse
                        all_embeddings.append(embeddings if embeddings else None)
                else:
                    # Çok elemanlı batch
                    if isinstance(embeddings, list) and len(embeddings) == len(batch):
                        all_embeddings.extend(embeddings)
                    else:
                        logger.error(
                            f"❌ Batch {batch_num}: Beklenen {len(batch)} embedding, "
                            f"alınan {len(embeddings) if embeddings else 0}"
                        )
                        all_embeddings.extend([None] * len(batch))
                
                logger.info(
                    f"✅ Batch {batch_num}/{total_batches} işlendi "
                    f"({len(batch)} doküman)"
                )
                
                # Rate limiting (Gemini free tier: 60 req/min)
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(
                    f"❌ Batch {batch_num} embedding hatası: {str(e)}\n"
                    f"Batch içeriği: {[t[:50] + '...' for t in batch]}"
                )
                # Hata durumunda None ekle
                all_embeddings.extend([None] * len(batch))
                time.sleep(2)  # Hata sonrası daha uzun bekle
        
        # Son kontrol
        if len(all_embeddings) != len(texts):
            logger.error(
                f"❌ Embedding sayısı uyuşmuyor! "
                f"Beklenen: {len(texts)}, Alınan: {len(all_embeddings)}"
            )
        
        return all_embeddings
    
    def get_embedding_dimension(self) -> int:
        """
        Embedding boyutunu döndürür.
        
        Returns:
            768 (text-embedding-004 için)
        """
        # text-embedding-004 için 768 boyut
        return 768


