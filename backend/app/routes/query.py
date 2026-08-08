import logging

from fastapi import APIRouter, HTTPException

from app.config import settings
from app.core.correction import answer_question
from app.core.introspection import get_cached_schema_context
from app.core.session_routing import resolve_pool_and_cache_key
from app.core.sql_chain import LLMConfig
from app.schemas.schemas import QueryRequest

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/query")
async def query(request: QueryRequest) -> dict:
    llm_config = (
        LLMConfig(provider=request.llm.provider, api_key=request.llm.api_key, model=request.llm.model)
        if request.llm
        else None
    )

    try:
        resolved = await resolve_pool_and_cache_key(request.session_id)
        if resolved is None:
            raise HTTPException(
                status_code=404,
                detail="Demo session not found or expired. Reconnect via POST /demo/connect.",
            )
        pool, cache_key = resolved

        schema_context = await get_cached_schema_context(
            pool, settings.schema_cache_ttl_seconds, cache_key=cache_key
        )
        return await answer_question(request.question, schema_context, pool, llm_config)
    except HTTPException:
        raise
    except Exception as exc:
        # Never log the request itself here — request.llm.api_key lives on it.
        logger.exception("Failed to answer question: %s", request.question)
        if llm_config is not None:
            raise HTTPException(
                status_code=400,
                detail="Couldn't use the provided LLM API key/model — check that it's valid and try again.",
            ) from exc
        raise HTTPException(status_code=502, detail="Upstream service failed to process the question.") from exc
