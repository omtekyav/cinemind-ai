"""
CineMind API Client
Streamlit UI'dan Backend'e istek atar.
"""

import os
import httpx
from typing import Optional, Dict, Any


# Environment'dan al, yoksa localhost (local dev için fallback)
DEFAULT_API_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


class CineMindClient:
    """Backend API ile iletişim kurar."""
    
    def __init__(self, base_url: str = DEFAULT_API_URL):
        self.base_url = base_url
        self.timeout = 60.0  # RAG sorguları uzun sürebilir
    
    def health_check(self) -> Dict[str, Any]:
        """Sistem sağlığını kontrol et."""
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{self.base_url}/api/v1/health")
                response.raise_for_status()
                return response.json()
        except httpx.RequestError as e:
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
            
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base_url}/api/v1/query",
                    json=payload
                )
                response.raise_for_status()
                return response.json()
        except httpx.RequestError as e:
            return {"error": True, "message": str(e)}
    
    def get_movie(self, movie_id: str) -> Dict[str, Any]:
        """Film detaylarını getir."""
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(
                    f"{self.base_url}/api/v1/movies/{movie_id}"
                )
                response.raise_for_status()
                return response.json()
        except httpx.RequestError as e:
            return {"error": True, "message": str(e)}
    
    def ingest(self, source: str, limit: int = 5) -> Dict[str, Any]:
        """Veri yükleme başlat."""
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(
                    f"{self.base_url}/api/v1/ingest",
                    json={"source": source, "limit": limit}
                )
                response.raise_for_status()
                return response.json()
        except httpx.RequestError as e:
            return {"error": True, "message": str(e)}