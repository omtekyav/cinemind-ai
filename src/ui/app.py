"""
CineMind AI - Streamlit UI
Sinema Analiz Asistanı Arayüzü
"""
import streamlit as st
from api_client import CineMindClient

# =============================================================================
# SAYFA AYARLARI
# =============================================================================
st.set_page_config(
    page_title="CineMind AI",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================================
# SESSION STATE
# =============================================================================
if "messages" not in st.session_state:
    st.session_state.messages = []

if "client" not in st.session_state:
    st.session_state.client = CineMindClient()

# =============================================================================
# SIDEBAR
# =============================================================================
with st.sidebar:
    st.header("⚙️ Ayarlar")
    
    # Kaynak Filtresi
    source_filter = st.selectbox(
        "📚 Kaynak Filtresi",
        options=[None, "script", "imdb", "tmdb"],
        format_func=lambda x: {
            None: "🌐 Tüm Kaynaklar",
            "script": "📜 Senaryo",
            "imdb": "🎬 IMDb Yorumları",
            "tmdb": "🎥 TMDb Yorumları"
        }.get(x, x)
    )
    
    # Sonuç Limiti
    result_limit = st.slider("🔢 Maksimum Kaynak", 1, 20, 10)
    
    # Benzerlik Eşiği
    similarity_threshold = st.slider("📊 Min. Benzerlik", 0.0, 1.0, 0.50, 0.05)
    
    st.divider()
    
    # Sistem Durumu
    st.subheader("🏥 Sistem Durumu")
    
    if st.button("🔄 Kontrol Et"):
        with st.spinner("Kontrol ediliyor..."):
            health = st.session_state.client.health_check()
            
            if health.get("status") == "healthy":
                st.success("✅ Sistem Sağlıklı")
                st.json(health.get("services", {}))
            elif health.get("status") == "error":
                st.error("❌ Bağlantı Hatası")
                st.caption(health.get("message", ""))
            else:
                st.warning(f"⚠️ {health.get('status', 'Bilinmiyor')}")
    
    st.divider()
    
    # Sohbeti Temizle
    if st.button("🗑️ Sohbeti Temizle"):
        st.session_state.messages = []
        st.rerun()

# =============================================================================
# ANA ALAN
# =============================================================================
st.title("🎬 CineMind AI")
st.caption("Sinema Analiz Asistanı - RAG Tabanlı")

# =============================================================================
# YARDIMCI FONKSİYONLAR
# =============================================================================
def filter_sources(sources: list, threshold: float) -> list:
    """Düşük benzerlikli kaynakları filtrele."""
    return [s for s in sources if (1 - s['distance']) >= threshold]


def render_sources(sources: list, threshold: float):
    """Kaynakları render et."""
    filtered = filter_sources(sources, threshold)
    
    if not filtered:
        st.info("📭 Bu soru için yeterli benzerlikte kaynak bulunamadı.")
        return
    
    with st.expander(f"📚 Kaynaklar ({len(filtered)} adet)"):
        for i, source in enumerate(filtered, 1):
            source_icon = {"script": "📜", "imdb": "🎬", "tmdb": "🎥"}.get(source['source'], "📄")
            similarity = 1 - source['distance']
            
            st.markdown(f"**{i}. {source_icon} {source['movie_title']}**")
            st.caption(f"Benzerlik: {similarity:.1%}")
            st.markdown(f"> {source['content'][:300]}...")
            st.divider()

# =============================================================================
# SOHBET GEÇMİŞİ
# =============================================================================
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        if message["role"] == "assistant" and "sources" in message:
            render_sources(message["sources"], similarity_threshold)

# =============================================================================
# KULLANICI GİRİŞİ
# =============================================================================
if prompt := st.chat_input("Filmler hakkında bir soru sorun..."):
    # Kullanıcı mesajını ekle
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Asistan yanıtı
    with st.chat_message("assistant"):
        with st.spinner("🤔 Düşünüyorum..."):
            response = st.session_state.client.query(
                question=prompt,
                source_filter=source_filter,
                limit=result_limit
            )
            
            if "error" in response:
                st.error(f"❌ Hata: {response.get('message', 'Bilinmeyen hata')}")
                answer = "Üzgünüm, bir hata oluştu. Lütfen Backend'in çalıştığından emin olun."
                sources = []
            else:
                answer = response.get("answer", "Yanıt alınamadı.")
                sources = response.get("sources", [])
            
            st.markdown(answer)
            
            if sources:
                render_sources(sources, similarity_threshold)
    
    # Asistan mesajını kaydet
    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
        "sources": sources
    })