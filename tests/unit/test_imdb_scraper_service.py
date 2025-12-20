import pytest
from unittest.mock import Mock, patch, AsyncMock
import httpx
from src.services.imdb_scraper_service import ImdbScraperService

# --- UPDATED MOCK HTML (IMDb 2024 yapısına uygun) ---
MOCK_HTML_CONTENT = """
<html>
<body>
    <article class="sc-bb1e1e59-1 gtpcFu user-review-item">
        <div class="ipc-list-card__content">
            <span class="ipc-rating-star--rating">10</span>
            <h3 class="ipc-title__text">Mükemmel Bir Film</h3>
            <div class="ipc-html-content-inner-div">
                Bu film sinema tarihinin en iyisidir. Kesinlikle izleyin.
            </div>
        </div>
    </article>
    
    <article class="user-review-item">
        <h3 class="ipc-title__text">Fena Değil</h3>
        <div class="ipc-html-content-inner-div">
            Ortalama bir filmdi.
        </div>
    </article>
</body>
</html>
"""

@pytest.mark.asyncio
async def test_fetch_reviews_success():
    """
    SENARYO 1: Başarılı Scraping İşlemi
    """
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = MOCK_HTML_CONTENT
    mock_response.raise_for_status = Mock()

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get, \
         patch("asyncio.sleep", new_callable=AsyncMock):
        
        mock_get.return_value = mock_response
        
        service = ImdbScraperService()
        reviews = await service.fetch_reviews("tt_dummy_id", max_reviews=5)

        # Doğrulamalar
        assert len(reviews) == 2, "2 adet yorum çekilmeliydi"
        
        # Yorum 1 (tam veri)
        review1 = reviews[0]
        assert review1["title"] == "Mükemmel Bir Film"
        assert review1["rating"] == 10.0  # Artık float olarak direkt
        assert "sinema tarihinin" in review1["content"]
        assert review1["source"] == "imdb"
        
        # Yorum 2 (eksik rating)
        review2 = reviews[1]
        assert review2["title"] == "Fena Değil"
        assert review2["rating"] is None
        assert "Ortalama" in review2["content"]

@pytest.mark.asyncio
async def test_fetch_reviews_network_error():
    """
    SENARYO 2: Network Hatası
    """
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get, \
         patch("asyncio.sleep", new_callable=AsyncMock):
        
        mock_get.side_effect = httpx.RequestError("Bağlantı koptu")
        
        service = ImdbScraperService()
        reviews = await service.fetch_reviews("tt_dummy_id")
        
        assert reviews == []
        assert isinstance(reviews, list)

@pytest.mark.asyncio
async def test_fetch_reviews_http_error():
    """
    SENARYO 3: HTTP 404 Hatası
    """
    mock_response = Mock()
    mock_response.status_code = 404
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Not Found", request=Mock(), response=mock_response
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get, \
         patch("asyncio.sleep", new_callable=AsyncMock):
        
        mock_get.return_value = mock_response
        
        service = ImdbScraperService()
        reviews = await service.fetch_reviews("tt_yanlis_id")
        
        assert reviews == []

@pytest.mark.asyncio
async def test_empty_content_filtering():
    """
    SENARYO 4: Boş İçerik Filtresi
    Beklenti: 20 karakterden kısa yorumlar atlanmalı
    """
    mock_html = """
    <html>
    <body>
        <article class="user-review-item">
            <h3 class="ipc-title__text">Test</h3>
            <div class="ipc-html-content-inner-div">Kısa</div>
        </article>
        <article class="user-review-item">
            <h3 class="ipc-title__text">Valid Review</h3>
            <div class="ipc-html-content-inner-div">
                Bu yeterince uzun bir yorum metnidir ve parse edilmelidir.
            </div>
        </article>
    </body>
    </html>
    """
    
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = mock_html
    mock_response.raise_for_status = Mock()

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get, \
         patch("asyncio.sleep", new_callable=AsyncMock):
        
        mock_get.return_value = mock_response
        
        service = ImdbScraperService()
        reviews = await service.fetch_reviews("tt_test", max_reviews=10)
        
        # Sadece ikinci yorum (uzun olan) dönmeli
        assert len(reviews) == 1
        assert reviews[0]["title"] == "Valid Review"