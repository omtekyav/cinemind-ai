"""
Generator
Tek sorumluluk: LLM ile cevap üretmek.
"""
import logging

import google.generativeai as genai

logger = logging.getLogger(__name__)


class Generator:
    """
    LLM cevap üretici.
    
    Liskov Substitution için:
    - Aynı interface'i implemente eden OpenAIGenerator yazılabilir
    - Pipeline hangi generator gelirse onu kullanır
    """
    
    SYSTEM_PROMPT = """Sen CineMind AI, bir sinema uzmanı asistansın.

KURALLAR:
1. Sadece verilen kaynaklardaki bilgileri kullan
2. Bilmiyorsan "Bu konuda bilgim yok" de
3. Spoiler içeren cevaplarda uyar
4. Türkçe yanıt ver
5. Kaynaklardan alıntı yaparken belirt (örn: "Senaryoya göre...")
"""
    
    def __init__(self, api_key: str, model: str = "models/gemini-2.5-flash"):
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(model)
        self._model_name = model
        
        logger.info(f"🤖 Generator başlatıldı: {model}")
    
    def generate(self, query: str, context: str) -> str:
        """
        Context ve sorgudan cevap üret.
        
        Args:
            query: Kullanıcı sorusu
            context: Formatlanmış kaynak bilgisi
            
        Returns:
            LLM cevabı
        """
        prompt = self._build_prompt(query, context)
        
        try:
            response = self._model.generate_content(prompt)
            answer = response.text
            
            logger.info(f"✅ Cevap üretildi ({len(answer)} karakter)")
            return answer
            
        except Exception as e:
            logger.error(f"❌ LLM hatası: {e}")
            return f"Üzgünüm, şu anda cevap üretemiyorum. Hata: {type(e).__name__}"
    
    def _build_prompt(self, query: str, context: str) -> str:
        """Final prompt'u oluştur."""
        return f"""{self.SYSTEM_PROMPT}

KAYNAKLAR:
{context}

KULLANICI SORUSU:
{query}

CEVAP:"""