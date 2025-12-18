# TMDb Logic
"""
Application Layer: TMDb API Service
Handling TMDb API interactions properly mapped to domain models.
"""
import httpx
from typing import Optional, List
from aiolimiter import AsyncLimiter
import asyncio

# Config'ten anahtarları, Model'den boş kutuları alıyoruz
from src.infrastructure.config import get_settings
from src.domain.models import Movie, TMDbReview, DataSource

class TMDbService:
    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.TMDB_BASE_URL
        
        # ROADMAP HEDEFİ: Rate Limiting (Saniyede max 10 istek)
        self.rate_limiter = AsyncLimiter(max_rate=10, time_period=1.0)
        
        self.headers = {
            "Authorization": f"Bearer {self.settings.TMDB_API_KEY}",
            "accept": "application/json"
        }
        self.default_params = {"language": "tr-TR"}
    
    async def _request(self, endpoint: str, params: dict = None) -> Optional[dict]:
        """Tüm isteklerin geçtiği ana kapı."""
        if params is None: params = {}
        params = {**self.default_params, **params}
        
        # Limiter kapısı
        async with self.rate_limiter:
            try:
                # Tarayıcıyı aç (Client) ve iş bitince kapat (Context Manager)
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(
                        f"{self.base_url}{endpoint}",
                        headers=self.headers,
                        params=params
                    )
                    # Hata varsa (404, 500) sessiz kalma, patlat ki yakalayalım
                    response.raise_for_status()
                    return response.json()
            except Exception as e:
                print(f"⚠️ TMDb Error ({endpoint}): {e}")
                return None
    
    async def search_movie(self, query: str) -> Optional[int]:
        """İsimden arama yapar, ID döner."""
        data = await self._request("/search/movie", {"query": query})
        if data and data.get("results"):
            return data["results"][0]["id"]
        return None
    
    async def get_movie(self, tmdb_id: int) -> Optional[Movie]:
        """API'den JSON alır, 'Movie' modeline çevirir."""
        # Yönetmen için credits ekle
        data = await self._request(f"/movie/{tmdb_id}", {"append_to_response": "credits"})
        if not data: return None
        
        # 1. Yönetmeni Bul
        director = "Unknown"
        if "credits" in data and "crew" in data["credits"]:
            for person in data["credits"]["crew"]:
                if person.get("job") == "Director":
                    director = person.get("name")
                    break
        
        # 2. Slug ID Oluştur (the-dark-knight-2008)
        title_slug = data.get("title", "").lower().replace(" ", "-").replace(":", "")
        year_str = data.get("release_date", "")[:4] if data.get("release_date") else ""
        movie_slug = f"{title_slug}-{year_str}" if year_str else title_slug
        
        # 3. Poster URL
        poster_url = None
        if data.get("poster_path"):
            poster_url = f"https://image.tmdb.org/t/p/w500{data['poster_path']}"
        
        # 4. Modeli Doldur
        return Movie(
            movie_id=movie_slug,    
            title=data.get("title"),
            director=director,
            year=int(year_str) if year_str else None,
            genres=[g["name"] for g in data.get("genres", [])],
            rating=data.get("vote_average"),
            synopsis=data.get("overview"),
            poster_url=poster_url,
            runtime=data.get("runtime")
        )

    async def get_reviews(self, tmdb_id: int, max_pages: int = 3) -> List[TMDbReview]:
        """Yorumları çeker ve 'TMDbReview' modeline çevirir."""
        reviews = []
        for page in range(1, max_pages + 1):
            data = await self._request(f"/movie/{tmdb_id}/reviews", {"page": page})
            if not data or not data.get("results"): break
            
            for item in data["results"]:
                if not item.get("content"): continue
                
                reviews.append(TMDbReview(
                    review_id=item["id"],
                    movie_id=str(tmdb_id),
                    author=item["author"],
                    rating=item.get("author_details", {}).get("rating"),
                    text=item["content"],
                    source=DataSource.TMDB
                ))
            
            if page >= data.get("total_pages", 0): break
        return reviews

# Singleton
tmdb_service = TMDbService()