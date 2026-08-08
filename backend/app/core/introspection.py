from app.db.redis_client import get_redis

SCHEMA_CACHE_KEY = "nlsql:schema_context"


async def get_schema_context(pool) -> str:
    query = """
        SELECT table_name, column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'public'
        ORDER BY table_name, ordinal_position;
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(query)

    tables: dict[str, list[str]] = {}
    for r in rows:
        tables.setdefault(r["table_name"], []).append(f'{r["column_name"]} ({r["data_type"]})')

    lines = []
    for table, cols in tables.items():
        lines.append(f"Table {table}: " + ", ".join(cols))
    return "\n".join(lines)


async def get_cached_schema_context(
    pool,
    ttl_seconds: int,
    force_refresh: bool = False,
    cache_key: str = SCHEMA_CACHE_KEY,
) -> str:
    r = get_redis()

    if not force_refresh:
        cached = await r.get(cache_key)
        if cached is not None:
            return cached

    context = await get_schema_context(pool)
    await r.set(cache_key, context, ex=ttl_seconds)
    return context


def demo_cache_key(session_id: str) -> str:
    return f"{SCHEMA_CACHE_KEY}:demo:{session_id}"
