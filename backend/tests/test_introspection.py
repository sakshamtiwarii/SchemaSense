import pytest

from app.core import introspection


class _FakeConn:
    def __init__(self, rows):
        self._rows = rows

    async def fetch(self, query):
        return self._rows

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakePool:
    def __init__(self, rows):
        self.rows = rows

    def acquire(self):
        return _FakeConn(self.rows)


class _FakeRedis:
    def __init__(self):
        self.store = {}

    async def get(self, key):
        return self.store.get(key)

    async def set(self, key, value, ex=None):
        self.store[key] = value


@pytest.mark.asyncio
async def test_groups_columns_by_table_in_order():
    rows = [
        {"table_name": "orders", "column_name": "id", "data_type": "integer"},
        {"table_name": "orders", "column_name": "revenue", "data_type": "numeric"},
        {"table_name": "products", "column_name": "id", "data_type": "integer"},
    ]
    pool = _FakePool(rows)

    context = await introspection.get_schema_context(pool)

    assert context == ("Table orders: id (integer), revenue (numeric)\nTable products: id (integer)")


@pytest.mark.asyncio
async def test_empty_schema_returns_empty_string():
    pool = _FakePool([])
    context = await introspection.get_schema_context(pool)
    assert context == ""


@pytest.mark.asyncio
async def test_caches_schema_context(monkeypatch):
    pool = _FakePool([{"table_name": "orders", "column_name": "id", "data_type": "integer"}])
    fake_redis = _FakeRedis()
    monkeypatch.setattr(introspection, "get_redis", lambda: fake_redis)

    first = await introspection.get_cached_schema_context(pool, ttl_seconds=60)
    pool.rows = []  # if the cache is actually used, this change must not affect the second call
    second = await introspection.get_cached_schema_context(pool, ttl_seconds=60)

    assert first == second == "Table orders: id (integer)"


@pytest.mark.asyncio
async def test_force_refresh_bypasses_cache(monkeypatch):
    pool = _FakePool([{"table_name": "orders", "column_name": "id", "data_type": "integer"}])
    fake_redis = _FakeRedis()
    monkeypatch.setattr(introspection, "get_redis", lambda: fake_redis)

    await introspection.get_cached_schema_context(pool, ttl_seconds=60)

    pool.rows = [{"table_name": "products", "column_name": "id", "data_type": "integer"}]
    refreshed = await introspection.get_cached_schema_context(pool, ttl_seconds=60, force_refresh=True)

    assert refreshed == "Table products: id (integer)"
