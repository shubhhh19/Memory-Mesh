#!/usr/bin/env python3
"""Lightweight async load test helper for the memory layer API."""

from __future__ import annotations

import argparse
import asyncio
import random
import string
import time
from typing import Any
import uuid

import httpx


def _random_text(prefix: str) -> str:
    suffix = "".join(random.choices(string.ascii_letters, k=8))
    return f"{prefix}-{suffix}"


async def _send_message(client: httpx.AsyncClient, payload: dict[str, Any]) -> tuple[bool, float]:
    start = time.perf_counter()
    try:
        response = await client.post("/v1/messages", json=payload)
        success = response.is_success
    except Exception:
        success = False
    return success, time.perf_counter() - start


async def _worker(
    client: httpx.AsyncClient,
    payloads: list[dict[str, Any]],
    results: list[float],
) -> None:
    for payload in payloads:
        ok, duration = await _send_message(client, payload)
        if ok:
            results.append(duration)


async def run_load(
    base_url: str,
    api_key: str | None,
    requests: int,
    concurrency: int,
    tenant_id: str,
) -> None:
    headers = {"x-api-key": api_key} if api_key else {}
    payloads = [
        {
            "tenant_id": tenant_id,
            "conversation_id": str(uuid.uuid4()),
            "role": "user",
            "content": _random_text("load-test"),
        }
        for _ in range(requests)
    ]
    batches = [payloads[i::concurrency] for i in range(concurrency)]
    results: list[float] = []
    async with httpx.AsyncClient(base_url=base_url, timeout=10.0, headers=headers) as client:
        tasks = [_worker(client, batch, results) for batch in batches if batch]
        await asyncio.gather(*tasks)
    if not results:
        print("No successful requests recorded.")
        return
    total = len(results)
    total_time = sum(results)
    print(f"Sent {requests} requests with concurrency {concurrency}")
    print(f"Successful: {total}/{requests} ({total / max(1, requests) * 100:.1f}%)")
    print(f"Avg latency: {total_time/total:.4f}s")
    print(f"P95 latency: {sorted(results)[int(total * 0.95) - 1]:.4f}s")


def main() -> None:
    parser = argparse.ArgumentParser(description="Simple load test for AI Memory Layer")
    parser.add_argument("--base-url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--api-key", default=None, help="API key to include in requests")
    parser.add_argument("--requests", type=int, default=100, help="Total number of requests to send")
    parser.add_argument("--concurrency", type=int, default=10, help="Number of concurrent workers")
    parser.add_argument("--tenant-id", default="load-test", help="Tenant ID to use for requests")
    args = parser.parse_args()
    asyncio.run(
        run_load(
            base_url=args.base_url,
            api_key=args.api_key,
            requests=args.requests,
            concurrency=args.concurrency,
            tenant_id=args.tenant_id,
        )
    )


if __name__ == "__main__":
    main()
