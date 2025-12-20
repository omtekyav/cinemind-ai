import logging
from typing import List, Dict, Any
from pathlib import Path
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class ScriptChunk:
    """Senaryonun bir parçası (chunk) ve ilişkili metadata verisi."""
    content: str
    metadata: Dict[str, Any]

class PdfParserService:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Args:
            chunk_size: Her parçanın hedef karakter uzunluğu.
            chunk_overlap: Parçalar arası örtüşme (bağlam kopmaması için).
        """
        # Senaryo formatına özel ayırıcılar (Önce sahne başlıkları, sonra paragraflar)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["INT.", "EXT.", "\n\n", "\n", " ", ""],
            length_function=len,
        )

    def load_and_split(self, file_path: str, movie_id: str) -> List[Dict[str, Any]]:
        """
        PDF dosyasını okur, metni sahnere/diyaloglara göre böler.

        Args:
            file_path: Script PDF dosyasının yolu.
            movie_id: Chunk'ların hangi filme ait olduğunu belirten ID.

        Returns:
            List[Dict]: Veritabanına yazılmaya hazır chunk listesi.
        """
        pdf_path = Path(file_path)
        
        # 1. Dosya Kontrolü (Validation)
        if not pdf_path.exists():
            logger.error(f"❌ Dosya bulunamadı: {file_path}")
            return []

        try:
            # 2. PDF'ten Ham Metni Çek
            raw_text = self._extract_text_from_pdf(file_path)
            
            if not raw_text.strip():
                logger.warning(f"⚠️ PDF içeriği boş: {file_path}")
                return []

            # 3. Metni Akıllı Böl (Chunking)
            chunks = self.text_splitter.create_documents([raw_text])
            
            # 4. Metadata ile Paketle
            processed_chunks = []
            total_chunks = len(chunks)
            
            for i, chunk in enumerate(chunks):
                chunk_data = ScriptChunk(
                    content=chunk.page_content,
                    metadata={
                        "source": "script",
                        "movie_id": movie_id,
                        "chunk_index": i,           # Sıralama için önemli
                        "total_chunks": total_chunks,
                        "file_name": pdf_path.name
                    }
                )
                processed_chunks.append(asdict(chunk_data))

            logger.info(f"✅ İşlem Başarılı: {pdf_path.name} -> {total_chunks} parça oluşturuldu.")
            return processed_chunks

        except Exception as e:
            logger.error(f"❌ PDF parse hatası ({file_path}): {str(e)}")
            return []

    def _extract_text_from_pdf(self, file_path: str) -> str:
        """
        pypdf kullanarak dosyadaki metni çıkarır.
        """
        text = ""
        try:
            reader = PdfReader(file_path)
            for page_num, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
                else:
                    logger.debug(f"Sayfa {page_num + 1} boş veya okunamadı: {file_path}")
            return text
        except Exception as e:
            logger.error(f"PDF okuma alt seviye hatası: {e}")
            raise e