import asyncio

from ai_memory_layer.rate_limit import InMemoryRateLimiter, RateLimitConfig, _parse_limit


def test_in_memory_rate_limiter_blocks_after_threshold():
    limiter = InMemoryRateLimiter()
    config = RateLimitConfig(amount=2, window_seconds=60)
    async def _exercise():
        result1 = await limiter.hit(config, "client")
        result2 = await limiter.hit(config, "client")
        result3 = await limiter.hit(config, "client")
        return result1, result2, result3

    result1, result2, result3 = asyncio.run(_exercise())

    assert result1.allowed and result2.allowed
    assert result3.allowed is False
    assert result3.count == 3
    assert result3.reset_epoch_ms > 0


def test_parse_limit_variants():
    assert _parse_limit("200/minute") == RateLimitConfig(amount=200, window_seconds=60)
    assert _parse_limit("10 per second").window_seconds == 1

