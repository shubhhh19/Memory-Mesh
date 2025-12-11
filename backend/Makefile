PYTHON ?= python3
UVICORN = uvicorn ai_memory_layer.main:app --host 0.0.0.0 --port 8000

.PHONY: install run format lint test migrate

install:
	uv sync

run:
	$(UVICORN)

format:
	ruff check --select I --fix .

lint:
	ruff check .
	mypy src

test:
	pytest

migrate:
	alembic upgrade head
