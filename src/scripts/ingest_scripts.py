"""
Script Ingestion
PDF senaryo dosyalarını işler.
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
    """Script ingestion başlat."""
    logger.info("=" * 60)
    logger.info("🎬 SCRIPT INGESTION BAŞLADI")
    logger.info("=" * 60)
    logger.info(f"Senaryo Klasörü: data/scripts/")
    logger.info("=" * 60)
    
    coordinator = IngestionCoordinator()
    
    try:
        await coordinator.run_script_pipeline()
        logger.info("🎉 İşlem tamamlandı.")
        
    except Exception as e:
        logger.error(f"❌ Kritik hata: {e}", exc_info=True)
        raise
    
    finally:
        coordinator.close()


if __name__ == "__main__":
    asyncio.run(main())