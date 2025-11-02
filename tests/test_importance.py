from datetime import datetime, timedelta, timezone

from ai_memory_layer.services.importance import ImportanceScorer


def test_importance_scoring_respects_recency_and_role():
    scorer = ImportanceScorer()
    now = datetime.now(timezone.utc)
    score_recent = scorer.score(created_at=now, role="system", explicit_importance=None)
    score_old = scorer.score(
        created_at=now - timedelta(days=2),
        role="assistant",
        explicit_importance=None,
    )
    assert score_recent > score_old
