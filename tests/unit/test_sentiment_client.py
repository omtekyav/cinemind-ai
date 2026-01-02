import pytest
import requests
from unittest.mock import Mock, patch, MagicMock, call
import sys
from pathlib import Path

# Proje kök dizinini Python path'ine ekle
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# DOĞRU IMPORT: src.services.sentiment_client modülünden
from src.services.sentiment_client import SentimentClient, _should_retry


# ============================================================================
# UNIT TESTS: _should_retry() Fonksiyonu
# ============================================================================

class TestShouldRetry:
    """Retry stratejisinin doğru çalıştığını test et."""
    
    def test_timeout_should_retry(self):
        exc = requests.Timeout("Connection timeout")
        assert _should_retry(exc) is True
    
    def test_connection_error_should_retry(self):
        exc = requests.ConnectionError("Network unreachable")
        assert _should_retry(exc) is True
    
    def test_5xx_error_should_retry(self):
        response = Mock(status_code=503)
        exc = requests.HTTPError()
        exc.response = response
        assert _should_retry(exc) is True
    
    def test_4xx_error_should_not_retry(self):
        response = Mock(status_code=400)
        exc = requests.HTTPError()
        exc.response = response
        assert _should_retry(exc) is False
    
    def test_other_exceptions_should_not_retry(self):
        assert _should_retry(ValueError("Test")) is False
        assert _should_retry(KeyError("Test")) is False


# ============================================================================
# UNIT TESTS: SentimentClient Initialization
# ============================================================================

class TestSentimentClientInit:
    """Client'ın doğru başlatıldığını test et."""
    
    def test_default_initialization(self):
        client = SentimentClient()
        assert client.base_url == "http://localhost:8001"
        assert client.timeout_seconds == 45
        assert client.fail_open is True
        assert client.batch_url == "http://localhost:8001/api/v1/analyze-batch"
        client.close()
    
    def test_custom_base_url(self):
        client = SentimentClient(base_url="http://custom:9000/")
        assert client.base_url == "http://custom:9000"
        client.close()
    
    def test_env_variable_override(self):
        with patch.dict('os.environ', {'SENTIMENT_SERVICE_URL': 'http://docker:8080'}):
            client = SentimentClient()
            assert client.base_url == "http://docker:8080"
            client.close()
    
    def test_custom_timeout(self):
        client = SentimentClient(timeout_seconds=30)
        assert client.timeout_seconds == 30
        client.close()
    
    def test_fail_closed_mode(self):
        client = SentimentClient(fail_open=False)
        assert client.fail_open is False
        client.close()


# ============================================================================
# UNIT TESTS: Context Manager
# ============================================================================

class TestContextManager:
    """Context manager desteğini test et."""
    
    def test_context_manager_closes_session(self):
        """Context manager çıkışında session.close() çağrılmalı."""
        # Session.close metodunu izleyelim (spy/mock)
        with patch('requests.Session.close') as mock_close:
            with SentimentClient() as client:
                assert client.session is not None
            
            # with bloğundan çıkınca close çağrılmış olmalı
            mock_close.assert_called_once()


# ============================================================================
# UNIT TESTS: check_health()
# ============================================================================

class TestHealthCheck:
    """Health check fonksiyonunu test et."""
    
    # DİKKAT: Patch yolu 'src.services.sentiment_client...' olarak güncellendi
    @patch('src.services.sentiment_client.requests.Session.get')
    def test_health_check_success(self, mock_get):
        mock_response = Mock(status_code=200)
        mock_get.return_value = mock_response
        
        client = SentimentClient()
        assert client.check_health() is True
        client.close()
    
    @patch('src.services.sentiment_client.requests.Session.get')
    def test_health_check_failure_500(self, mock_get):
        mock_response = Mock(status_code=500)
        mock_get.return_value = mock_response
        
        client = SentimentClient()
        assert client.check_health() is False
        client.close()
    
    @patch('src.services.sentiment_client.requests.Session.get')
    def test_health_check_timeout(self, mock_get):
        mock_get.side_effect = requests.Timeout("Timeout")
        
        client = SentimentClient()
        assert client.check_health() is False
        client.close()


# ============================================================================
# UNIT TESTS: _send_batch()
# ============================================================================

