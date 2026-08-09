import pytest
from fastapi import HTTPException

from app.core import rate_limit
from app.core.rate_limit import enforce_rate_limit


class _FakeClient:
    def __init__(self, host):
        self.host = host


class _FakeRequest:
    def __init__(self, headers=None, client_host="1.2.3.4"):
        self.headers = headers or {}
        self.client = _FakeClient(client_host)


class _FakeRedis:
    def __init__(self):
        self.store = {}
        self.fail = False

    async def incr(self, key):
        if self.fail:
            raise ConnectionError("redis down")
        self.store[key] = self.store.get(key, 0) + 1
        return self.store[key]

    async def expire(self, key, seconds):
        pass


@pytest.fixture(autouse=True)
def fake_redis(monkeypatch):
    fake = _FakeRedis()
    monkeypatch.setattr(rate_limit, "get_redis", lambda: fake)
    return fake


@pytest.mark.asyncio
async def test_allows_requests_under_the_limit():
    request = _FakeRequest()
    for _ in range(5):
        await enforce_rate_limit(request, key="test", limit=5, window_seconds=60)


@pytest.mark.asyncio
async def test_blocks_requests_over_the_limit():
    request = _FakeRequest()
    for _ in range(3):
        await enforce_rate_limit(request, key="test", limit=3, window_seconds=60)

    with pytest.raises(HTTPException) as exc_info:
        await enforce_rate_limit(request, key="test", limit=3, window_seconds=60)

    assert exc_info.value.status_code == 429
    assert "Retry-After" in exc_info.value.headers


@pytest.mark.asyncio
async def test_different_ips_have_independent_limits():
    a = _FakeRequest(client_host="1.1.1.1")
    b = _FakeRequest(client_host="2.2.2.2")

    for _ in range(3):
        await enforce_rate_limit(a, key="test", limit=3, window_seconds=60)

    # b hasn't made any requests yet, so it should not be blocked by a's usage.
    await enforce_rate_limit(b, key="test", limit=3, window_seconds=60)


@pytest.mark.asyncio
async def test_prefers_x_forwarded_for_over_direct_client_host():
    a = _FakeRequest(headers={"x-forwarded-for": "9.9.9.9, 5.5.5.5"}, client_host="127.0.0.1")
    for _ in range(3):
        await enforce_rate_limit(a, key="test", limit=3, window_seconds=60)

    with pytest.raises(HTTPException):
        await enforce_rate_limit(a, key="test", limit=3, window_seconds=60)

    # Same direct client_host (both behind the same proxy), different forwarded IP.
    b = _FakeRequest(headers={"x-forwarded-for": "8.8.8.8"}, client_host="127.0.0.1")
    await enforce_rate_limit(b, key="test", limit=3, window_seconds=60)


@pytest.mark.asyncio
async def test_different_route_keys_have_independent_limits():
    request = _FakeRequest()
    for _ in range(3):
        await enforce_rate_limit(request, key="query", limit=3, window_seconds=60)

    await enforce_rate_limit(request, key="schema", limit=3, window_seconds=60)


@pytest.mark.asyncio
async def test_fails_open_when_redis_is_unreachable(fake_redis):
    fake_redis.fail = True
    request = _FakeRequest()

    for _ in range(10):
        await enforce_rate_limit(request, key="test", limit=1, window_seconds=60)


@pytest.mark.asyncio
async def test_window_resets_after_the_boundary(monkeypatch):
    request = _FakeRequest()

    monkeypatch.setattr(rate_limit.time, "time", lambda: 0)
    for _ in range(3):
        await enforce_rate_limit(request, key="test", limit=3, window_seconds=60)
    with pytest.raises(HTTPException):
        await enforce_rate_limit(request, key="test", limit=3, window_seconds=60)

    monkeypatch.setattr(rate_limit.time, "time", lambda: 61)
    await enforce_rate_limit(request, key="test", limit=3, window_seconds=60)
