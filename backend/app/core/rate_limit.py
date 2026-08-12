import time

from fastapi import HTTPException, Request

from app.db.redis_client import get_redis


async def enforce_rate_limit(request: Request, *, key: str, limit: int, window_seconds: int) -> None:
    """Fixed-window rate limit backed by Redis, keyed by client IP + a route label.

    Redis-backed (not an in-memory counter) so this is correct across
    multiple backend replicas, not just a single process — the same class
    of bug documented on demo_sessions.py, avoided here on purpose.

    Fails open: if Redis itself is unreachable, the request is allowed
    through rather than turning a Redis hiccup into a false "rate limited"
    response. Anything actually dependent on Redis (schema caching) will
    surface its own honest error downstream instead.
    """
    client_ip = _client_ip(request)
    window_start = int(time.time()) // window_seconds
    redis_key = f"ratelimit:{key}:{client_ip}:{window_start}"

    r = get_redis()
    try:
        count = await r.incr(redis_key)
        if count == 1:
            await r.expire(redis_key, window_seconds)
    except Exception:
        return

    if count > limit:
        retry_after = window_seconds - (int(time.time()) % window_seconds)
        raise HTTPException(
            status_code=429,
            detail=f"Too many requests — limit is {limit} per {window_seconds}s. Try again shortly.",
            headers={"Retry-After": str(retry_after)},
        )


def _client_ip(request: Request) -> str:
    # Trusts X-Forwarded-For as set by the platform's edge proxy — Railway
    # (and most other PaaS hosts) sets this correctly on the way in. This
    # app isn't meant to sit directly on the public internet without one of
    # those in front of it — if it ever does, this header becomes
    # spoofable and this function should be revisited.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
