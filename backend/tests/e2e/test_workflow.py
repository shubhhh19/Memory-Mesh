import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_full_workflow(client: AsyncClient):
    payload = {
        "tenant_id": "tenant-e2e",
        "conversation_id": "conv-e2e",
        "role": "assistant",
        "content": "Your order has shipped.",
    }
    response = await client.post("/v1/messages", json=payload)
    assert response.status_code == 200
    message_id = response.json()["id"]

    retention_response = await client.post(
        "/v1/admin/retention/run",
        json={"tenant_id": "tenant-e2e", "actions": ["archive"], "dry_run": True},
    )
    assert retention_response.status_code == 200
    assert retention_response.json()["archived"] == 0

    # Ensure fetching works after retention dry-run
    get_response = await client.get(f"/v1/messages/{message_id}")
    assert get_response.status_code == 200
