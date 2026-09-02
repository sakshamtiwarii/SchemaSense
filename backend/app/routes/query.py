import logging

from fastapi import APIRouter, HTTPException, Request

from app.config import settings
from app.core.correction import answer_question
from app.core.introspection import get_cached_schema_context
from app.core.rate_limit import enforce_rate_limit
from app.core.session_routing import resolve_pool_and_cache_key
from app.core.sql_chain import LLMConfig, LLMConfigError
from app.schemas.schemas import QueryRequest

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/query")
async def query(request: QueryRequest, http_request: Request) -> dict:
    await enforce_rate_limit(
        http_request,
        key="query",
        limit=settings.rate_limit_query_per_minute,
        window_seconds=60,
    )

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
    except LLMConfigError as exc:
        # Only a key/model problem reaches here — everything else in the
        # pipeline (session lookup, introspection, Redis, execution) falls
        # through to the handler below, so a backend outage is never
        # reported to the caller as "your API key is bad".
        if llm_config is not None:
            # A provider can quote a partially masked form of the caller's own
            # key back in its error text, so log the shape of the failure and
            # never the message itself.
            logger.warning(
                "Bring-your-own-key request rejected by %s: %s",
                llm_config.provider,
                type(exc.__cause__).__name__,
            )
            raise HTTPException(
                status_code=400,
                detail="Couldn't use the provided LLM API key/model — check that it's valid and try again.",
            ) from exc
        # The server's own credentials are the broken ones. That is a 5xx:
        # the caller did nothing wrong and can't fix it by retrying with a
        # different question.
        logger.error("The server's own LLM credentials were rejected: %s", exc)
        raise HTTPException(
            status_code=502,
            detail="The server's LLM credentials aren't working — this is a server-side "
            "misconfiguration, not a problem with your question. Supplying your own API "
            "key in the workspace panel will bypass it.",
        ) from exc
    except Exception as exc:
        # Never log the request itself here — request.llm.api_key lives on it.
        logger.exception("Failed to answer question: %s", request.question)
        raise HTTPException(status_code=502, detail="Upstream service failed to process the question.") from exc
