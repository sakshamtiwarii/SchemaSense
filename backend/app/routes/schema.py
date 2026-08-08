from fastapi import APIRouter, Query

from app.config import settings
from app.core.introspection import get_cached_schema_context
from app.db.postgres import get_db_pool
from app.schemas.schemas import SchemaResponse

router = APIRouter()


@router.get("/schema", response_model=SchemaResponse)
async def schema(
    refresh: bool = Query(False, description="Bypass the Redis cache and re-read the schema"),
) -> SchemaResponse:
    pool = await get_db_pool()
    context = await get_cached_schema_context(pool, settings.schema_cache_ttl_seconds, force_refresh=refresh)
    return SchemaResponse(schema_context=context)
