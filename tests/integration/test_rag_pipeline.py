"""
RAG Pipeline Integration Test
Tüm RAG bileşenlerinin birlikte çalıştığını doğrular.
"""
import pytest
import logging

from src.services.rag import RAGPipeline, SourceType, RAGResponse

logging.basicConfig(level=logging.INFO)


class TestRAGPipeline:
    """RAG Pipeline entegrasyon testleri."""
    
    @pytest.fixture(scope="class")
    def pipeline(self):
        """Test boyunca tek pipeline instance kullan."""
        return RAGPipeline()
    
    def test_basic_query_returns_response(self, pipeline):
        """Temel sorgu RAGResponse döndürmeli."""
        response = pipeline.query("The Dark Knight filminde Joker'in planı neydi?")
        
        print("\n" + "=" * 60)
        print("📌 TEST 1: Temel Sorgu")
        print("=" * 60)
        print(f"SORU: {response.query}")
        print(f"\nCEVAP:\n{response.answer}")
        print(f"\nKAYNAK SAYISI: {len(response.sources)}")
        
        assert isinstance(response, RAGResponse)
        assert response.query is not None
        assert response.answer is not None
        assert len(response.answer) > 0
    
    def test_query_returns_sources(self, pipeline):
        """Sorgu kaynakları içermeli."""
        response = pipeline.query("Batman karakteri nasıl?")
        
        print("\n" + "=" * 60)
        print("📌 TEST 2: Kaynak Kontrolü")
        print("=" * 60)
        print(f"SORU: {response.query}")
        print(f"\nKAYNAKLAR ({len(response.sources)} adet):")
        for i, src in enumerate(response.sources, 1):
            print(f"  {i}. [{src.source.value}] {src.movie_title}")
            print(f"     Distance: {src.distance:.4f}")
            print(f"     İçerik: {src.content[:100]}...")
        
        assert response.sources is not None
        assert len(response.sources) > 0
        
        for src in response.sources:
            assert src.content is not None
            assert src.source is not None
            assert src.movie_title is not None
            assert src.distance >= 0
    
    def test_source_filter_works(self, pipeline):
        """Kaynak filtresi çalışmalı."""
        response = pipeline.query(
            "Batman ve Joker sahnesi",
            source_filter=SourceType.SCRIPT
        )
        
        print("\n" + "=" * 60)
        print("📌 TEST 3: Kaynak Filtresi (Sadece SCRIPT)")
        print("=" * 60)
        print(f"SORU: {response.query}")
        print(f"\nCEVAP:\n{response.answer[:300]}...")
        print(f"\nKAYNAKLAR:")
        for i, src in enumerate(response.sources, 1):
            print(f"  {i}. [{src.source.value}] {src.movie_title}")
        
        for src in response.sources:
            assert src.source == SourceType.SCRIPT, f"Beklenen SCRIPT, gelen {src.source}"
    
    def test_query_movie_helper(self, pipeline):
        """Film bazlı sorgu helper'ı çalışmalı."""
        response = pipeline.query_movie("Inception", "Film nasıl yorumlanmış?")
        
        print("\n" + "=" * 60)
        print("📌 TEST 4: Film Bazlı Sorgu")
        print("=" * 60)
        print(f"SORU: {response.query}")
        print(f"\nCEVAP:\n{response.answer}")
        
        assert isinstance(response, RAGResponse)
        assert "Inception" in response.query
    
    def test_empty_results_handled(self, pipeline):
        """Sonuç bulunamazsa graceful response dönmeli."""
        response = pipeline.query("xyzabc123 olmayan film adı")
        
        print("\n" + "=" * 60)
        print("📌 TEST 5: Boş Sonuç Kontrolü")
        print("=" * 60)
        print(f"SORU: {response.query}")
        print(f"\nCEVAP:\n{response.answer}")
        print(f"KAYNAK SAYISI: {len(response.sources)}")
        
        assert isinstance(response, RAGResponse)
        assert response.answer is not None