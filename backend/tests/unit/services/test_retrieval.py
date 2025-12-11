from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from ai_memory_layer.services.retrieval import MemoryRetriever


def _message(content: str, importance: float, created_at: datetime) -> SimpleNamespace:
    return SimpleNamespace(
        id=content,
        content=content,
        role="user",
        metadata={},
        importance_score=importance,
        embedding=[float(len(content)), 1.0],
        created_at=created_at,
    )


def test_retriever_orders_by_combined_score():
    retriever = MemoryRetriever(similarity_weight=0.5, importance_weight=0.4, decay_weight=0.1)
    now = datetime.now(timezone.utc)
    messages = [
        _message("short", 0.2, now - timedelta(days=2)),
        _message("much longer text", 0.9, now),
    ]
    query_embedding = [10.0, 1.0]
    ranked = retriever.rank(query_embedding=query_embedding, candidates=messages, top_k=2)
    assert ranked[0].message.content == "much longer text"
