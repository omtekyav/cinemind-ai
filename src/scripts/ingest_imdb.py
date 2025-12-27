"""
IMDb Ingestion Script
IMDb'den film yorumlarını scrape eder.
"""
import asyncio
import logging
import sys
import os
from pathlib import Path

# Path ayarı: Proje kökünü Python path'ine ekle
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.services.ingestion_coordinator import IngestionCoordinator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """IMDb ingestion başlat."""
    logger.info("=" * 60)
    logger.info("🎬 IMDB INGESTION BAŞLADI")
    logger.info("=" * 60)
    logger.info("⚠️ Anti-bot: Her film arası 3sn bekleme aktif")
    logger.info("=" * 60)
    
    coordinator = IngestionCoordinator()
    
    try:
        # Seed listesindeki 3 filmi işle
        await coordinator.run_imdb_pipeline(limit=3)
        logger.info("🎉 İşlem tamamlandı.")
        
    except Exception as e:
        logger.error(f"❌ Kritik hata: {e}", exc_info=True)
        raise
    
    finally:
        coordinator.close()


if __name__ == "__main__":
    asyncio.run(main())