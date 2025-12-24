import logging
import chromadb
from typing import List, Dict, Any, Optional
import uuid

logger = logging.getLogger(__name__)

class VectorStoreService:
    """
    ChromaDB Vector Store Wrapper.
    768-boyutlu vektörleri yerel diskte saklar.
    """
    
    EMBEDDING_DIM = 768
    
    def __init__(self, collection_name: str = "cinemind_store", persist_path: str = "data/vector_store"):
        self.persist_path = persist_path
        self.collection_name = collection_name
        
        try:
            self.client = chromadb.PersistentClient(path=persist_path)
            self.collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"💾 Vector Store: {persist_path}/{collection_name}")
            
        except Exception as e:
            logger.error(f"❌ ChromaDB init error: {e}")
            raise

    def add_documents(
        self, 
        texts: List[str], 
        embeddings: List[List[float]], 
        metadatas: List[Dict[str, Any]],
        ids: Optional[List[str]] = None
    ):
        """Dokümanları vector store'a ekler."""
        if not texts or not embeddings:
            logger.warning("⚠️ Boş veri, ekleme atlandı")
            return

        # Validation
        if len(texts) != len(embeddings) != len(metadatas):
            raise ValueError("texts, embeddings ve metadatas uzunlukları eşit olmalı")
        
        # Dimension check
        if embeddings and len(embeddings[0]) != self.EMBEDDING_DIM:
            logger.warning(
                f"⚠️ Embedding boyutu uyumsuz: {len(embeddings[0])} "
                f"(beklenen: {self.EMBEDDING_DIM})"
            )

        try:
            if not ids:
                ids = [str(uuid.uuid4()) for _ in texts]
                
            self.collection.add(
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )
            logger.info(f"✅ {len(texts)} doküman eklendi")
            
        except Exception as e:
            logger.error(f"❌ Add error: {e}")
            raise

    def search(
        self, 
        query_vector: List[float], 
        limit: int = 5, 
        filter: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Semantik arama yapar.
        
        Returns:
            [{"id": str, "document": str, "metadata": dict, "distance": float}, ...]
        """
        try:
            results = self.collection.query(
                query_embeddings=[query_vector],
                n_results=limit,
                where=filter
            )
            
            # Format response
            formatted = []
            if results['ids'] and results['ids'][0]:
                for i in range(len(results['documents'][0])):
                    formatted.append({
                        "id": results['ids'][0][i],
                        "document": results['documents'][0][i],
                        "metadata": results['metadatas'][0][i],
                        "distance": results['distances'][0][i]
                    })
            
            logger.info(f"🔍 {len(formatted)} sonuç bulundu")
            return formatted
            
        except Exception as e:
            logger.error(f"❌ Search error: {e}")
            return []
    
    def get_by_id(self, doc_id: str) -> Optional[Dict]:
        """ID ile doküman getir."""
        try:
            result = self.collection.get(ids=[doc_id])
            if result['documents']:
                return {
                    "id": doc_id,
                    "document": result['documents'][0],
                    "metadata": result['metadatas'][0]
                }
            return None
        except Exception as e:
            logger.error(f"❌ Get by ID error: {e}")
            return None
    
    def delete_by_ids(self, ids: List[str]):
        """Dokümanları sil."""
        try:
            self.collection.delete(ids=ids)
            logger.info(f"🗑️ {len(ids)} doküman silindi")
        except Exception as e:
            logger.error(f"❌ Delete error: {e}")
            
    def count(self) -> int:
        """Toplam doküman sayısı."""
        return self.collection.count()
    
    def reset_collection(self):
        """⚠️ UYARI: Tüm veriyi siler (Test için)."""
        try:
            self.client.delete_collection(self.collection_name)
            self.collection = self.client.create_collection(
                self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            logger.warning(f"♻️ Koleksiyon sıfırlandı: {self.collection_name}")
        except Exception as e:
            logger.error(f"❌ Reset error: {e}")