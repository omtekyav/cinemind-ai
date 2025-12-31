"""
CineMind API Client
Streamlit UI'dan Backend'e istek atar.
"""
import requests
from typing import Optional, Dict, Any


class CineMindClient:
    """Backend API ile iletişim kurar."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.timeout = 60  # RAG sorguları uzun sürebilir
    
    def health_check(self) -> Dict[str, Any]:
        """Sistem sağlığını kontrol et."""
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/health",
                timeout=5
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"status": "error", "message": str(e)}
    
    def query(
        self, 
        question: str, 
        source_filter: Optional[str] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """RAG sorgusu gönder."""
        try:
            payload = {
                "question": question,
                "limit": limit
            }
            if source_filter:
                payload["source_filter"] = source_filter
            
            response = requests.post(
                f"{self.base_url}/api/v1/query",
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": True, "message": str(e)}
    
    def get_movie(self, movie_id: str) -> Dict[str, Any]:
        """Film detaylarını getir."""
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/movies/{movie_id}",
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": True, "message": str(e)}
    
    def ingest(self, source: str, limit: int = 5) -> Dict[str, Any]:
        """Veri yükleme başlat."""
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/ingest",
                json={"source": source, "limit": limit},
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": True, "message": str(e)}