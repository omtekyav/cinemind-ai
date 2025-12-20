import pytest
import asyncio
import logging
from src.services.imdb_scraper_service import ImdbScraperService

# Test sırasında log çıktılarını görmek için
logging.basicConfig(level=logging.INFO)

class TestImdbScraperIntegration:
    """
    Gerçek IMDb sitesine bağlanarak scraper'ın çalışıp çalışmadığını test eder.
    
    ⚠️ UYARI: Bu test gerçek network çağrısı yapar, bu yüzden:
    - İnternet bağlantısı gerektirir
    - IMDb'nin erişilebilir olması gerekir
    - Rate limiting nedeniyle yavaş çalışır (2-4 saniye bekleme)
    """
    
    @pytest.fixture
    def scraper(self):
        """Her test için yeni bir scraper instance oluşturur."""
        return ImdbScraperService()
    
    @pytest.mark.asyncio
    async def test_fetch_reviews_success(self, scraper):
        """
        Test: The Dark Knight (tt0468569) için yorumları çekebiliyor mu?
        Beklenti: En az 1 yorum dönmeli ve yapısal olarak doğru olmalı.
        """
        imdb_id = "tt0468569"  # The Dark Knight
        max_reviews = 3
        
        # Act
        reviews = await scraper.fetch_reviews(imdb_id, max_reviews=max_reviews)
        
        # Assert
        assert len(reviews) > 0, "Hiç yorum çekilemedi!"
        assert len(reviews) <= max_reviews, f"Limit aşıldı: {len(reviews)} > {max_reviews}"
        
        # İlk yorumu kontrol et
        first_review = reviews[0]
        
        # Zorunlu alanlar
        assert "source" in first_review, "source field eksik"
        assert "title" in first_review, "title field eksik"
        assert "content" in first_review, "content field eksik"
        assert "rating" in first_review, "rating field eksik"
        
        # Değer kontrolü
        assert first_review["source"] == "imdb", "source 'imdb' olmalı"
        assert isinstance(first_review["content"], str), "content string olmalı"
        assert len(first_review["content"]) > 0, "content boş olamaz"
        
        # Rating optional ama varsa float olmalı
        if first_review["rating"] is not None:
            assert isinstance(first_review["rating"], float), "rating float olmalı"
            assert 0 <= first_review["rating"] <= 10, "rating 0-10 arası olmalı"
        
        # Debug: İlk yorumu yazdır
        print("\n--- İLK YORUM ---")
        print(f"Başlık: {first_review['title']}")
        print(f"Puan: {first_review['rating']}")
        print(f"İçerik (ilk 100 karakter): {first_review['content'][:100]}...")
    
    @pytest.mark.asyncio
    async def test_invalid_imdb_id(self, scraper):
        """
        Test: Geçersiz IMDb ID ile boş liste dönüyor mu?
        """
        invalid_id = "tt9999999999"  # Olmayan bir ID
        
        # Act
        reviews = await scraper.fetch_reviews(invalid_id, max_reviews=3)
        
        # Assert
        assert reviews == [], "Geçersiz ID için boş liste dönmeliydi"
    
    @pytest.mark.asyncio
    async def test_multiple_reviews_structure(self, scraper):
        """
        Test: Birden fazla yorum aynı yapıda mı?
        """
        imdb_id = "tt0468569"
        max_reviews = 5
        
        # Act
        reviews = await scraper.fetch_reviews(imdb_id, max_reviews=max_reviews)
        
        # Assert
        assert len(reviews) > 1, "En az 2 yorum olmalı test için"
        
        # Her yorumun yapısını kontrol et
        for idx, review in enumerate(reviews):
            assert "source" in review, f"Review {idx}: source eksik"
            assert "title" in review, f"Review {idx}: title eksik"
            assert "content" in review, f"Review {idx}: content eksik"
            assert "rating" in review, f"Review {idx}: rating eksik"
            
            # İçerik boş olmamalı
            assert len(review["content"]) > 0, f"Review {idx}: content boş"
        
        print(f"\n✅ {len(reviews)} yorum yapısal olarak doğru")
    
    @pytest.mark.asyncio
    async def test_rate_limiting_applied(self, scraper):
        """
        Test: Rate limiting çalışıyor mu?
        2 ardışık istek arasında en az 2 saniye geçmeli.
        """
        import time
        
        imdb_id = "tt0468569"
        
        # İlk istek
        start = time.time()
        await scraper.fetch_reviews(imdb_id, max_reviews=1)
        
        # İkinci istek
        await scraper.fetch_reviews(imdb_id, max_reviews=1)
        elapsed = time.time() - start
        
        # Assert: Toplam süre en az 4 saniye (2 istek × 2 saniye min wait)
        assert elapsed >= 4.0, f"Rate limiting çalışmıyor: {elapsed:.2f}s < 4.0s"
        
        print(f"\n✅ Rate limiting aktif: {elapsed:.2f}s geçti")


# --- MANUEL TEST (Direkt çalıştırma için) ---
if __name__ == "__main__":
    async def quick_test():
        """Pytest olmadan hızlı test."""
        print("🚀 Hızlı Test Başlıyor...\n")
        
        scraper = ImdbScraperService()
        reviews = await scraper.fetch_reviews("tt0468569", max_reviews=2)
        
        if reviews:
            print(f"✅ {len(reviews)} yorum çekildi")
            print(f"İlk yorum başlık: {reviews[0]['title']}")
            print(f"İlk yorum rating: {reviews[0]['rating']}")
        else:
            print("❌ Test başarısız")
    
    asyncio.run(quick_test())