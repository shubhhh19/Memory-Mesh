"""Importance scoring utilities."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from ai_memory_layer.config import ImportanceWeights, get_settings


RoleWeight = dict[Literal["system", "user", "assistant"], float]


class ImportanceScorer:
    """Combines recency, role, and explicit hints into a normalized importance score."""

    def __init__(
        self,
        *,
        role_weights: RoleWeight | None = None,
        weights: ImportanceWeights | None = None,
    ) -> None:
        self.role_weights = role_weights or {
            "system": 0.9,
            "assistant": 0.5,
            "user": 0.7,
        }
        self.weights = (weights or get_settings().importance_weights).normalized()

    def score(
        self,
        *,
        created_at: datetime,
        role: str,
        explicit_importance: float | None,
    ) -> float:
        now = datetime.now(timezone.utc)
        recency_seconds = (now - created_at.astimezone(timezone.utc)).total_seconds()
        recency_component = max(0.0, 1.0 - recency_seconds / (60 * 60 * 24))  # decay in 24h
        role_component = self.role_weights.get(role, 0.5)
        explicit_component = explicit_importance if explicit_importance is not None else 0.0

        score = (
            recency_component * self.weights.recency
            + role_component * self.weights.role
            + explicit_component * self.weights.explicit
        )
        return max(0.0, min(score, 1.0))
