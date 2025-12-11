"""Memory retrieval logic that combines similarity, importance, and decay."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, Sequence

from ai_memory_layer.config import get_settings
from ai_memory_layer.models.memory import Message


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


@dataclass
class RetrievedMemory:
    message: Message
    score: float
    similarity: float
    decay: float


class MemoryRetriever:
    """Combines scoring signals to deterministically rank memories."""

    def __init__(
        self,
        *,
        similarity_weight: float = 0.6,
        importance_weight: float = 0.3,
        decay_weight: float = 0.1,
    ) -> None:
        total = similarity_weight + importance_weight + decay_weight
        self.similarity_weight = similarity_weight / total
        self.importance_weight = importance_weight / total
        self.decay_weight = decay_weight / total

    def rank(
        self,
        *,
        query_embedding: Sequence[float],
        candidates: Iterable[Message],
        top_k: int,
    ) -> list[RetrievedMemory]:
        scored: list[RetrievedMemory] = []
        now = datetime.now(timezone.utc)
        for message in candidates:
            if message.embedding is None:
                continue
            embedding = list(message.embedding)
            similarity = cosine_similarity(query_embedding, embedding)
            age_seconds = (now - message.created_at.replace(tzinfo=timezone.utc)).total_seconds()
            decay = math.exp(-age_seconds / (60 * 60 * 24 * 7))  # 1-week half-life
            importance = message.importance_score or 0.0
            score = (
                similarity * self.similarity_weight
                + importance * self.importance_weight
                + decay * self.decay_weight
            )
            scored.append(
                RetrievedMemory(
                    message=message,
                    score=score,
                    similarity=similarity,
                    decay=decay,
                )
            )
        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[:top_k]


def default_retriever() -> MemoryRetriever:
    settings = get_settings()
    return MemoryRetriever(
        similarity_weight=0.6,
        importance_weight=0.3,
        decay_weight=0.1,
    )
