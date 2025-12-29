"""
ChromaDB İçeriğini Görüntüleme Script'i
Veritabanındaki verilerin doğruluğunu, sentiment dağılımını ve kaynaklarını analiz eder.
"""
import sys
import os
from pathlib import Path
from collections import Counter

# ----------------------------------------------------------------
# PATH AYARI: 'src' modülünü bulabilmesi için (KRİTİK)
# ----------------------------------------------------------------
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.infrastructure.vector_store import VectorStoreService
from src.infrastructure.config import get_settings

def main():
    print("=" * 60)
    print("🕵️‍♂️  VECTOR STORE INSPECTOR (Müfettiş Gadget)")
    print("=" * 60)

    # Vector Store'a bağlan
    try:
        store = VectorStoreService(
            collection_name="cinemind_store",
            persist_path="data/vector_store"
        )
    except Exception as e:
        print(f"❌ Veritabanına bağlanılamadı: {e}")
        return

    # Toplam doküman sayısı
    total = store.count()
    print(f"📊 TOPLAM DOKÜMAN SAYISI: {total}")
    print("=" * 60)

    if total == 0:
        print("⚠️  Veritabanı boş! Önce ingest scriptlerini çalıştırın.")
        return

    # Tüm dokümanları çek (ilk 50'si yeterli, hepsini çekersek ekran dolar)
    # ChromaDB'de .get() metodu veriyi ham haliyle getirir
    results = store.collection.get(limit=50)

    # Listeleri güvenli bir şekilde zipleyip dönelim
    ids = results.get('ids', [])
    documents = results.get('documents', [])
    metadatas = results.get('metadatas', [])

    # Her dokümanı göster
    for i, (doc_id, text, metadata) in enumerate(zip(ids, documents, metadatas), 1):
        # Metadata boş gelebilir, kontrol edelim
        metadata = metadata or {}
        
        print(f"\n🎬 DOKÜMAN #{i}")
        print(f"🆔 ID: {doc_id}")
        print(f"🎥 Film: {metadata.get('movie_title', 'Bilinmiyor')}")
        print(f"🌍 Kaynak: {metadata.get('source', 'Bilinmiyor')}")
        
        # Sentiment formatı
        sent_label = metadata.get('sentiment_label', 'N/A')
        sent_score = metadata.get('sentiment_score', 0)
        print(f"❤️ Sentiment: {sent_label} (Güven: {sent_score:.2f})")
        
        # İçerik önizleme
        preview = text[:150].replace('\n', ' ') if text else "Boş İçerik"
        print(f"📝 İçerik: {preview}...")
        print("-" * 60)

    # --- İSTATİSTİKLER ---
    
    # Tüm veriyi (sadece metadata) çekerek istatistik çıkaralım
    all_data = store.collection.get(include=['metadatas'])
    all_metas = all_data.get('metadatas', [])
    
    # Temizlik (None olanları ayıkla)
    valid_metas = [m for m in all_metas if m]

    sources = [m.get('source', 'unknown') for m in valid_metas]
    sentiments = [m.get('sentiment_label', 'unknown') for m in valid_metas]
    movies = [m.get('movie_title', 'unknown') for m in valid_metas]

    print("\n📈 KAYNAK DAĞILIMI:")
    for source, count in Counter(sources).items():
        print(f"   🔹 {source}: {count} doküman")

    print("\n💭 SENTIMENT DAĞILIMI:")
    for sentiment, count in Counter(sentiments).items():
        # Renkli çıktı (Opsiyonel)
        icon = "😐"
        if sentiment == "Pozitif": icon = "🟢"
        elif sentiment == "Negatif": icon = "🔴"
        print(f"   {icon} {sentiment}: {count} doküman")
        
    print("\n🎞️  EN ÇOK YORUMU OLAN FİLMLER (Top 5):")
    for movie, count in Counter(movies).most_common(5):
        print(f"   🎬 {movie}: {count} yorum")

    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()