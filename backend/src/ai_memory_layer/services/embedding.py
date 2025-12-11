"""Embedding service abstractions."""

from __future__ import annotations

import asyncio
import hashlib
import math
from functools import lru_cache
from typing import Any, Protocol, Sequence

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ai_memory_layer.config import get_settings
from ai_memory_layer.logging import get_logger
from ai_memory_layer.services.circuit_breaker import CircuitBreaker, CircuitOpenError

logger = get_logger(component="embedding_service")

SentenceTransformer: Any | None = None
_GENAI_MODULE: Any | None = None


class EmbeddingService(Protocol):
    async def embed(self, text: str) -> list[float]:
        ...


class CircuitBreakerEmbeddingService:

    def __init__(
        self,
        primary: EmbeddingService,
        fallback: EmbeddingService | None = None,
        *,
        breaker: CircuitBreaker | None = None,
    ) -> None:
        self.primary = primary
        self.fallback = fallback or MockEmbeddingService()
        self.breaker = breaker or CircuitBreaker()

    async def embed(self, text: str) -> list[float]:
        try:
            return await self.breaker.call(self.primary.embed, text)
        except CircuitOpenError:
            logger.warning("embedding_circuit_open", provider=type(self.primary).__name__)
        except Exception as exc:
            logger.error("embedding_provider_failed", error=str(exc))
        return await self.fallback.embed(text)


class MockEmbeddingService:

    def __init__(self, dimensions: int | None = None) -> None:
        settings = get_settings()
        self.dimensions = dimensions or settings.embedding_dimensions

    async def embed(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        values = [b / 255 for b in digest]
        repeats = math.ceil(self.dimensions / len(values))
        raw = (values * repeats)[: self.dimensions]
        return raw


class SentenceTransformerEmbeddingService:

    def __init__(self, model_name: str, dimensions: int) -> None:
        _load_sentence_transformer()
        self.model = _load_model(model_name)
        self.dimensions = dimensions

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        reraise=True,
    )
    async def embed(self, text: str) -> list[float]:
        try:
            loop = asyncio.get_running_loop()
            vector = await loop.run_in_executor(
                None, lambda: self.model.encode(text, show_progress_bar=False)  # type: ignore[attr-defined]
            )
            values = vector.tolist() if hasattr(vector, "tolist") else list(vector)
            if len(values) != self.dimensions:
                # pad/truncate to configured dimension
                if len(values) > self.dimensions:
                    values = values[: self.dimensions]
                else:
                    values.extend([0.0] * (self.dimensions - len(values)))
            return values
        except Exception as exc:
            logger.error("sentence_transformer_embedding_failed", error=str(exc), text_length=len(text))
            raise


def _load_sentence_transformer():
    global SentenceTransformer  # noqa: PLW0603
    if SentenceTransformer is not None:
        return SentenceTransformer
    try:  # pragma: no cover - optional dependency
        from sentence_transformers import SentenceTransformer as _SentenceTransformer
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("sentence-transformers is required for sentence_transformer provider") from exc
    SentenceTransformer = _SentenceTransformer
    return SentenceTransformer


@lru_cache(maxsize=1)
def _load_model(model_name: str):
    model_cls = _load_sentence_transformer()
    return model_cls(model_name)


class GoogleGeminiEmbeddingService:

    def __init__(self, api_key: str, model_name: str = "models/embedding-001", dimensions: int = 768) -> None:
        genai = _load_genai()
        if not api_key:
            raise ValueError("GEMINI_API_KEY is required for google_gemini provider")
            
        genai.configure(api_key=api_key)
        self.model_name = model_name
        self.dimensions = dimensions

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        reraise=True,
    )
    async def embed(self, text: str) -> list[float]:
        loop = asyncio.get_running_loop()
        
        def _call_gemini():
            result = genai.embed_content(
                model=self.model_name,
                content=text,
                task_type="retrieval_document",
                title="Embedding of text"
            )
            return result['embedding']

        try:
            values = await loop.run_in_executor(None, _call_gemini)
            if len(values) != self.dimensions:
                logger.warning(
                    "gemini_embedding_dimension_mismatch",
                    expected=self.dimensions,
                    actual=len(values)
                )
                if len(values) > self.dimensions:
                    values = values[: self.dimensions]
                else:
                    values.extend([0.0] * (self.dimensions - len(values)))
            return values
        except Exception as e:
            logger.error("gemini_embedding_failed", error=str(e), text_length=len(text))
            raise


def build_embedding_service(provider: str | None = None) -> EmbeddingService:
    settings = get_settings()
    provider = provider or settings.embedding_provider
    fallback = MockEmbeddingService(dimensions=settings.embedding_dimensions)
    breaker = CircuitBreaker(
        failure_threshold=settings.circuit_failure_threshold,
        recovery_time_seconds=settings.circuit_recovery_seconds,
    )
    base: EmbeddingService | None = None
    if provider == "sentence_transformer":
        try:
            base = SentenceTransformerEmbeddingService(
                model_name=settings.embedding_model_name,
                dimensions=settings.embedding_dimensions,
            )
        except Exception as exc:  # pragma: no cover - fallback for missing model
            logger.warning("sentence_transformer_unavailable_falling_back_to_mock", error=str(exc))
    elif provider == "google_gemini":
        try:
            base = GoogleGeminiEmbeddingService(
                api_key=settings.gemini_api_key or "",
                model_name="models/embedding-001", 
                dimensions=settings.embedding_dimensions,
            )
        except Exception as exc:
            logger.warning("google_gemini_unavailable_falling_back_to_mock", error=str(exc))
    if base is None:
        return fallback
    return CircuitBreakerEmbeddingService(primary=base, fallback=fallback, breaker=breaker)


def _load_genai():
    global _GENAI_MODULE  # noqa: PLW0603
    if _GENAI_MODULE is not None:
        return _GENAI_MODULE
    try:  # pragma: no cover - optional dependency
        import google.generativeai as genai  # type: ignore[import]
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("google-generativeai is required for google_gemini provider") from exc
    _GENAI_MODULE = genai
    return _GENAI_MODULE
