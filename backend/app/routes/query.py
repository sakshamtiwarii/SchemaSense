import logging

from fastapi import APIRouter, HTTPException

from app.config import settings
from app.core.correction import answer_question
from app.core.demo_sessions import get_session
from app.core.introspection import SCHEMA_CACHE_KEY, demo_cache_key, get_cached_schema_context
from app.db.postgres import get_db_pool
from app.schemas.schemas import QueryRequest

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/query")
async def query(request: QueryRequest) -> dict:
    try:
        if request.session_id:
            session = get_session(request.session_id)
            if session is None:
                raise HTTPException(
                    status_code=404,
                    detail="Demo session not found or expired. Reconnect via POST /demo/connect.",
                )
            pool = session.pool
            cache_key = demo_cache_key(request.session_id)
        else:
            pool = await get_db_pool()
            cache_key = SCHEMA_CACHE_KEY

        schema_context = await get_cached_schema_context(
            pool, settings.schema_cache_ttl_seconds, cache_key=cache_key
        )
        return await answer_question(request.question, schema_context, pool)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to answer question: %s", request.question)
        raise HTTPException(status_code=502, detail="Upstream service failed to process the question.") from exc
