"""
Generator (Refactored for Agentic RAG)
LangChain Chat Model wrapper kullanıyor.
"""
import logging
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

logger = logging.getLogger(__name__)


class Generator:
    """
    LangChain tabanlı Generator.
    Tool binding'e hazır yapı.
    """
    
    SYSTEM_PROMPT = """Sen CineMind AI, bir sinema uzmanı asistansın.

KURALLAR:
1. Sadece verilen kaynaklardaki bilgileri kullan
2. Bilmiyorsan "Bu konuda bilgim yok" de
3. Spoiler içeren cevaplarda uyar
4. Türkçe yanıt ver
5. Kaynaklardan alıntı yaparken belirt (örn: "Senaryoya göre...")
"""
    
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        self._llm = ChatGoogleGenerativeAI(
            model=model,
            google_api_key=api_key,
            temperature=0
        )
        self._model_name = model
        logger.info(f"🤖 LangChain Generator başlatıldı: {model}")
    
    def generate(self, query: str, context: str) -> str:
        """
        LCEL ile cevap üret.
        Akış: Prompt -> LLM -> String Parser
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.SYSTEM_PROMPT),
            ("user", """KAYNAKLAR:
{context}

KULLANICI SORUSU:
{query}

CEVAP:""")
        ])
        
        chain = prompt | self._llm | StrOutputParser()
        
        try:
            answer = chain.invoke({"context": context, "query": query})
            logger.info(f"✅ Cevap üretildi ({len(answer)} karakter)")
            return answer
        except Exception as e:
            logger.error(f"❌ LangChain hatası: {e}")
            return f"Üzgünüm, şu anda cevap üretemiyorum. Hata: {type(e).__name__}"