<div align="center">



#  CineMind AI
### Modular Monolith RAG & Sentiment Analysis Platform

**Senaryodan Ekrana Derin Analiz.**
<br>
Clean Architecture prensipleriyle tasarlanmış Modular Monolith ana yapı,<br>
Dockerize edilmiş yardımcı mikroservisler ve RAG altyapısı.

<br>

[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Google Gemini](https://img.shields.io/badge/Google%20AI-Gemini-4285F4?logo=google&logoColor=white)](https://ai.google.dev/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector-orange)](https://www.trychroma.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.31-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![HuggingFace](https://img.shields.io/badge/Model-BERT-yellow?logo=huggingface&logoColor=white)](https://huggingface.co/)
[![Obsidian](https://img.shields.io/badge/Obsidian-Design-7C3AED?logo=obsidian&logoColor=white)](https://obsidian.md/)
[![License](https://img.shields.io/badge/license-MIT-green)](./LICENSE)

<br>

[Hata Bildir](https://github.com/omtekyav/cinemind-ai/issues)

</div>

---

##  Proje Hakkında

**CineMind**, sinema senaryolarını ve izleyici verilerini analiz eden yapay zeka destekli bir asistan projesidir. Proje, "Full-Stack AI Engineering" yetkinliklerini sergilemek amacıyla, endüstri standardı **Modular Monolith** mimarisi üzerine inşa edilmiştir.

Veri tutarlılığını ve geliştirme hızını korumak için ana backend **Layered Architecture** (Katmanlı Mimari) ile geliştirilmişken; ağır işlem gücü gerektiren Duygu Analizi (Sentiment Analysis) modülü, ana yapıdan izole edilerek **Microservice** mantığıyla Dockerize edilmiştir.

### Temel Özellikler

* **Modular Monolith Core:** Domain, Infrastructure ve API katmanlarının net bir şekilde ayrıldığı, bakımı kolay ve ölçeklenebilir yapı.
* **Hybrid Deployment Strategy:** Ana uygulama monolitik olsa da, dağıtım (deployment) aşamasında mikroservis esnekliğini sağlayan Docker Compose orkestrasyonu.
* **Multi-Source RAG:** PDF senaryoları, IMDb (Scraping) ve TMDb (API) verilerinin tek bir vektör uzayında (ChromaDB) birleştirilmesi.
* **Microservice Integration:** Python/FastAPI tabanlı ana uygulamanın, ayrı bir container'da çalışan BERT tabanlı Sentiment Servisi ile HTTP üzerinden haberleşmesi.
* **Clean Code & Testing:** `pytest` ile %80+ test kapsamı ve Type Hinting kullanımı.

---

##  Mimari ve Teknoloji Yığını

Proje, sorumlulukların ayrılığı (SoC) ilkesine sadık kalır:

| Katman | Yapı | Teknoloji | Açıklama |
| :--- | :--- | :--- | :--- |
| **Core Backend** | **Modular Monolith** | FastAPI, Pydantic | İş mantığı, RAG orkestrasyonu ve API yönetimi. |
| **ML Service** | **Microservice** | Transformers (BERT) | Sadece duygu analizi yapan izole servis. |
| **Database** | **Vector Store** | ChromaDB | Doküman embedding'lerinin saklanması. |
| **Architecture** | **Layered** | Domain-Driven Design | `Domain` -> `Service` -> `Infrastructure` -> `API` akışı. |
| **DevOps** | **Containerization** | Docker & Compose | Multi-container ortam yönetimi. |

---

##  Proje Yapısı

Proje, katmanlı mimari prensiplerine uygun olarak düzenlenmiştir:

```bash
cinemind-ai/
├── data/                      # PDF senaryo ve ham veri dosyaları
├── src/
│   ├── api/                   # [Presentation Layer] API Endpoint'leri
│   │   ├── routes.py
│   │   └── schemas.py         # DTO/Pydantic Modelleri
│   ├── domain/                # [Domain Layer] Saf İş Kuralları ve Modeller
│   │   ├── embeddings.py
│   │   └── models.py
│   ├── infrastructure/        # [Infrastructure Layer] Dış Dünya Bağlantıları
│   │   ├── config.py
│   │   ├── gemini_client.py
│   │   └── vector_store.py
│   ├── services/              # [Application Layer] Use Case Lojikleri
│   │   ├── rag/               # RAG Pipeline
│   │   ├── sentiment_client.py # Microservice ile iletişim
│   │   ├── ingestion_coordinator.py
│   │   └── pdf_parser_service.py
│   ├── scripts/               # Veri Yükleme (ETL) Araçları
│   └── ui/                    # Streamlit Frontend
├── tests/                     # Integration ve Unit Testler
├── docker-compose.yml         # Servis Orkestrasyonu
├── Dockerfile                 # Backend Image
└── README.md
```


## Kurulum ve Çalıştırma

Projeyi yerel ortamınızda ayağa kaldırmak için aşağıdaki adımları izleyin.

### Ön Hazırlıklar
* Docker ve Docker Compose yüklü olmalı.
* Google AI Studio'dan alınmış bir `GOOGLE_API_KEY`.

### 1. Projeyi Klonlayın
```bash
git clone [https://github.com/omtekyav/cinemind-ai.git](https://github.com/omtekyav/cinemind-ai.git)
cd cinemind-ai
````

### 2\. Çevresel Değişkenleri Ayarlayın

`.env.example` dosyasını kopyalayarak `.env` oluşturun ve API anahtarınızı girin:

```bash
cp .env.example .env
# .env dosyasını açıp GOOGLE_API_KEY değerini yapıştırın.
```

### 3\. Docker ile Başlatın

```bash
docker-compose up --build -d
```

### 4\. Veri Yükleme (Ingestion)

Sistemin çalışabilmesi için veritabanını besleyin:

```bash
# Container içinde ingestion scriptlerini çalıştır
docker-compose exec cinemind_api python src/scripts/ingest_scripts.py
docker-compose exec cinemind_api python src/scripts/ingest_tmdb.py
```

Sistem aşağıdaki adreslerde çalışacaktır:

  * **Frontend:**  http://localhost:8502
  * **API Docs:** http://localhost:8000/docs
  * **Sentiment Service**: http://localhost:8001/docs

-----

## Test Süreci

Kod kalitesini korumak için birim ve entegrasyon testleri ayrılmıştır.

Testleri çalıştırmak için:

```bash
# Tüm testleri Docker ortamında çalıştır
docker-compose exec cinemind_api pytest tests/ -v
```

**Test Kapsamı:**

  * **Ingestion Logic:** PDF parsing ve Metadata kontrolü.
  * **API Endpoints:** `/health` ve `/api/v1/query` endpoint kontrolleri.
  * **Schema Validation:** Pydantic input/output format doğrulaması.

-----

## Katkıda Bulunma

1.  Forklayın (Fork).
2.  Yeni bir dal oluşturun (`git checkout -b feature/AmazingFeature`).
3.  Değişikliklerinizi commit edin (`git commit -m 'Add some AmazingFeature'`).
4.  Branch'i pushlayın (`git push origin feature/AmazingFeature`).
5.  Bir Pull Request (PR) açın.

-----

Built by [omtekyav](https://www.google.com/search?q=https://github.com/omtekyav)


