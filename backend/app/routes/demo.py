import logging

from fastapi import APIRouter, HTTPException, Response

from app.config import settings
from app.core.demo_sessions import DemoSessionLimitError, close_session, create_session
from app.core.introspection import demo_cache_key
from app.core.network_guard import UnsafeHostError, assert_host_is_safe
from app.db.redis_client import get_redis
from app.schemas.schemas import DemoConnectRequest, DemoConnectResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/demo")


@router.post("/connect", response_model=DemoConnectResponse)
async def connect(request: DemoConnectRequest) -> DemoConnectResponse:
    try:
        await assert_host_is_safe(request.connection_string)
    except UnsafeHostError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        session_id = await create_session(request.connection_string)
    except DemoSessionLimitError as exc:
        raise HTTPException(
            status_code=429, detail="Too many active demo sessions — try again shortly."
        ) from exc
    except Exception as exc:
        # Never echo the raw driver exception back to the client: it can
        # embed connection details. Log server-side, return a generic message.
        logger.exception("Failed to open a demo database connection")
        raise HTTPException(
            status_code=400,
            detail="Could not connect with the provided connection string. Check the host, "
            "credentials, and that the database is reachable.",
        ) from exc

    return DemoConnectResponse(session_id=session_id, expires_in_seconds=settings.demo_session_ttl_seconds)


@router.delete("/connect/{session_id}", status_code=204)
async def disconnect(session_id: str) -> Response:
    await close_session(session_id)
    await get_redis().delete(demo_cache_key(session_id))
    return Response(status_code=204)
