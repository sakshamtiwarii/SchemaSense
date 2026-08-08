import pytest

from app.core import demo_sessions, session_routing


class _FakeConn:
    async def fetchval(self, query):
        return 1

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakePool:
    def acquire(self):
        return _FakeConn()

    async def close(self):
        pass


@pytest.fixture(autouse=True)
def _clean_sessions():
    demo_sessions._sessions.clear()
    yield
    demo_sessions._sessions.clear()


@pytest.mark.asyncio
async def test_no_session_id_resolves_to_default_pool(monkeypatch):
    default_pool = _FakePool()

    async def fake_get_db_pool():
        return default_pool

    monkeypatch.setattr(session_routing, "get_db_pool", fake_get_db_pool)

    pool, cache_key = await session_routing.resolve_pool_and_cache_key(None)

    assert pool is default_pool
    assert cache_key == session_routing.SCHEMA_CACHE_KEY


@pytest.mark.asyncio
async def test_valid_session_id_resolves_to_its_pool(monkeypatch):
    async def fake_create_pool(dsn, **kwargs):
        return _FakePool()

    monkeypatch.setattr(demo_sessions.asyncpg, "create_pool", fake_create_pool)
    session_id = await demo_sessions.create_session("postgresql://u:p@example.com/db")

    resolved = await session_routing.resolve_pool_and_cache_key(session_id)

    assert resolved is not None
    pool, cache_key = resolved
    assert pool is demo_sessions.get_session(session_id).pool
    assert cache_key == session_routing.demo_cache_key(session_id)


@pytest.mark.asyncio
async def test_unknown_session_id_resolves_to_none():
    assert await session_routing.resolve_pool_and_cache_key("does-not-exist") is None
