from app.config import settings


async def execute_query(pool, sql: str) -> list[dict]:
    bounded_sql = _apply_row_limit(sql, settings.max_result_rows)
    async with pool.acquire() as conn:
        # A transaction-level read-only guarantee, enforced by Postgres
        # itself regardless of the connecting role's actual grants. This is
        # what makes it safe to run generated SQL against a database we
        # don't control the role setup for (e.g. a demo session's external
        # database), not just the one we seeded ourselves.
        async with conn.transaction(readonly=True):
            records = await conn.fetch(bounded_sql)
    return [dict(r) for r in records]


def _apply_row_limit(sql: str, max_rows: int) -> str:
    stripped = sql.strip().rstrip(";")
    if "LIMIT" in stripped.upper():
        return stripped
    return f"{stripped} LIMIT {max_rows}"
