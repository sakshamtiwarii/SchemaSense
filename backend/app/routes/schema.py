from fastapi import APIRouter, HTTPException, Query, Request

from app.config import settings
from app.core.introspection import get_cached_schema_context
from app.core.rate_limit import enforce_rate_limit
from app.core.session_routing import resolve_pool_and_cache_key
from app.schemas.schemas import SchemaResponse

router = APIRouter()


@router.get("/schema", response_model=SchemaResponse)
async def schema(
    http_request: Request,
    refresh: bool = Query(False, description="Bypass the Redis cache and re-read the schema"),
    session_id: str | None = Query(None, description="Demo session id to inspect instead of the default database"),
) -> SchemaResponse:
    await enforce_rate_limit(
        http_request,
        key="schema",
        limit=settings.rate_limit_schema_per_minute,
        window_seconds=60,
    )

    resolved = await resolve_pool_and_cache_key(session_id)
    if resolved is None:
        raise HTTPException(
            status_code=404,
            detail="Demo session not found or expired. Reconnect via POST /demo/connect.",
        )
    pool, cache_key = resolved

    context = await get_cached_schema_context(
        pool, settings.schema_cache_ttl_seconds, force_refresh=refresh, cache_key=cache_key
    )
    return SchemaResponse(schema_context=context)
