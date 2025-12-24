import pytest
import shutil
import os
import gc # <--- EKLENDİ: Garbage Collector
import time
from src.infrastructure.vector_store import VectorStoreService

# Testler için geçici veritabanı yolu
TEST_DB_PATH = "data/test_vector_store_integration"

class TestVectorStoreIntegration:
    
    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """
        Windows dostu temizlik mekanizması.
        """
        # --- SETUP ---
        # Önceki testten kalan varsa temizle (Zorla)
        if os.path.exists(TEST_DB_PATH):
            try:
                shutil.rmtree(TEST_DB_PATH)
            except PermissionError:
                pass # Setup aşamasında hata verirse yoksay, teardown halleder.
            
        yield # Test burada çalışır
        
        # --- TEARDOWN ---
        # Test bitti, değişkenleri bellekten sil
        gc.collect() # Çöpçüyü çağır: "Kullanılmayan bağlantıları kapat"
        
        # Dosya kilidinin açılması için Windows'a milisaniyelik nefes payı ver
        time.sleep(0.1) 
        
        if os.path.exists(TEST_DB_PATH):
            try:
                shutil.rmtree(TEST_DB_PATH)
            except PermissionError:
                # Bazen Windows çok inatçıdır, ikinci kez deneriz
                time.sleep(0.5)
                try:
                    shutil.rmtree(TEST_DB_PATH)
                except:
                    print(f"\n⚠️ Windows dosyayı bırakmadı: {TEST_DB_PATH} (Manuel silinebilir)")

    def test_full_flow(self):
        """Uçtan Uca Test Senaryosu"""
        store = VectorStoreService(
            collection_name="integration_test", 
            persist_path=TEST_DB_PATH
        )
        
        vec_a = [1.0] + [0.0] * 767
        vec_b = [0.0] + [1.0] * 767
        
        texts = ["Batman Hero", "Joker Villain"]
        embeddings = [vec_a, vec_b]
        metadatas = [{"type": "hero"}, {"type": "villain"}]
        
        store.add_documents(texts, embeddings, metadatas)
        assert store.count() == 2
        
        results = store.search(query_vector=vec_a, limit=1)
        assert len(results) == 1
        assert results[0]['document'] == "Batman Hero"
        
        doc_id = results[0]['id']
        doc = store.get_by_id(doc_id)
        assert doc is not None
        
        store.delete_by_ids([doc_id])
        assert store.count() == 1
        
        # Belleği temizle ki Windows dosyayı bıraksın
        del store 

    def test_dimension_check(self):
        """Hata yönetimi testi"""
        store = VectorStoreService(persist_path=TEST_DB_PATH)
        vec_wrong = [[0.1, 0.2]]
        
        try:
            # DÜZELTME: Boş metadata ({}) yerine dolu metadata ({"test": "true"}) gönderiyoruz.
            store.add_documents(["Test"], vec_wrong, [{"test": "true"}])
            assert True 
        except Exception as e:
            # Hatanın ne olduğunu görmek için loga basalım
            print(f"\nBeklenmeyen Hata: {e}")
            pytest.fail("Yanlış boyut sistemi çökertti!")
        
        # Belleği temizle
        del store