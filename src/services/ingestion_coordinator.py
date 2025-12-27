"""
Ingestion Coordinator
Tüm ingestion işlemlerini orkestra eden merkezi servis.
"""
import logging
import asyncio
from typing import List

from src.infrastructure.config import get_settings
from src.services.tmdb_service import TMDbService
from src.services.imdb_scraper_service import ImdbScraperService
from src.services.pdf_parser_service import PdfParserService
from src.services.sentiment_client import SentimentClient
from src.infrastructure.vector_store import VectorStoreService
from src.domain.embeddings import EmbeddingService
from src.domain.models import (
    CinemaDocument, 
    SentimentResult, 
    Movie, 
    IMDbReview,
    ScriptScene,
    DataSource  # ← Enum'u import et
)
from pathlib import Path

logger = logging.getLogger(__name__)


class IngestionCoordinator:
    """
    Tüm Ingestion İşlemlerinin Merkezi.
    Hem TMDb, IMDb hem de Script akışlarını buradan yönetir.
    """
    
    def __init__(self):
        self.settings = get_settings()
        
        # 1. Veri Kaynakları (Tedarikçiler)
        self.tmdb_service = TMDbService()
        self.imdb_service = ImdbScraperService()
        self.pdf_parser = PdfParserService(chunk_size=1000, chunk_overlap=200)
        
        # 2. Analiz ve Kayıt Araçları
        self.sentiment_client = SentimentClient(
            base_url=self.settings.SENTIMENT_SERVICE_URL,
            fail_open=True
        )
        self.embedding_service = EmbeddingService()
        self.vector_store = VectorStoreService(
            collection_name="cinemind_store",
            persist_path="data/vector_store"
        )
    
    # =========================================================================
    # 1. TMDb AKIŞI (Popüler Filmleri Çek)
    # =========================================================================
    
    async def run_tmdb_batch(self, limit: int = 5):
        """Popüler filmleri TMDb'den çek ve işle."""
        logger.info(f"🚀 TMDb Batch Başlıyor: {limit} Film")
        
        try:
            data = await self.tmdb_service._request("/movie/popular", {"page": 1})
            movies = data.get("results", [])[:limit]
        except Exception as e:
            logger.error(f"❌ TMDb liste hatası: {e}")
            return
        
        for m_data in movies:
            await self._process_tmdb_movie(m_data["id"])
            await asyncio.sleep(0.5)  # Rate limiting
        
        logger.info("🎉 TMDb Batch Tamamlandı.")
    
    async def _process_tmdb_movie(self, tmdb_id: int):
        """Tek bir TMDb filmini işle."""
        # Veri çek
        movie = await self.tmdb_service.get_movie(tmdb_id)
        reviews = await self.tmdb_service.get_reviews(tmdb_id, max_pages=1)
        
        if not movie or not reviews:
            return
        
        logger.info(f"🎬 TMDb İşleniyor: {movie.title} ({len(reviews)} yorum)")
        
        # Analiz et ve kaydet
        await self._analyze_and_store(movie, reviews, source_type="tmdb")
    
    # =========================================================================
    # 2. IMDb AKIŞI (Manuel Listeden Çek)
    # =========================================================================
    
    async def run_imdb_pipeline(self, limit: int = 3):
        """Sample IMDb filmlerini scrape et ve işle."""
        # IMDb API olmadığı için hedef listesiyle çalışıyoruz
        targets = [
            {"id": "tt1375666", "title": "Inception", "year": 2010},
            {"id": "tt0468569", "title": "The Dark Knight", "year": 2008},
            {"id": "tt0133093", "title": "The Matrix", "year": 1999},
            {"id": "tt0111161", "title": "The Shawshank Redemption", "year": 1994},
            {"id": "tt0068646", "title": "The Godfather", "year": 1972}
        ]
        
        logger.info(f"🚀 IMDb Pipeline Başlıyor: {limit} Film")
        
        for t in targets[:limit]:
            logger.info(f"🔍 IMDb Scraping: {t['title']}")
            
            # Movie objesini manuel oluştur (source parametresi YOK)
            movie = Movie(
                movie_id=f"imdb-{t['id']}", 
                title=t["title"], 
                year=t["year"]
            )
            
            # Scraper Service ile yorumları çek
            raw_reviews = await self.imdb_service.fetch_reviews(t["id"], max_reviews=5)
            
            if raw_reviews:
                # Dict -> IMDbReview modeline dönüştür
                reviews_models = []
                for i, r in enumerate(raw_reviews):
                    reviews_models.append(IMDbReview(
                        review_id=f"imdb-{t['id']}-{i}",
                        movie_id=t["id"],
                        author=r.get("title", "Anonymous"),
                        text=r["content"],
                        rating=r.get("rating"),
                        source=DataSource.IMDB  # ← Enum kullan
                    ))
                
                # Ortak kaydetme fonksiyonuna gönder
                await self._analyze_and_store(movie, reviews_models, source_type="imdb")
            
            await asyncio.sleep(3)  # Anti-bot beklemesi
        
        logger.info("🎉 IMDb Pipeline Tamamlandı.")
    
    # =========================================================================
    # 3. SCRIPT AKIŞI (PDF Senaryo Dosyaları)
    # =========================================================================
    
    async def run_script_pipeline(self):
        """data/scripts/ klasöründeki PDF'leri işle."""
        scripts_dir = Path("data/scripts")
        scripts_dir.mkdir(parents=True, exist_ok=True)
        
        pdf_files = list(scripts_dir.glob("*.pdf"))
        
        if not pdf_files:
            logger.warning(f"⚠️ {scripts_dir} klasöründe PDF bulunamadı.")
            logger.info(f"💡 Örnek PDF'leri buraya koyun: {scripts_dir.absolute()}")
            return
        
        logger.info(f"🚀 Script Pipeline Başlıyor: {len(pdf_files)} dosya")
        
        for pdf_path in pdf_files:
            await self._process_script_file(pdf_path)
        
        logger.info("🎉 Script Pipeline Tamamlandı.")
    
    async def _process_script_file(self, pdf_path: Path):
        """Tek bir PDF senaryosunu işle."""
        logger.info(f"📄 İşleniyor: {pdf_path.name}")
        
        # Film bilgilerini dosya adından çıkar
        movie_info = self._extract_movie_info_from_filename(pdf_path.name)
        movie = Movie(
            movie_id=movie_info["movie_id"],
            title=movie_info["title"],
            year=movie_info["year"]
        )
        
        # PDF'i chunk'lara böl
        chunks = self.pdf_parser.load_and_split(
            str(pdf_path), 
            movie_id=movie_info["movie_id"]
        )
        
        if not chunks:
            logger.warning(f"⚠️ {pdf_path.name} için chunk oluşturulamadı.")
            return
        
        logger.info(f"✂️ {len(chunks)} chunk oluşturuldu.")
        
        # ScriptScene objelerine dönüştür
        scenes = []
        for i, chunk_data in enumerate(chunks):
            scene = ScriptScene(
                scene_id=f"{movie_info['movie_id']}_chunk{i}",
                movie_id=movie_info["movie_id"],
                scene_number=i + 1,
                heading=f"Chunk {i+1}/{len(chunks)}",
                dialogue=chunk_data["content"],
                page_number=None
            )
            scenes.append(scene)
        
        # Senaryolarda sentiment analizi YAPMA (opsiyonel)
        await self._store_scripts(movie, scenes)
    
    def _extract_movie_info_from_filename(self, filename: str) -> dict:
        """Dosya adından film bilgilerini çıkar (the-dark-knight-2008.pdf)."""
        stem = Path(filename).stem
        parts = stem.split("-")
        
        year = None
        title_parts = parts
        
        if parts and parts[-1].isdigit() and len(parts[-1]) == 4:
            year = int(parts[-1])
            title_parts = parts[:-1]
        
        title = " ".join(word.capitalize() for word in title_parts)
        
        return {
            "movie_id": f"script_{stem}",
            "title": title,
            "year": year
        }
    
    # =========================================================================
    # ORTAK FONKSİYONLAR (Sentiment + Embedding + Save)
    # =========================================================================
    
    async def _analyze_and_store(self, movie: Movie, reviews, source_type: str):
        """Hem TMDb hem IMDb yorumlarını analiz edip kaydeder."""
        
        # 1. Sentiment Analizi (Batch)
        texts = [r.text for r in reviews]
        sentiments = self.sentiment_client.analyze_batch(texts)
        
        documents = []
        for review, sent in zip(reviews, sentiments):
            # Sentiment sonucunu ekle
            review.sentiment = SentimentResult(
                label=sent.get("sentiment", "Nötr"),
                score=sent.get("confidence", 0.0)
            )
            
            # Hangi kaynaktan geldiyse ona göre Document üret
            if source_type == "tmdb":
                doc = CinemaDocument.from_tmdb_review(movie, review)
            else:
                doc = CinemaDocument.from_imdb_review(movie, review)
            
            documents.append(doc)
        
        # 2. Embedding ve Kayıt
        await self._embed_and_store(documents, source_type)
    
    async def _store_scripts(self, movie: Movie, scenes):
        """Senaryo metinlerini kaydet (sentiment yok)."""
        documents = []
        for scene in scenes:
            doc = CinemaDocument.from_script_scene(movie, scene)
            documents.append(doc)
        
        await self._embed_and_store(documents, "script")
    
    async def _embed_and_store(self, documents: List[CinemaDocument], source_type: str):
        """Dokümanları embed et ve Vector Store'a kaydet."""
        if not documents:
            return
        
        texts = [d.content for d in documents]
        embeddings = self.embedding_service.embed_documents(texts)
        
        valid_ids, valid_texts, valid_metas, valid_embs = [], [], [], []
        for doc, emb in zip(documents, embeddings):
            if emb:
                _, _, meta, _ = doc.to_chroma_format()
                valid_ids.append(doc.doc_id)
                valid_texts.append(doc.content)
                valid_metas.append(meta)
                valid_embs.append(emb)
        
        if valid_ids:
            self.vector_store.add_documents(valid_texts, valid_embs, valid_metas, valid_ids)
            logger.info(f"   ✅ Kaydedildi: {len(valid_ids)} belge ({source_type})")
    
    def close(self):
        """Servisleri temizle."""
        self.sentiment_client.close()