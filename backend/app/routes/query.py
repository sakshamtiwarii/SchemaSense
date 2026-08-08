import logging

from fastapi import APIRouter, HTTPException

from app.config import settings
from app.core.correction import answer_question
from app.core.introspection import get_cached_schema_context
from app.db.postgres import get_db_pool
from app.schemas.schemas import QueryRequest

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/query")
async def query(request: QueryRequest) -> dict:
    try:
        pool = await get_db_pool()
        schema_context = await get_cached_schema_context(pool, settings.schema_cache_ttl_seconds)
        return await answer_question(request.question, schema_context, pool)
    except Exception as exc:
        logger.exception("Failed to answer question: %s", request.question)
        raise HTTPException(status_code=502, detail="Upstream service failed to process the question.") from exc
