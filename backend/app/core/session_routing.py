from app.core.demo_sessions import get_session
from app.core.introspection import SCHEMA_CACHE_KEY, demo_cache_key
from app.db.postgres import get_db_pool


async def resolve_pool_and_cache_key(session_id: str | None):
    """Resolve which database pool + schema cache key a request should use.

    Returns None if a session_id was given but no matching demo session
    exists (expired or never created) — callers turn that into a 404 with
    their own wording, since that's an HTTP concern this module doesn't own.
    """
    if session_id:
        session = get_session(session_id)
        if session is None:
            return None
        return session.pool, demo_cache_key(session_id)

    pool = await get_db_pool()
    return pool, SCHEMA_CACHE_KEY
