import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    response = await client.get("/v1/admin/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in {"ok", "degraded"}
    assert "uptime_seconds" in data
    assert "version" in data
    assert data["embedding"] in {"ok", "failed", "skipped"}


@pytest.mark.asyncio
async def test_readiness_endpoint(client: AsyncClient):
    response = await client.get("/v1/admin/readiness")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in {"ok", "degraded", "down"}
    assert "uptime_seconds" in data
    assert data["embedding"] in {"ok", "failed", "skipped"}
