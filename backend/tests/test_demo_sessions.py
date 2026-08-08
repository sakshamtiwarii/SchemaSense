import time

import pytest

from app.core import demo_sessions


class _FakeConn:
    async def fetchval(self, query):
        return 1

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakePool:
    def __init__(self):
        self.closed = False

    def acquire(self):
        return _FakeConn()

    async def close(self):
        self.closed = True


@pytest.fixture(autouse=True)
def _clean_sessions():
    demo_sessions._sessions.clear()
    yield
    demo_sessions._sessions.clear()


@pytest.mark.asyncio
async def test_create_session_returns_opaque_id(monkeypatch):
    async def fake_create_pool(dsn, **kwargs):
        return _FakePool()

    monkeypatch.setattr(demo_sessions.asyncpg, "create_pool", fake_create_pool)

    session_id = await demo_sessions.create_session("postgresql://u:p@example.com/db")

    assert isinstance(session_id, str)
    assert len(session_id) > 20
    assert demo_sessions.get_session(session_id) is not None


@pytest.mark.asyncio
async def test_expired_session_is_not_returned(monkeypatch):
    async def fake_create_pool(dsn, **kwargs):
        return _FakePool()

    monkeypatch.setattr(demo_sessions.asyncpg, "create_pool", fake_create_pool)
    monkeypatch.setattr(demo_sessions.settings, "demo_session_ttl_seconds", 0)

    session_id = await demo_sessions.create_session("postgresql://u:p@example.com/db")
    time.sleep(0.01)

    assert demo_sessions.get_session(session_id) is None


@pytest.mark.asyncio
async def test_session_limit_is_enforced(monkeypatch):
    async def fake_create_pool(dsn, **kwargs):
        return _FakePool()

    monkeypatch.setattr(demo_sessions.asyncpg, "create_pool", fake_create_pool)
    monkeypatch.setattr(demo_sessions.settings, "max_demo_sessions", 1)

    await demo_sessions.create_session("postgresql://u:p@example.com/db1")

    with pytest.raises(demo_sessions.DemoSessionLimitError):
        await demo_sessions.create_session("postgresql://u:p@example.com/db2")


@pytest.mark.asyncio
async def test_close_session_closes_pool_and_forgets_it(monkeypatch):
    async def fake_create_pool(dsn, **kwargs):
        return _FakePool()

    monkeypatch.setattr(demo_sessions.asyncpg, "create_pool", fake_create_pool)

    session_id = await demo_sessions.create_session("postgresql://u:p@example.com/db")
    pool = demo_sessions.get_session(session_id).pool

    closed = await demo_sessions.close_session(session_id)

    assert closed is True
    assert pool.closed is True
    assert demo_sessions.get_session(session_id) is None


@pytest.mark.asyncio
async def test_closing_unknown_session_is_a_no_op():
    assert await demo_sessions.close_session("does-not-exist") is False
