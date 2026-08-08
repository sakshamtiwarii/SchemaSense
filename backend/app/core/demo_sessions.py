import asyncio
import secrets
import time

import asyncpg

from app.config import settings


class DemoSessionLimitError(Exception):
    pass


class DemoSession:
    __slots__ = ("pool", "created_at", "last_used")

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool
        self.created_at = time.monotonic()
        self.last_used = self.created_at


# Process-local only, by design: a demo connection string is never written
# to Redis, disk, or logs. This means sessions aren't shared across worker
# processes — run a single API worker, or move this to a per-tenant store
# if that limitation stops being acceptable.
_sessions: dict[str, DemoSession] = {}


async def create_session(dsn: str) -> str:
    _reap_expired()
    if len(_sessions) >= settings.max_demo_sessions:
        raise DemoSessionLimitError()

    pool = await asyncpg.create_pool(dsn, min_size=1, max_size=3, timeout=5, command_timeout=10)
    async with pool.acquire() as conn:
        await conn.fetchval("SELECT 1")

    session_id = secrets.token_urlsafe(24)
    _sessions[session_id] = DemoSession(pool)
    return session_id


def get_session(session_id: str) -> DemoSession | None:
    session = _sessions.get(session_id)
    if session is None or _is_expired(session):
        return None
    session.last_used = time.monotonic()
    return session


async def close_session(session_id: str) -> bool:
    session = _sessions.pop(session_id, None)
    if session is None:
        return False
    await session.pool.close()
    return True


async def close_all_sessions() -> None:
    for session_id in list(_sessions):
        await close_session(session_id)


def _is_expired(session: DemoSession) -> bool:
    return (time.monotonic() - session.last_used) > settings.demo_session_ttl_seconds


def _reap_expired() -> None:
    expired = [sid for sid, s in _sessions.items() if _is_expired(s)]
    for sid in expired:
        session = _sessions.pop(sid, None)
        if session is not None:
            asyncio.create_task(session.pool.close())
