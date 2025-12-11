"""Utility helpers for input sanitization."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


class MetadataValidationError(ValueError):
    """Raised when metadata payloads are invalid."""


def sanitize_metadata(
    metadata: Mapping[str, Any],
    *,
    max_depth: int = 4,
    max_items: int = 50,
    max_string_length: int = 2048,
) -> dict[str, Any]:
    """Sanitize metadata by enforcing type safety, depth, and size limits."""

    def _clean(value: Any, depth: int) -> Any:
        if depth > max_depth:
            raise MetadataValidationError("metadata exceeds maximum nesting depth")
        if isinstance(value, Mapping):
            if len(value) > max_items:
                raise MetadataValidationError("metadata object has too many keys")
            return {str(k): _clean(v, depth + 1) for k, v in value.items()}
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            if len(value) > max_items:
                raise MetadataValidationError("metadata array has too many items")
            return [_clean(item, depth + 1) for item in value]
        if isinstance(value, (str, int, float, bool)) or value is None:
            if isinstance(value, str) and len(value) > max_string_length:
                return value[:max_string_length]
            return value
        raise MetadataValidationError(f"unsupported metadata type: {type(value).__name__}")

    cleaned = _clean(dict(metadata), depth=1)
    if not isinstance(cleaned, dict):
        raise MetadataValidationError("metadata must be an object")
    return cleaned
