import pytest

from app.core.executor import execute_query


class _FakeTransaction:
    def __init__(self, readonly):
        self.readonly = readonly

    async def __aenter__(self):
        assert self.readonly is True, "execute_query must run inside a READ ONLY transaction"
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeConn:
    def __init__(self):
        self.fetched_sql = None

    def transaction(self, readonly=False):
        return _FakeTransaction(readonly)

    async def fetch(self, sql):
        self.fetched_sql = sql
        return [{"id": 1}]

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakePool:
    def __init__(self):
        self.conn = _FakeConn()

    def acquire(self):
        return self.conn


@pytest.mark.asyncio
async def test_execute_query_runs_inside_readonly_transaction():
    pool = _FakePool()

    rows = await execute_query(pool, "SELECT * FROM orders")

    assert rows == [{"id": 1}]


@pytest.mark.asyncio
async def test_execute_query_appends_limit_when_missing():
    pool = _FakePool()

    await execute_query(pool, "SELECT * FROM orders")

    assert "LIMIT 200" in pool.conn.fetched_sql


@pytest.mark.asyncio
async def test_execute_query_respects_existing_limit():
    pool = _FakePool()

    await execute_query(pool, "SELECT * FROM orders LIMIT 5")

    assert pool.conn.fetched_sql.count("LIMIT") == 1
