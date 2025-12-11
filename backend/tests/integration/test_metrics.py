import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_metrics_endpoint(client: AsyncClient):
    response = await client.get("/metrics", headers={"Origin": "https://example.com"})
    assert response.status_code == 200
    assert "aiml_requests_total" in response.text
    assert response.headers.get("access-control-allow-origin") in {"*", "https://example.com"}