class TestSendBatch:
    """_send_batch() metodunu test et (retry devre dışı)."""
    
    # DİKKAT: Patch yolu 'src.services.sentiment_client...' olarak güncellendi
    @patch('src.services.sentiment_client.requests.Session.post')
    def test_send_batch_success(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {"sentiment": "Pozitif", "confidence": 0.95},
                {"sentiment": "Negatif", "confidence": 0.89}
            ]
        }
        mock_post.return_value = mock_response
        
        client = SentimentClient()
        # Retry sayacını temizlemek gerekebilir ama mock ile genelde sorun olmaz
        results = client._send_batch(["Great!", "Bad!"])
        
        assert len(results) == 2
        assert results[0]["sentiment"] == "Pozitif"
        assert results[1]["sentiment"] == "Negatif"
        client.close()
    
    @patch('src.services.sentiment_client.requests.Session.post')
    def test_send_batch_invalid_response_format(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": "NOT_A_LIST"} 
        mock_post.return_value = mock_response
        
        client = SentimentClient()
        with pytest.raises(ValueError, match="beklenmeyen format"):
            client._send_batch(["Test"])
        client.close()
    
    @patch('src.services.sentiment_client.requests.Session.post')
    def test_send_batch_4xx_error_no_retry(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        # raise_for_status çağrılınca hata fırlatsın
        mock_response.raise_for_status.side_effect = requests.HTTPError()
        mock_post.return_value = mock_response
        
        client = SentimentClient()
        with pytest.raises(requests.HTTPError):
            client._send_batch(["Test"])
        
        assert mock_post.call_count == 1
        client.close()


# ============================================================================
# UNIT TESTS: analyze_batch() - Input Validation
# ============================================================================

class TestAnalyzeBatchValidation:
    
    def test_empty_list_returns_empty(self):
        client = SentimentClient()
        result = client.analyze_batch([])
        assert result == []
        client.close()
    
    def test_batch_size_too_small(self):
        client = SentimentClient()
        with pytest.raises(ValueError, match="1-100 arasında olmalı"):
            client.analyze_batch(["Test"], batch_size=0)
        with pytest.raises(ValueError, match="1-100 arasında olmalı"):
            client.analyze_batch(["Test"], batch_size=-5)
        client.close()
    
    def test_batch_size_too_large(self):
        client = SentimentClient()
        with pytest.raises(ValueError, match="1-100 arasında olmalı"):
            client.analyze_batch(["Test"], batch_size=101)
        client.close()


# ============================================================================
# UNIT TESTS: analyze_batch() - Happy Path
# ============================================================================

class TestAnalyzeBatchHappyPath:
    
    @patch.object(SentimentClient, '_send_batch')
    def test_single_batch_success(self, mock_send):
        mock_send.return_value = [
            {"sentiment": "Pozitif", "confidence": 0.9},
            {"sentiment": "Negatif", "confidence": 0.8}
        ]
        
        client = SentimentClient()
        results = client.analyze_batch(["Good", "Bad"], batch_size=10)
        
        assert len(results) == 2
        assert results[0]["sentiment"] == "Pozitif"
        assert mock_send.call_count == 1
        client.close()
    
    @patch.object(SentimentClient, '_send_batch')
    def test_multiple_batches(self, mock_send):
        mock_send.return_value = [{"sentiment": "Nötr", "confidence": 0.5}] * 2
        
        client = SentimentClient()
        texts = ["Text"] * 5 
        results = client.analyze_batch(texts, batch_size=2) 
        
        assert len(results) == 5
        assert mock_send.call_count == 3 
        client.close()
    
    @patch.object(SentimentClient, '_send_batch')
    def test_none_values_normalized(self, mock_send):
        mock_send.return_value = [{"sentiment": "Nötr", "confidence": 0.0}] * 2
        
        client = SentimentClient()
        results = client.analyze_batch([None, "Test"], batch_size=10)
        
        call_args = mock_send.call_args[0][0]
        assert call_args[0] == "" 
        assert call_args[1] == "Test"
        client.close()


# ============================================================================
# UNIT TESTS: analyze_batch() - Error Handling
# ============================================================================

class TestAnalyzeBatchErrorHandling:
    
    @patch.object(SentimentClient, '_send_batch')
    def test_fail_open_mode_network_error(self, mock_send):
        mock_send.side_effect = requests.ConnectionError("Network down")
        
        client = SentimentClient(fail_open=True)
        results = client.analyze_batch(["Test1", "Test2"], batch_size=10)
        
        assert len(results) == 2
        assert all(r["sentiment"] == "Nötr" for r in results)
        client.close()
    
    @patch.object(SentimentClient, '_send_batch')
    def test_fail_closed_mode_raises_error(self, mock_send):
        mock_send.side_effect = requests.ConnectionError("Network down")
        
        client = SentimentClient(fail_open=False)
        with pytest.raises(requests.ConnectionError):
            client.analyze_batch(["Test"], batch_size=10)
        client.close()
    
    @patch.object(SentimentClient, '_send_batch')
    def test_length_mismatch_fills_neutral(self, mock_send):
        mock_send.return_value = [
            {"sentiment": "Pozitif", "confidence": 0.9},
            {"sentiment": "Negatif", "confidence": 0.8}
        ]
        
        client = SentimentClient()
        results = client.analyze_batch(["A", "B", "C"], batch_size=10)
        
        assert len(results) == 3
        assert results[2]["sentiment"] == "Nötr"
        client.close()
    
    @patch.object(SentimentClient, '_send_batch')
    def test_critical_error_raises(self, mock_send):
        mock_send.side_effect = MemoryError("Out of memory")
        
        client = SentimentClient(fail_open=True)
        with pytest.raises(MemoryError):
            client.analyze_batch(["Test"], batch_size=10)
        client.close()


# ============================================================================
# PARAMETRIC TESTS
# ============================================================================

@pytest.mark.parametrize("batch_size,expected_calls", [
    (10, 1),
    (5, 2),
    (3, 4),
])
@patch.object(SentimentClient, '_send_batch')
def test_batch_splitting(mock_send, batch_size, expected_calls):
    mock_send.return_value = [{"sentiment": "Nötr", "confidence": 0.5}] * batch_size
    
    client = SentimentClient()
    texts = ["Text"] * 10
    client.analyze_batch(texts, batch_size=batch_size)
    
    assert mock_send.call_count == expected_calls
    client.close()