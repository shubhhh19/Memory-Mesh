import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_api_key_required_when_configured(
    client_builder, settings_override
):
    settings_override(api_keys=["test-key"])
    from ai_memory_layer.config import get_settings

    assert "test-key" in get_settings().api_keys

    async with client_builder() as client:
        response = await client.post(
            "/v1/messages",
            json={
                "tenant_id": "tenant-sec",
                "conversation_id": "c1",
                "role": "user",
                "content": "Secure",
            },
        )
        assert response.status_code == 401

        response = await client.post(
            "/v1/messages",
            headers={"x-api-key": "test-key"},
            json={
                "tenant_id": "tenant-sec",
                "conversation_id": "c1",
                "role": "user",
                "content": "Secure",
            },
        )
        assert response.status_code == 200
