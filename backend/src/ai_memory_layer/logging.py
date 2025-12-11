"""Logging configuration for the AI Memory Layer service."""

from __future__ import annotations

import logging
import sys
from typing import Any

try:  # pragma: no cover - optional dependency fallback
    import structlog
except ImportError:  # pragma: no cover
    structlog = None  # type: ignore[assignment]

from ai_memory_layer.config import get_settings
from ai_memory_layer.middleware_module import request_id_ctx_var


def configure_logging() -> None:
    """Configure standard logging + structlog when available."""
    settings = get_settings()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stdout,
    )
    if structlog is None:
        logging.getLogger(__name__).warning("structlog not installed, falling back to std logging")
        return
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            _inject_request_id,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(**kwargs: Any):
    """Helper to retrieve a logger with bound context."""
    if structlog is None:
        logger = logging.getLogger("ai_memory_layer")
        if kwargs:
            return logging.LoggerAdapter(logger, extra=kwargs)
        return logger
    logger = structlog.get_logger()
    if kwargs:
        return logger.bind(**kwargs)
    return logger


def _inject_request_id(logger, method_name, event_dict):
    request_id = request_id_ctx_var.get()
    if request_id:
        event_dict["request_id"] = request_id
    return event_dict
