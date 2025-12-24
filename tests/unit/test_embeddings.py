import pytest
from unittest.mock import Mock, patch
from src.domain.embeddings import EmbeddingService

class TestEmbeddingService:
    
    @pytest.fixture
    def mock_genai(self):
        """Google API'sini mocklar."""
        with patch("src.domain.embeddings.genai") as mock:
            yield mock

    def test_init_raises_error_without_api_key(self):
        """API Key yoksa hata vermeli."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="GOOGLE_API_KEY bulunamadı"):
                EmbeddingService()

    def test_embed_query_success(self, mock_genai):
        """Başarılı bir sorgu embedding senaryosu."""
        # Ortam değişkeni ayarla
        with patch.dict("os.environ", {"GOOGLE_API_KEY": "fake_key"}):
            service = EmbeddingService()
            
            # API'nin döneceği fake cevap
            mock_response = {'embedding': [0.1, 0.2, 0.3]}
            mock_genai.embed_content.return_value = mock_response
            
            # Test et
            vector = service.embed_query("Batman")
            
            assert vector == [0.1, 0.2, 0.3]
            # Doğru parametrelerle çağrıldı mı?
            mock_genai.embed_content.assert_called_with(
                model="models/text-embedding-004",
                content="Batman",
                task_type="retrieval_query"
            )

    def test_embed_documents_batching(self, mock_genai):
        """Batch (Gruplama) mantığı doğru çalışıyor mu?"""
        with patch.dict("os.environ", {"GOOGLE_API_KEY": "fake_key"}):
            service = EmbeddingService()
            
            # 2 tane doküman yollayalım
            docs = ["Doc1", "Doc2"]
            
            # API'nin dönüşü (Liste içinde liste)
            mock_genai.embed_content.return_value = {
                'embedding': [[0.1], [0.2]]
            }
            
            vectors = service.embed_documents(docs)
            
            assert len(vectors) == 2
            assert vectors[0] == [0.1]
            assert mock_genai.embed_content.call_count == 1 # Tek seferde gitmeli
            
    def test_api_failure_handling(self, mock_genai):
        """API hata verirse sistem çökmemeli, None dönmeli."""
        with patch.dict("os.environ", {"GOOGLE_API_KEY": "fake_key"}):
            service = EmbeddingService()
            
            # API hata fırlatsın
            mock_genai.embed_content.side_effect = Exception("API Down")
            
            vector = service.embed_query("Joker")
            assert vector is None # Çökmedi, None döndü