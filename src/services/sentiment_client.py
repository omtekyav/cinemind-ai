# Sentiment Client
import os
import logging
import requests
from requests import Response
from typing import List, Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

# Logger yapılandırması
logger = logging.getLogger(__name__)

def _should_retry(exc: Exception) -> bool:
    """
    Retry Stratejisi:
    - Connection/Timeout: EVET
    - HTTP 5xx: EVET
    - HTTP 4xx: HAYIR
    """
    if isinstance(exc, requests.Timeout):
        return True
    if isinstance(exc, requests.ConnectionError):
        return True
    if isinstance(exc, requests.HTTPError):
        resp: Optional[Response] = getattr(exc, "response", None)
        if resp is not None and 500 <= resp.status_code < 600:
            return True
    return False

class SentimentClient:
    MAX_BATCH_SIZE = 100  # Servis limiti
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout_seconds: int = 45,
        fail_open: bool = True,
    ):
        # URL'i çevresel değişkenden al (Docker dostu)
        self.base_url = base_url or os.getenv("SENTIMENT_SERVICE_URL", "http://localhost:8000")
        self.base_url = self.base_url.rstrip("/")
        self.batch_url = f"{self.base_url}/api/v1/analyze-batch"
        self.health_url = f"{self.base_url}/health"

        self.timeout_seconds = timeout_seconds
        self.fail_open = fail_open 

        # Connection Pooling (Performans artışı)
        self.session = requests.Session()

    def close(self):
        """Client kapatıldığında session'ı temizle."""
        self.session.close()
        logger.debug("Session kapatıldı.")

    def __enter__(self):
        """Context manager desteği."""
        return self

    def __exit__(self, *args):
        """Context manager çıkışında session'ı kapat."""
        self.close()

    def check_health(self) -> bool:
        """Servis ayakta mı kontrol et (opsiyonel, debugging için)."""
        try:
            r = self.session.get(self.health_url, timeout=2)
            return r.status_code == 200
        except requests.RequestException:
            logger.warning(f"Sentiment servisine ulaşılamıyor ({self.base_url}).")
            return False

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception(_should_retry),
        reraise=True,
    )
    def _send_batch(self, texts: List[str]) -> List[Dict[str, Any]]:
        """Tek batch'i servise gönder (retry mantığı burada)."""
        payload = {"texts": texts}
        
        r = self.session.post(self.batch_url, json=payload, timeout=self.timeout_seconds)

        try:
            r.raise_for_status()
        except requests.HTTPError as e:
            # 4xx hatalar WARNING (client hatası, retry edilmez)
            if 400 <= r.status_code < 500:
                logger.warning(f"Client hatası: {r.status_code} - Body: {r.text[:200]}")
            else:
                logger.error(f"Server hatası: {r.status_code} - Body: {r.text[:200]}")
            raise 

        data = r.json()
        results = data.get("results", [])
        
        if not isinstance(results, list):
            raise ValueError("Servisten beklenmeyen format: 'results' bir liste değil.")

        return results

    def analyze_batch(self, texts: List[str], batch_size: int = 32) -> List[Dict[str, Any]]:
        """
        Büyük listeyi parçalar, yönetir ve hataları tolere eder.
        
        Args:
            texts: Analiz edilecek metinler
            batch_size: Her seferde kaç metin gönderilecek (max 100)
            
        Returns:
            Her metin için sentiment sonucu (başarısızlıkta Nötr döner)
        """
        if not texts:
            return []

        # Batch size validasyonu
        if not 0 < batch_size <= self.MAX_BATCH_SIZE:
            raise ValueError(f"Batch size 1-{self.MAX_BATCH_SIZE} arasında olmalı. Gelen: {batch_size}")

        all_results: List[Dict[str, Any]] = []
        total = len(texts)
        logger.info(f"Toplam {total} metin analiz edilecek. Batch size: {batch_size}")

        for i in range(0, total, batch_size):
            chunk = texts[i : i + batch_size]
            chunk_norm = [("" if t is None else str(t)) for t in chunk]

            try:
                batch_results = self._send_batch(chunk_norm)

                # Gelen/giden uzunluk kontrolü
                if len(batch_results) != len(chunk_norm):
                    logger.error(
                        f"Mismatch! Giden: {len(chunk_norm)}, Gelen: {len(batch_results)}. "
                        "Eksikler Nötr ile dolduruluyor."
                    )
                    while len(batch_results) < len(chunk_norm):
                        batch_results.append({"sentiment": "Nötr", "confidence": 0.0})
                    batch_results = batch_results[:len(chunk_norm)]

                all_results.extend(batch_results)
                logger.info(f"{min(i + batch_size, total)}/{total} işlendi.")

            except (requests.RequestException, ValueError, KeyError) as e:
                # Beklenen hatalar: Network, JSON parse, key eksikliği
                logger.warning(f"Batch {i}-{min(i+batch_size, total)} başarısız: {e}. Nötr atanıyor.")
                
                if not self.fail_open:
                    logger.error("Fail-open kapalı, hata yukarı fırlatılıyor.")
                    raise
                    
                all_results.extend([{"sentiment": "Nötr", "confidence": 0.0} for _ in chunk_norm])
                
            except Exception as e:
                # Beklenmeyen kritik hatalar (memory, assertion vb.)
                logger.critical(f"Kritik hata (Batch {i}): {e}. Pipeline durduruluyor.")
                raise

        logger.info(f"Tüm batch işlemi tamamlandı. Toplam sonuç: {len(all_results)}")
        return all_results