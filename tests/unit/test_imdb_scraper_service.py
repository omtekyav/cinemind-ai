import pytest
from unittest.mock import Mock, patch, AsyncMock
import httpx
from src.services.imdb_scraper_service import ImdbScraperService

# --- MOCK DATA (SAHTE HTML) ---
# IMDb'nin karmaşık yapısının basitleştirilmiş bir taklidi.
# Testin amacı HTML parser'ın bu yapıyı çözüp çözemediğini görmektir.
MOCK_HTML_CONTENT = """
<html>
    <body>
        <div class="review-container">
            <div class="lister-item-content">
                <a class="title"> Mükemmel Bir Film </a>
                <div class="display-name-date">
                    <span class="rating-other-user-rating">
                        <span>9/10</span>
                    </span>
                </div>
                <div class="content">
                    <div class="text show-more__control">
                        Bu film sinema tarihinin en iyisidir.
                        <br> Kesinlikle izleyin.
                    </div>
                </div>
            </div>
        </div>
        
        <div class="review-container">
            <a class="title"> Fena Değil </a>
            <div class="text show-more__control"> Ortalama bir filmdi. </div>
            </div>
    </body>
</html>
"""

@pytest.mark.asyncio
async def test_fetch_reviews_success():
    """
    SENARYO 1: Başarılı Scraping İşlemi
    Beklenti: HTML'in doğru parse edilmesi ve List[Dict] dönmesi.
    """
    # 1. Mock (Sahte) Response Hazırla
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = MOCK_HTML_CONTENT
    mock_response.raise_for_status = Mock()

    # 2. Patch İşlemi (Interceptor)
    # httpx.AsyncClient.get metodunu yakalayıp bizim sahte cevabı döndürüyoruz.
    # asyncio.sleep metodunu yakalayıp bekleme süresini sıfırlıyoruz (Hız için).
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get, \
         patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        
        mock_get.return_value = mock_response
        
        # 3. Servisi Çalıştır
        service = ImdbScraperService()
        reviews = await service.fetch_reviews("tt_dummy_id", max_reviews=5)

        # 4. Doğrulamalar (Assertions)
        assert len(reviews) == 2, "2 adet yorum çekilmeliydi"
        
        # Yorum 1 Kontrolü (Tam veri)
        review1 = reviews[0]
        assert review1["title"] == "Mükemmel Bir Film"
        assert review1["rating"] == 9.0
        assert "sinema tarihinin" in review1["content"]
        assert review1["source"] == "imdb"
        
        # Yorum 2 Kontrolü (Eksik veri)
        review2 = reviews[1]
        assert review2["title"] == "Fena Değil"
        assert review2["rating"] is None  # Rating yoksa None dönmeli

@pytest.mark.asyncio
async def test_fetch_reviews_network_error():
    """
    SENARYO 2: Network Hatası (Graceful Failure)
    Beklenti: İnternet koptuğunda servisin çökmemesi ve boş liste dönmesi.
    """
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get, \
         patch("asyncio.sleep", new_callable=AsyncMock):
        
        # Side Effect: Metot çağrıldığında Hata fırlat
        mock_get.side_effect = httpx.RequestError("Bağlantı koptu")
        
        service = ImdbScraperService()
        reviews = await service.fetch_reviews("tt_dummy_id")
        
        # Servis çökmek yerine boş liste dönmeli
        assert reviews == []
        assert isinstance(reviews, list)

@pytest.mark.asyncio
async def test_fetch_reviews_http_error():
    """
    SENARYO 3: HTTP Hatası (404 Not Found)
    Beklenti: Yanlış ID girildiğinde 404 hatasının yakalanması.
    """
    mock_response = Mock()
    mock_response.status_code = 404
    # raise_for_status çağrıldığında hata fırlatacak şekilde ayarla
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Not Found", request=Mock(), response=mock_response
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get, \
         patch("asyncio.sleep", new_callable=AsyncMock):
        
        mock_get.return_value = mock_response
        
        service = ImdbScraperService()
        reviews = await service.fetch_reviews("tt_yanlis_id")
        
        assert reviews == []