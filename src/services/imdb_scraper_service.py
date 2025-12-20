# src/services/imdb_scraper_service.py

import httpx
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from typing import List, Dict, Optional, Union
import logging
import asyncio
import random

logger = logging.getLogger(__name__)

class ImdbScraperService:
    def __init__(self):
        """
        IMDb scraper servisi.
        Bot korumasını aşmak için UserAgent rotasyonu kullanır.
        """
        self.ua = UserAgent(fallback='chrome')
        self.base_url = "https://www.imdb.com"
    
    def _get_headers(self) -> dict:
        """
        Her istekte farklı tarayıcı kimliği (User-Agent) üretir.
        IMDb'nin bot tespitini atlatmak için gerekli.
        """
        return {
            "User-Agent": self.ua.random,
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.google.com/"
        }
    
    async def fetch_reviews(
        self, 
        imdb_id: str, 
        max_reviews: int = 5
    ) -> List[Dict[str, Optional[Union[str, float]]]]:
        """
        Belirtilen IMDb ID için kullanıcı yorumlarını çeker.
        
        Args:
            imdb_id: Filmin IMDb ID'si (örn: "tt0468569")
            max_reviews: Çekilecek maksimum yorum sayısı
            
        Returns:
            List[Dict]: Her yorum {"source": "imdb", "title": str, 
                        "rating": float|None, "content": str} formatında
        """
        url = f"{self.base_url}/title/{imdb_id}/reviews"
        
        # Rate limiting: IP ban önleme
        wait_time = random.uniform(2, 4)
        logger.info(f"⏳ Rate limit beklemesi: {wait_time:.2f}s - {imdb_id}")
        await asyncio.sleep(wait_time)
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    url, 
                    headers=self._get_headers(), 
                    follow_redirects=True,
                    timeout=10.0
                )
                response.raise_for_status()
                
                return self._parse_html(response.text, max_reviews)
                
            except httpx.HTTPStatusError as e:
                logger.error(f"❌ HTTP {e.response.status_code}: {imdb_id}")
                return []
            except httpx.RequestError as e:
                logger.error(f"❌ Network hatası: {str(e)}")
                return []
            except Exception as e:
                logger.error(f"❌ Beklenmeyen hata: {str(e)}")
                return []
    
    def _parse_html(self, html_content: str, limit: int) -> List[Dict]:
        """
        HTML içeriğinden yorum verilerini parse eder.
        IMDb'nin 2024 HTML yapısına göre güncellenmiştir.
        """
        soup = BeautifulSoup(html_content, "lxml")
        reviews = []
        
        # IMDb 2024 yapısı: <article class="user-review-item">
        containers = soup.select("article.user-review-item")
        logger.info(f"🔍 {len(containers)} yorum container bulundu")
        
        for container in containers[:limit]:
            try:
                # 1. TITLE - Yorum başlığı
                title_tag = container.select_one("h3.ipc-title__text")
                title = title_tag.get_text(strip=True) if title_tag else "No Title"
                
                # 2. CONTENT - Yorum metni
                content_tag = container.select_one(".ipc-html-content-inner-div")
                content = content_tag.get_text(separator=" ", strip=True) if content_tag else ""
                
                # 3. RATING - Kullanıcı puanı (opsiyonel)
                rating = None
                rating_tag = container.select_one(".ipc-rating-star--rating")
                if rating_tag:
                    try:
                        raw = rating_tag.get_text(strip=True)  # "10" veya "9"
                        rating = float(raw)
                    except (ValueError, IndexError):
                        pass
                
                # Boş içerik kontrolü
                if not content or len(content) < 20:
                    logger.debug(f"⚠️ Boş içerik atlandı: {title}")
                    continue
                
                reviews.append({
                    "source": "imdb",
                    "title": title,
                    "rating": rating,
                    "content": content
                })
                
                logger.debug(f"✅ Parse: {title[:40]}... (Rating: {rating})")
                
            except Exception as e:
                logger.warning(f"⚠️ Parse hatası (atlandı): {e}")
                continue
        
        logger.info(f"✅ Toplam {len(reviews)} yorum başarıyla parse edildi")
        return reviews