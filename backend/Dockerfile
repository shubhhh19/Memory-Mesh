# syntax=docker/dockerfile:1.6
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential libpq-dev curl && \
    rm -rf /var/lib/apt/lists/*

# Add non-root user
RUN addgroup --system app && adduser --system --ingroup app app

COPY pyproject.toml uv.lock README.md ./
COPY alembic.ini ./
COPY alembic ./alembic
COPY src ./src
COPY static ./static

RUN pip install --upgrade pip && \
    pip install --no-cache-dir uv && \
    uv sync --frozen --no-dev

USER app

EXPOSE 8000

CMD [".venv/bin/uvicorn", "ai_memory_layer.main:app", "--host", "0.0.0.0", "--port", "8000"]

