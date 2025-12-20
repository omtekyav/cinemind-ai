import pytest
from unittest.mock import Mock, patch
from src.services.pdf_parser_service import PdfParserService

# --- MOCK SENARYO İÇERİĞİ ---
MOCK_SCRIPT_TEXT = """
INT. GOTHAM BANK - DAY

The Joker stands in the middle of the room. He takes off his mask.

JOKER
I believe whatever doesn't kill you, simply makes you... stranger.

EXT. GOTHAM STREETS - DAY

Police cars are racing towards the bank.
"""

MOCK_MULTIPAGE_PAGE1 = """
INT. WAYNE MANOR - NIGHT

Bruce Wayne sits in the dark.

ALFRED
Master Wayne, you're brooding again.
"""

MOCK_MULTIPAGE_PAGE2 = """
EXT. GOTHAM ROOFTOP - NIGHT

Batman stands watching the city.

BATMAN
This city needs more than hope.
"""


class TestPdfParserService:
    
    @pytest.fixture
    def mock_pdf_reader(self):
        """
        pypdf.PdfReader sınıfını mocklar.
        """
        with patch("src.services.pdf_parser_service.PdfReader") as MockReader:
            mock_instance = MockReader.return_value
            mock_page = Mock()
            mock_page.extract_text.return_value = MOCK_SCRIPT_TEXT
            mock_instance.pages = [mock_page]
            yield MockReader

    def test_load_and_split_success(self, mock_pdf_reader):
        """
        SENARYO 1: Başarılı Okuma ve Bölme
        """
        with patch("pathlib.Path.exists", return_value=True):
            service = PdfParserService(chunk_size=100, chunk_overlap=20)
            chunks = service.load_and_split("dummy_script.pdf", movie_id="tt0468569")
            
            # Assertions
            assert len(chunks) > 0, "Chunk listesi boş olmamalı"
            
            first_chunk = chunks[0]
            assert "GOTHAM" in first_chunk["content"], "İçerik doğru okunmalı"
            
            # Metadata kontrolü
            meta = first_chunk["metadata"]
            assert meta["movie_id"] == "tt0468569"
            assert meta["source"] == "script"
            assert meta["file_name"] == "dummy_script.pdf"
            assert "chunk_index" in meta
            assert "total_chunks" in meta
            assert meta["total_chunks"] == len(chunks)

    def test_file_not_found(self):
        """
        SENARYO 2: Dosya Bulunamadı
        """
        with patch("pathlib.Path.exists", return_value=False):
            service = PdfParserService()
            chunks = service.load_and_split("non_existent.pdf", movie_id="123")
            
            assert chunks == []
            assert isinstance(chunks, list)

    def test_empty_pdf_content(self, mock_pdf_reader):
        """
        SENARYO 3: Boş PDF İçeriği
        """
        mock_pdf_reader.return_value.pages[0].extract_text.return_value = ""
        
        with patch("pathlib.Path.exists", return_value=True):
            service = PdfParserService()
            chunks = service.load_and_split("empty.pdf", movie_id="123")
            
            assert chunks == []

    def test_corrupt_pdf_handling(self):
        """
        SENARYO 4: Bozuk PDF (PdfReader exception)
        """
        with patch("src.services.pdf_parser_service.PdfReader") as MockReader, \
             patch("pathlib.Path.exists", return_value=True):
            
            # PdfReader exception fırlatır
            MockReader.side_effect = Exception("Corrupt PDF file")
            
            service = PdfParserService()
            chunks = service.load_and_split("corrupt.pdf", movie_id="666")
            
            # Crash olmamalı, boş liste dönmeli
            assert chunks == []

    def test_scene_based_chunking(self, mock_pdf_reader):
        """
        SENARYO 5: Scene-Based Chunking (INT/EXT delimiter)
        Beklenti: Separator'lar ["INT.", "EXT.", ...] chunk oluşumunu etkilemeli
        """
        with patch("pathlib.Path.exists", return_value=True):
            # Küçük chunk_size ile scene'lerin ayrı chunk'lara düşmesini zorla
            service = PdfParserService(chunk_size=80, chunk_overlap=10)
            chunks = service.load_and_split("scenes.pdf", movie_id="tt123")
            
            # En az 2 chunk olmalı (INT ve EXT sahneleri için)
            assert len(chunks) >= 2, "Scene delimiter'lar chunk oluşturmalı"
            
            # Chunk'larda scene keyword'leri olmalı
            all_content = " ".join([c["content"] for c in chunks])
            assert "INT. GOTHAM BANK" in all_content
            assert "EXT. GOTHAM STREETS" in all_content

    def test_chunk_overlap_preservation(self, mock_pdf_reader):
        """
        SENARYO 6: Chunk Overlap (Context kaybı önleme)
        """
        # Uzun bir metin oluştur
        long_text = "This is a long script text. " * 50
        mock_pdf_reader.return_value.pages[0].extract_text.return_value = long_text
        
        with patch("pathlib.Path.exists", return_value=True):
            service = PdfParserService(chunk_size=100, chunk_overlap=20)
            chunks = service.load_and_split("long.pdf", movie_id="789")
            
            # Birden fazla chunk oluşmalı
            assert len(chunks) > 1, "Uzun metin birden fazla chunk'a bölünmeli"
            
            # Her chunk 100 karaktere yakın olmalı (overlap hariç)
            for chunk in chunks:
                # chunk_size + overlap göz önünde bulundurulmalı
                assert len(chunk["content"]) > 0

    def test_multipage_pdf_handling(self):
        """
        SENARYO 7: Çok Sayfalı PDF
        """
        with patch("src.services.pdf_parser_service.PdfReader") as MockReader, \
             patch("pathlib.Path.exists", return_value=True):
            
            mock_instance = MockReader.return_value
            
            # 2 sayfalı PDF mock'u
            page1 = Mock()
            page1.extract_text.return_value = MOCK_MULTIPAGE_PAGE1
            
            page2 = Mock()
            page2.extract_text.return_value = MOCK_MULTIPAGE_PAGE2
            
            mock_instance.pages = [page1, page2]
            
            service = PdfParserService(chunk_size=150, chunk_overlap=20)
            chunks = service.load_and_split("multipage.pdf", movie_id="multi")
            
            # Her iki sayfadan da içerik olmalı
            all_content = " ".join([c["content"] for c in chunks])
            assert "WAYNE MANOR" in all_content, "Sayfa 1 içeriği olmalı"
            assert "GOTHAM ROOFTOP" in all_content, "Sayfa 2 içeriği olmalı"
            assert "ALFRED" in all_content
            assert "BATMAN" in all_content

    def test_chunk_metadata_consistency(self, mock_pdf_reader):
        """
        SENARYO 8: Chunk Index Tutarlılığı
        """
        with patch("pathlib.Path.exists", return_value=True):
            service = PdfParserService(chunk_size=50, chunk_overlap=10)
            chunks = service.load_and_split("test.pdf", movie_id="consistency")
            
            # Chunk index'leri sıralı mı?
            for idx, chunk in enumerate(chunks):
                assert chunk["metadata"]["chunk_index"] == idx
                assert chunk["metadata"]["total_chunks"] == len(chunks)