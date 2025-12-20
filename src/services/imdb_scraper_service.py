# IMDb Logic
import httpx
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from typing import List, Dict, Optional, Union
import logging
import asyncio
import random

# Loglama yapılandırması
logger = logging.getLogger(__name__)

class ImdbScraperService:
    def __init__(self):
        # Fallback: DB erişimi olmazsa default chrome kullan
        self.ua = UserAgent(fallback='chrome')
        self.base_url = "https://www.imdb.com"
    
    def _get_headers(self) -> dict:
        """
        Bot korumasını (403 Forbidden) aşmak için her istekte
        farklı bir tarayıcı kimliği (User-Agent) üretir.
        """
        return {
            "User-Agent": self.ua.random,
            "Accept-Language": "en-US,en;q=0.9",  # İngilizce içerik zorlama
            "Referer": "https://www.google.com/"
        }
    
    async def fetch_reviews(
        self, 
        imdb_id: str, 
        max_reviews: int = 5
    ) -> List[Dict[str, Optional[Union[str, float]]]]:
        """
        IMDb'den belirtilen film için yorum ve puan verilerini çeker.
        
        Args:
            imdb_id: Filmin ID'si (örn: tt0468569)
            max_reviews: Çekilecek maksimum yorum sayısı
            
        Returns:
            List[Dict]: Yapısal veri döner (title, content, rating, source)
        """
        url = f"{self.base_url}/title/{imdb_id}/reviews"
        
        # RATE LIMITING: Ardışık isteklerde IP ban yememek için bekleme
        wait_time = random.uniform(2, 4)
        logger.info(f"⏳ Rate limit beklemesi: {wait_time:.2f}s - {imdb_id}")
        await asyncio.sleep(wait_time)
        
        async with httpx.AsyncClient() as client:
            try:
                # Timeout 10s: Scraping işlemleri API'ye göre daha yavaş olabilir
                response = await client.get(
                    url, 
                    headers=self._get_headers(), 
                    follow_redirects=True,
                    timeout=10.0
                )
                response.raise_for_status()
                
                return self._parse_html(response.text, max_reviews)
                
            except httpx.HTTPStatusError as e:
                logger.error(f"❌ HTTP Hatası {e.response.status_code}: {imdb_id}")
                return []
            except httpx.RequestError as e:
                logger.error(f"❌ Network Hatası: {str(e)}")
                return []
            except Exception as e:
                logger.error(f"❌ Beklenmeyen hata: {str(e)}")
                return []
    
    def _parse_html(self, html_content: str, limit: int) -> List[Dict]:
        """
        Ham HTML içeriğini parse eder ve Dictionary listesi döndürür.
        """
        # Standart python parser kullanıyoruz (ekstra kütüphane gerekmez)
        soup = BeautifulSoup(html_content, "html.parser")
        reviews = []
        
        # IMDb CSS Selector'ları (Kırılgan nokta)
        containers = soup.select(".review-container")
        
        for container in containers[:limit]:
            try:
                # 1. BAŞLIK
                title_tag = container.select_one("a.title")
                title = title_tag.get_text(strip=True) if title_tag else "No Title"
                
                # 2. İÇERİK
                # <br> taglerini boşlukla değiştirerek metni birleştirir
                content_tag = container.select_one(".text.show-more__control")
                content = content_tag.get_text(separator=" ", strip=True) if content_tag else ""
                
                # 3. RATING (Puan verilmeyen yorumlar olabilir)
                rating = None
                rating_tag = container.select_one(".rating-other-user-rating span")
                if rating_tag:
                    try:
                        # Örn: "8/10" -> "8" -> 8.0
                        raw = rating_tag.get_text(strip=True)
                        rating = float(raw.split("/")[0])
                    except (ValueError, IndexError):
                        pass 
                
                reviews.append({
                    "source": "imdb",
                    "title": title,
                    "rating": rating,
                    "content": content
                })
                
            except Exception as e:
                logger.warning(f"⚠️ Parse hatası (atlandı): {e}")
                continue
        
        logger.info(f"✅ {len(reviews)} yorum başarıyla çekildi.")
        return reviews

