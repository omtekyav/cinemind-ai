"""
API Integration Tests
FastAPI endpoint'lerinin doğru çalıştığını test eder.
Validation odaklı - Mock karmaşıklığından kaçınır.
"""
import pytest
from fastapi.testclient import TestClient
from src.main import app


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


# =============================================================================
# ROOT ENDPOINT
# =============================================================================

class TestRootEndpoint:
    """Root endpoint testleri."""
    
    def test_root_returns_app_info(self, client):
        """Root endpoint API bilgisi döndürmeli."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "app" in data
        assert "version" in data
        assert "docs" in data


# =============================================================================
# QUERY ENDPOINT - Validation Tests
# =============================================================================

class TestQueryValidation:
    """POST /api/v1/query validation testleri."""
    
    def test_query_validation_error_short_question(self, client):
        """Çok kısa soru 422 hatası vermeli."""
        response = client.post(
            "/api/v1/query",
            json={"question": "ab"}
        )
        
        assert response.status_code == 422
    
    def test_query_validation_error_missing_question(self, client):
        """Question alanı zorunlu, eksikse 422."""
        response = client.post(
            "/api/v1/query",
            json={}
        )
        
        assert response.status_code == 422
    
    def test_query_invalid_source_filter(self, client):
        """Geçersiz source_filter 422 hatası vermeli."""
        response = client.post(
            "/api/v1/query",
            json={
                "question": "Test sorusu",
                "source_filter": "invalid_source"
            }
        )
        
        assert response.status_code == 422
    
    def test_query_invalid_limit_too_high(self, client):
        """Limit çok yüksekse 422 hatası vermeli."""
        response = client.post(
            "/api/v1/query",
            json={
                "question": "Test sorusu",
                "limit": 100
            }
        )
        
        assert response.status_code == 422
    
    def test_query_invalid_limit_too_low(self, client):
        """Limit çok düşükse 422 hatası vermeli."""
        response = client.post(
            "/api/v1/query",
            json={
                "question": "Test sorusu",
                "limit": 0
            }
        )
        
        assert response.status_code == 422


# =============================================================================
# INGEST ENDPOINT - Validation Tests
# =============================================================================

class TestIngestValidation:
    """POST /api/v1/ingest validation testleri."""
    
    def test_ingest_invalid_source(self, client):
        """Geçersiz source 422 hatası vermeli."""
        response = client.post(
            "/api/v1/ingest",
            json={"source": "invalid", "limit": 5}
        )
        
        assert response.status_code == 422
    
    def test_ingest_limit_too_high(self, client):
        """Limit çok yüksekse 422 hatası vermeli."""
        response = client.post(
            "/api/v1/ingest",
            json={"source": "tmdb", "limit": 100}
        )
        
        assert response.status_code == 422
    
    def test_ingest_missing_source(self, client):
        """Source zorunlu, eksikse 422."""
        response = client.post(
            "/api/v1/ingest",
            json={"limit": 5}
        )
        
        assert response.status_code == 422


# =============================================================================
# HEALTH ENDPOINT
# =============================================================================

class TestHealthEndpoint:
    """GET /api/v1/health testleri."""
    
    def test_health_check_returns_200(self, client):
        """Health endpoint 200 döndürmeli."""
        response = client.get("/api/v1/health")
        
        assert response.status_code == 200
    
    def test_health_check_structure(self, client):
        """Health endpoint doğru yapıda response döndürmeli."""
        response = client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "version" in data
        assert "services" in data
    
    def test_health_status_valid_value(self, client):
        """Health status healthy veya degraded olmalı."""
        response = client.get("/api/v1/health")
        
        data = response.json()
        assert data["status"] in ["healthy", "degraded"]