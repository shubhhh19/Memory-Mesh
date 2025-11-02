"""Embedding service abstractions."""

from __future__ import annotations

import hashlib
import math
from typing import Protocol, Sequence

from ai_memory_layer.config import get_settings


class EmbeddingService(Protocol):
    async def embed(self, text: str) -> list[float]:
        ...


class MockEmbeddingService:
    """Deterministic mock embedder for local dev & tests."""

    def __init__(self, dimensions: int | None = None) -> None:
        settings = get_settings()
        self.dimensions = dimensions or settings.embedding_dimensions

    async def embed(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        values = [b / 255 for b in digest]
        repeats = math.ceil(self.dimensions / len(values))
        raw = (values * repeats)[: self.dimensions]
        return raw


def build_embedding_service(provider: str | None = None) -> EmbeddingService:
    settings = get_settings()
    provider = provider or settings.embedding_provider
    # Future: wire up OpenAI/Azure clients here.
    return MockEmbeddingService(dimensions=settings.embedding_dimensions)
