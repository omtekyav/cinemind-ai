"""
RAG DTOs (Data Transfer Objects)
Pipeline içinde veri taşıyan yapılar.
Domain entity'lerinden bağımsız.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any
from enum import Enum


class SourceType(str, Enum):
    """Veri kaynağı tipleri."""
    TMDB = "tmdb"
    IMDB = "imdb"
    SCRIPT = "script"


@dataclass
class RetrievedDocument:
    """Vector search'ten dönen doküman."""
    content: str
    source: SourceType
    movie_title: str
    distance: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    weighted_score: float = 0.0


@dataclass
class RAGResponse:
    """RAG pipeline çıktısı."""
    answer: str
    sources: List[RetrievedDocument]
    query: str
    tokens_used: int = 0