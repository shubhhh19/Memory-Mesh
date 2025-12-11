"""Monitoring and alerting service."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from ai_memory_layer.config import get_settings
from ai_memory_layer.database import check_database_health
from ai_memory_layer.logging import get_logger
from ai_memory_layer.metrics import get_metrics

logger = get_logger(component="monitoring")


class MonitoringService:
    """Service for monitoring system health and triggering alerts."""

    def __init__(self):
        self.settings = get_settings()
        self.alert_handlers: list[callable] = []

    def register_alert_handler(self, handler: callable) -> None:
        """Register an alert handler function."""
        self.alert_handlers.append(handler)

    async def check_health(self) -> dict[str, Any]:
        """Perform comprehensive health check."""
        health_status = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "healthy",
            "checks": {},
        }

        # Database health
        db_healthy, db_latency = await check_database_health()
        health_status["checks"]["database"] = {
            "healthy": db_healthy,
            "latency_ms": db_latency * 1000 if db_latency else None,
        }

        if not db_healthy:
            health_status["status"] = "unhealthy"
            await self._trigger_alert("database_unhealthy", "Database health check failed")

        # Redis health (if configured)
        if self.settings.redis_url:
            try:
                import redis.asyncio as redis

                client = redis.from_url(self.settings.redis_url)
                await client.ping()
                await client.close()
                health_status["checks"]["redis"] = {"healthy": True}
            except Exception as e:
                health_status["checks"]["redis"] = {"healthy": False, "error": str(e)}
                health_status["status"] = "unhealthy"
                await self._trigger_alert("redis_unhealthy", f"Redis health check failed: {e}")

        # Metrics summary
        try:
            metrics = get_metrics()
            health_status["checks"]["metrics"] = {
                "healthy": True,
                "request_count": metrics.get("http_requests_total", 0),
                "error_rate": metrics.get("error_rate", 0.0),
            }
        except Exception as e:
            health_status["checks"]["metrics"] = {"healthy": False, "error": str(e)}

        return health_status

    async def _trigger_alert(self, alert_type: str, message: str, severity: str = "warning") -> None:
        """Trigger an alert to all registered handlers."""
        alert = {
            "type": alert_type,
            "message": message,
            "severity": severity,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        logger.warning("alert_triggered", **alert)

        for handler in self.alert_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(alert)
                else:
                    handler(alert)
            except Exception as e:
                logger.error("alert_handler_failed", handler=str(handler), error=str(e))

    async def get_system_metrics(self) -> dict[str, Any]:
        """Get comprehensive system metrics."""
        metrics = get_metrics()
        health = await self.check_health()

        return {
            "health": health,
            "metrics": metrics,
            "settings": {
                "environment": self.settings.environment,
                "async_embeddings": self.settings.async_embeddings,
                "cache_enabled": self.settings.cache_enabled,
            },
        }


# Global monitoring service instance
_monitoring_service: MonitoringService | None = None


def get_monitoring_service() -> MonitoringService:
    """Get the global monitoring service instance."""
    global _monitoring_service
    if _monitoring_service is None:
        _monitoring_service = MonitoringService()
    return _monitoring_service

