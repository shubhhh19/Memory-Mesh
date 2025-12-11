"""Distributed tracing with OpenTelemetry."""

from __future__ import annotations

import os
from typing import Any

from fastapi import Request
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Span, Tracer

from ai_memory_layer.config import get_settings

_tracer: Tracer | None = None
_tracer_provider: TracerProvider | None = None


def init_tracing(app: Any) -> None:
    """Initialize OpenTelemetry tracing."""
    global _tracer, _tracer_provider
    
    settings = get_settings()
    
    # Only enable tracing if explicitly configured
    jaeger_endpoint = os.environ.get("JAEGER_ENDPOINT")
    if not jaeger_endpoint:
        return
    
    # Create resource
    resource = Resource.create(
        {
            "service.name": settings.app_name,
            "service.version": "0.1.0",
            "deployment.environment": settings.environment,
        }
    )
    
    # Create tracer provider
    _tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(_tracer_provider)
    
    # Add Jaeger exporter
    jaeger_exporter = JaegerExporter(
        agent_host_name=jaeger_endpoint.split(":")[0] if ":" in jaeger_endpoint else jaeger_endpoint,
        agent_port=int(jaeger_endpoint.split(":")[1]) if ":" in jaeger_endpoint else 6831,
    )
    span_processor = BatchSpanProcessor(jaeger_exporter)
    _tracer_provider.add_span_processor(span_processor)
    
    # Get tracer
    _tracer = trace.get_tracer(__name__)
    
    # Instrument FastAPI
    FastAPIInstrumentor.instrument_app(app)
    
    return _tracer


def get_tracer() -> Tracer | None:
    """Get the global tracer instance."""
    return _tracer


def get_current_span() -> Span | None:
    """Get the current active span."""
    if _tracer is None:
        return None
    return trace.get_current_span()


def add_span_attributes(attributes: dict[str, Any]) -> None:
    """Add attributes to the current span."""
    span = get_current_span()
    if span:
        for key, value in attributes.items():
            span.set_attribute(key, str(value))


def trace_request(request: Request) -> None:
    """Add request information to the current span."""
    span = get_current_span()
    if span:
        span.set_attribute("http.method", request.method)
        span.set_attribute("http.url", str(request.url))
        span.set_attribute("http.route", request.url.path)
        if request.client:
            span.set_attribute("http.client_ip", request.client.host)


def shutdown_tracing() -> None:
    """Shutdown tracing and flush remaining spans."""
    global _tracer_provider
    if _tracer_provider:
        _tracer_provider.shutdown()
        _tracer_provider = None

