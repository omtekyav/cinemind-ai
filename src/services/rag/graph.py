"""
Agentic RAG Graph
Ajanın beyni burada tanımlanır.
Döngüsel akış: Agent -> (Tool Call?) -> Tools -> Agent
"""
import logging
from typing import TypedDict, Annotated, List
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from langgraph.prebuilt import ToolNode, tools_condition

from src.infrastructure.config import get_settings
from src.services.rag.tools import ALL_TOOLS
from src.services.rag.generator import Generator

logger = logging.getLogger(__name__)


# --- 1. STATE (HAFIZA) ---
class AgentState(TypedDict):
    """Ajanın hafızası. Mesaj geçmişini tutar."""
    messages: Annotated[List[BaseMessage], add_messages]


# --- 2. SYSTEM PROMPT ---
SYSTEM_PROMPT = """Sen CineMind AI, bir sinema uzmanı asistansın.

Elindeki araçlar:
1. search_vector_db: Senaryo, yorum ve film analizleri için kullan.
2. search_tmdb_metadata: Yönetmen, oyuncu, yıl gibi film künye bilgileri için kullan.

KURALLAR:
- Kullanıcı bir film hakkında soru sorduğunda, önce uygun aracı kullan.
- Araç sonucuna göre Türkçe cevap ver.
- Bilgi bulamazsan "Bu konuda bilgim yok" de, uydurma.
- Spoiler varsa uyar.
"""


# --- 3. GRAPH BUILDER ---
def create_graph():
    """LangGraph akışını oluşturur ve derler."""
    
    settings = get_settings()
    
    # Generator'ı başlat
    gen_service = Generator(api_key=settings.GOOGLE_API_KEY)
    
    # LLM'e Tool'ları öğret (BINDING)
    llm_with_tools = gen_service._llm.bind_tools(ALL_TOOLS)

    # --- NODE: AGENT (KARAR VERİCİ) ---
    def agent_node(state: AgentState):
        logger.info("🤖 Ajan düşünüyor...")
        
        # İlk mesajsa system prompt ekle
        messages = state["messages"]
        if not any(isinstance(m, SystemMessage) for m in messages):
            messages = [SystemMessage(content=SYSTEM_PROMPT)] + list(messages)
        
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    # --- NODE: TOOLS (EYLEM) ---
    tool_node_instance = ToolNode(ALL_TOOLS)

    # --- GRAFİĞİ ÇİZ ---
    workflow = StateGraph(AgentState)

    # Düğümleri ekle
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tool_node_instance)

    # Kenarları ekle
    workflow.add_edge(START, "agent")
    
    workflow.add_conditional_edges(
        "agent",
        tools_condition,
        {
            "tools": "tools",
            "__end__": END
        }
    )
    
    workflow.add_edge("tools", "agent")

    # Grafiği derle ve döndür
    return workflow.compile()


# --- 4. KULLANIM FONKSİYONU ---
def query_agent(question: str) -> str:
    """
    Agent'a soru sor ve cevap al.
    
    Args:
        question: Kullanıcı sorusu
        
    Returns:
        Agent'ın cevabı
    """
    graph = create_graph()
    
    # Başlangıç state'i
    initial_state = {
        "messages": [HumanMessage(content=question)]
    }
    
    # Graph'ı çalıştır
    logger.info(f"🎯 Agent query: {question[:50]}...")
    result = graph.invoke(initial_state)
    
    # Son mesajı al (AI cevabı)
    final_message = result["messages"][-1]
    
    return final_message.content