import pytest
from unittest.mock import AsyncMock, MagicMock
from src.services.tmdb_service import TMDbService
from src.domain.models import Movie, TMDbReview

# Testlerde gerçek bir Service örneği kullanacağız
# Ama HTTP isteklerini engelleyeceğiz (Mocking)
@pytest.fixture
def service():
    return TMDbService()

@pytest.mark.asyncio
async def test_search_movie_success(service, mocker):
    """
    Senaryo: Başarılı bir arama isteği.
    Beklenen: Filmin ID'sinin (int) dönmesi.
    """
    # 1. SAHTE CEVAP HAZIRLA
    mock_response = {
        "results": [{"id": 155, "title": "The Dark Knight"}]
    }
    
    # 2. _request METODUNU MOCKLA (Daha kolay yöntem)
    # Service'in internete çıkan kapısını (_request) taklit ediyoruz.
    mocker.patch.object(service, '_request', return_value=mock_response)

    # 3. AKSİYON
    result = await service.search_movie("The Dark Knight")

    # 4. KONTROL (ASSERTION)
    assert result == 155
    # _request'in doğru parametrelerle çağrılıp çağrılmadığını kontrol et
    service._request.assert_called_with("/search/movie", {"query": "The Dark Knight"})

@pytest.mark.asyncio
async def test_search_movie_empty(service, mocker):
    """
    Senaryo: Arama sonucu boş dönerse.
    Beklenen: None dönmesi.
    """
    mocker.patch.object(service, '_request', return_value={"results": []})
    
    result = await service.search_movie("Bilinmeyen Film 123")
    assert result is None

@pytest.mark.asyncio
async def test_get_movie_details_success(service, mocker):
    """
    Senaryo: Başarılı film detayı ve Credits çekimi.
    Beklenen: Dolu bir Movie objesi.
    """
    # 1. SAHTE API CEVABI (Hem detay hem credits içerir)
    mock_data = {
        "id": 155,
        "title": "The Dark Knight",
        "release_date": "2008-07-16",
        "genres": [{"name": "Action"}, {"name": "Crime"}],
        "vote_average": 9.0,
        "overview": "Batman fights Joker.",
        "poster_path": "/poster.jpg",
        "runtime": 152,
        "credits": {
            "crew": [
                {"job": "Director", "name": "Christopher Nolan"},
                {"job": "Producer", "name": "Emma Thomas"}
            ]
        }
    }
    
    mocker.patch.object(service, '_request', return_value=mock_data)

    # 2. AKSİYON
    movie = await service.get_movie(155)

    # 3. KONTROL
    assert isinstance(movie, Movie)
    assert movie.title == "The Dark Knight"
    assert movie.year == 2008
    assert movie.director == "Christopher Nolan"  # Credits'ten çekilen veri
    assert movie.movie_id == "the-dark-knight-2008"  # Slug mantığı
    assert str(movie.poster_url) == "https://image.tmdb.org/t/p/w500/poster.jpg"

@pytest.mark.asyncio
async def test_get_movie_not_found(service, mocker):
    """
    Senaryo: API boş cevap dönerse veya 404 alırsa.
    Beklenen: None.
    """
    # _request metodunun None döndüğünü simüle edelim (Hata durumunda None döner)
    mocker.patch.object(service, '_request', return_value=None)
    
    movie = await service.get_movie(999999)
    assert movie is None

@pytest.mark.asyncio
async def test_get_reviews_success(service, mocker):
    """
    Senaryo: Başarılı yorum çekimi.
    Beklenen: TMDbReview listesi.
    """
    mock_data = {
        "results": [
            {
                "id": "review1",
                "author": "user1",
                "content": "Great movie!",
                "author_details": {"rating": 10.0}
            }
        ],
        "total_pages": 1
    }
    
    mocker.patch.object(service, '_request', return_value=mock_data)

    reviews = await service.get_reviews(155)

    assert len(reviews) == 1
    assert isinstance(reviews[0], TMDbReview)
    assert reviews[0].author == "user1"
    assert reviews[0].rating == 10.0
    assert reviews[0].movie_id == "155"

# --- ERROR HANDLING TESTİ (Derinlemesine) ---
@pytest.mark.asyncio
async def test_http_exception_handling(service, mocker):
    """
    Senaryo: _request metodunun kendisinin hata yönetimi.
    Bu testte direkt service._request'i değil, onun içindeki httpx'i mockluyoruz.
    Amacımız: try/except bloğunun çalışıp çalışmadığını görmek.
    """
    # httpx.AsyncClient().get() metodunu patlatacağız
    # Bu biraz karmaşık bir mock, çünkü Context Manager (async with) var.
    
    # 1. Mock Client Oluştur
    mock_client = AsyncMock()
    # get metodu bir hata fırlatsın (örn: Bağlantı hatası)
    mock_client.get.side_effect = Exception("Connection Error")

    # 2. httpx.AsyncClient'ın bu mock_client'ı dönmesini sağla
    # Service dosyasındaki 'httpx' modülünü patchliyoruz
    mocker.patch("src.services.tmdb_service.httpx.AsyncClient", return_value=mock_client)
    
    # Context manager (__aenter__) mocklaması
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    # 3. Aksiyon
    # _request metodu hatayı yakalayıp ekrana basmalı ve None dönmeli
    result = await service._request("/test-endpoint")
    
    assert result is None