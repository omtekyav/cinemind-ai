import pytest
from src.services.tmdb_service import TMDbService

# DİKKAT: Bu testler MOCK DEĞİLDİR.
# Gerçek API isteği atar. İnternet ve API Key şarttır.

@pytest.fixture
def service():
    return TMDbService()

@pytest.mark.asyncio
async def test_real_connection_to_tmdb(service):
    """
    GERÇEK ENTEGRASYON TESTİ
    Amaç: API Key geçerli mi ve TMDb sunucularına ulaşabiliyor muyuz?
    """
    print("\n🌍 TMDb'ye gerçek istek atılıyor...")
    
    # 1. Gerçek Arama Yap ("Inception")
    movie_id = await service.search_movie("Inception")
    
    # 2. Kontrol Et
    # Inception'ın ID'si 27205'tir. 
    # Eğer bu ID geliyorsa; internet var, key doğru, kod çalışıyor demektir.
    assert movie_id is not None
    assert movie_id == 27205
    print("✅ Bağlantı Başarılı! Inception ID'si doğrulandı.")

@pytest.mark.asyncio
async def test_real_movie_details(service):
    """
    GERÇEK DETAY ÇEKİMİ
    Amaç: Gelen JSON verisi bizim Movie modelimize sorunsuz dönüşüyor mu?
    """
    # The Dark Knight (ID: 155)
    movie = await service.get_movie(155)
    
    assert movie is not None
    assert movie.title == "Kara Şövalye"
    assert movie.director == "Christopher Nolan"
    # URL string kontrolü
    assert "image.tmdb.org" in str(movie.poster_url)
    print("✅ Veri Modeli Doğrulandı! The Dark Knight verileri sağlam.")