# NL-to-SQL Generator — Backend

Turns a plain-English question into a real, executed SQL query against a live
PostgreSQL database — grounded by schema introspection, guarded by a
read-only safety layer, and made reliable by a self-correction loop that
retries against the actual database error.

## Architecture

```
Question → Schema Introspection (cached in Redis) → Prompt Assembly →
LLM generates SQL → Safety check (SELECT-only) → Execute →
  succeeds → return rows
  fails → feed DB error back to LLM → retry (max 3 attempts)
```

See `app/core/correction.py` for the loop and `app/core/safety.py` for the
read-only enforcement.

## Stack

FastAPI · LangChain (`langchain-openai`) · PostgreSQL (`asyncpg`) · Redis ·
OpenAI `gpt-4o-mini` · Docker Compose

## Defense in depth on safety

1. **App-level**: `is_read_only()` rejects anything that isn't a bare
   `SELECT`, or that contains `DROP`/`DELETE`/`UPDATE`/`INSERT`/etc.
2. **Transaction-level**: every query runs inside a Postgres `READ ONLY`
   transaction (`executor.py`). Postgres enforces this regardless of the
   connecting role's actual grants — this is what makes it safe to run
   generated SQL against a database whose role setup we don't control (see
   Demo mode below), not just the one we seeded ourselves.
3. **DB-level backstop (seeded DB only)**: the default database connects as
   `nlsql_app`, a Postgres role created in `docker/init.sql` with
   `SELECT`-only grants on the schema.
4. **Result size cap**: `executor.py` appends a hard `LIMIT` server-side if
   the generated SQL doesn't already have one.

## Running locally

```bash
cp .env.example .env        # fill in OPENAI_API_KEY
docker compose up --build
```

This starts Postgres (seeded with sample `products`/`orders` tables via
`docker/init.sql`), Redis, and the API on `http://localhost:8000`.

## Running without Docker

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# start your own Postgres + Redis, point .env at them
uvicorn app.main:app --reload
```

## API

### `POST /query`

```json
// Request
{ "question": "What were our top 5 products by revenue?" }

// Response (success)
{
  "sql": "SELECT product_name, SUM(revenue) AS total FROM ...",
  "rows": [{ "product_name": "Gizmo Pro", "total": 360.0 }],
  "attempts": 1
}

// Response (retries exhausted)
{
  "error": "Could not produce a working query after 3 attempts.",
  "last_sql_tried": "SELECT ...",
  "last_error": "column \"prod_name\" does not exist"
}
```

Sample questions to try against the seeded data:
- "What were our top 3 products by revenue?"
- "How many orders were placed in the last 30 days?"
- "What's the average order revenue by product category?"

**Bring your own LLM key.** Add an `llm` field to use your own Groq or
OpenAI key instead of the server's, for that request only:

```json
{
  "question": "What were our top 3 products by revenue?",
  "llm": { "provider": "groq", "api_key": "gsk_...", "model": "llama-3.3-70b-versatile" }
}
```

`model` is optional — it defaults to `llama-3.3-70b-versatile` for Groq and
the server's configured model for OpenAI. Groq's API is OpenAI-compatible,
so this reuses the same `ChatOpenAI` client pointed at a different base URL
(`app/core/sql_chain.py`); `provider` is a closed set mapped to a
server-controlled base URL, not a free-text host, so it can't be used as an
open proxy the way a demo DB connection string could be. The key is never
cached, logged, or reused across requests — a fresh client is built per
call. A bad key surfaces as `400` with a clear message; the server's own
key failing surfaces as `502`, since that's a different kind of problem
(ours, not yours).

### `GET /schema?refresh=false`

Debug endpoint — returns the introspected schema context the LLM is prompted
with. Pass `?refresh=true` to bypass the Redis cache.

### `GET /health`

Liveness check.

## Demo mode — bring your own database

A visitor can point the service at their own Postgres database for a single
session, without registering an account and without the connection string
ever being persisted anywhere (no disk, no Redis, no logs).

```json
// POST /demo/connect
{ "connection_string": "postgresql://readonly_user:pw@their-host:5432/theirdb" }

// Response
{ "session_id": "kA1n...redacted...", "expires_in_seconds": 1800 }
```

Pass that `session_id` on subsequent calls to query their database instead of
the default one:

```json
// POST /query
{ "question": "How many rows are in the customers table?", "session_id": "kA1n..." }
```

`DELETE /demo/connect/{session_id}` closes the connection immediately and
wipes its cached schema; otherwise it expires on its own after
`DEMO_SESSION_TTL_SECONDS` of inactivity (default 30 min).

**What's different about this path, and why it's still safe:**
- The server resolves the host and refuses to connect to private/loopback/
  link-local addresses (`app/core/network_guard.py`) — without this, the
  endpoint would let anyone make the server probe internal infrastructure or
  cloud metadata endpoints (a classic SSRF hole). Set
  `ALLOW_PRIVATE_DEMO_HOSTS=true` only for local testing against your own
  dev database.
- We can't `CREATE ROLE` inside someone else's database, so the DB-level
  backstop (layer 3 above) doesn't apply here. The READ ONLY transaction
  wrapper (layer 2) does — Postgres rejects any write inside it independent
  of the connecting user's actual grants, so a visitor whose "read-only"
  credentials aren't actually locked down still can't cause damage.
- Sessions live in an in-memory dict (`app/core/demo_sessions.py`), capped at
  `MAX_DEMO_SESSIONS` concurrent connections and reaped on expiry. This is
  intentionally process-local — run a single API worker, or replace this
  store if that stops being acceptable at scale.
- Ask visitors for read-only credentials in the connection string as a matter
  of good practice, but don't rely on it being true — the transaction wrapper
  is the actual guarantee.

## Production hardening

Two things a public deployment needs that local dev doesn't:

- **CORS**: `CORS_ALLOWED_ORIGINS` (comma-separated) — defaults to the local
  Vite dev server. Set it to the real frontend origin(s) before deploying;
  `main.py` no longer allows `"*"`, and only `GET`/`POST`/`DELETE` +
  `Content-Type` are permitted, matching what the API actually uses.
- **Rate limiting** (`app/core/rate_limit.py`): a Redis-backed fixed-window
  limiter, keyed by client IP (`X-Forwarded-For` if present, else the
  connection's own address) plus a per-route label, so `/query`,
  `/demo/connect`, and `/schema` are limited independently. `/query` gets
  the tightest cap (`RATE_LIMIT_QUERY_PER_MINUTE`, default 10/min) since
  it's the expensive one — up to 3 LLM calls per request via the
  correction loop. Redis-backed rather than an in-memory counter on
  purpose: correct across multiple backend replicas, the same class of bug
  already documented on `demo_sessions.py` below, avoided here instead of
  repeated. Fails open on a Redis error — a rate-limit check failing
  shouldn't itself take the API down; anything actually dependent on
  Redis will surface its own honest error.

Neither of these was needed for local development, both are close to the
top of what's needed before this is exposed to the public internet. See
`docker/init.sql`'s hardcoded `nlsql_app` password and the in-memory demo
session store (below) for what's still open beyond this.

## Tests

```bash
pytest
```

- `tests/test_safety.py` — confirms non-`SELECT` and forbidden-keyword SQL
  is rejected, including stacked-query and CTE-smuggling attempts.
- `tests/test_correction.py` — confirms the retry loop recovers from a bad
  query using a mocked LLM/executor, and gives up cleanly after
  `MAX_ATTEMPTS`.
- `tests/test_introspection.py` — confirms schema formatting and Redis
  caching behavior (including `force_refresh`) with a fake pool/redis.
- `tests/test_executor.py` — confirms every query runs inside a `readonly`
  transaction and that the row-limit logic behaves correctly.
- `tests/test_network_guard.py` — confirms loopback/private/link-local hosts
  (including the `169.254.169.254` cloud-metadata address) are rejected, a
  public IP is allowed, and the `ALLOW_PRIVATE_DEMO_HOSTS` escape hatch works.
- `tests/test_demo_sessions.py` — confirms session creation/expiry/limits and
  that closing a session actually closes its pool.
- `tests/test_sql_chain.py` — confirms the default LLM client is a cached
  singleton, a bring-your-own-key config is never cached or reused, and
  provider routing (Groq's base URL, per-provider default models, explicit
  model overrides) resolves correctly.
- `tests/test_rate_limit.py` — confirms requests under the limit pass,
  requests over it get a `429` with `Retry-After`, different IPs/routes
  are limited independently, `X-Forwarded-For` is preferred over the raw
  connection address, the window actually resets after its boundary, and
  a Redis failure fails open instead of blocking requests.

These run against mocks, not a live DB/LLM, so no Postgres/Redis/OpenAI
connection is required to run them.

## Project layout

```
app/
  main.py              # FastAPI entrypoint, CORS, lifespan (pool/redis)
  config.py            # env-driven settings
  routes/
    query.py           # POST /query (default DB or a demo session)
    schema.py           # GET /schema
    demo.py              # POST /demo/connect, DELETE /demo/connect/{id}
  core/
    introspection.py   # reads Postgres schema, caches in Redis
    sql_chain.py        # prompt assembly + LLM SQL generation + BYOK provider routing
    executor.py          # runs SQL in a READ ONLY transaction, enforces row limit
    correction.py        # the self-correction retry loop
    safety.py            # read-only enforcement (SELECT-only)
    prompts.py           # system prompts
    demo_sessions.py     # in-memory registry of demo DB connections
    network_guard.py     # SSRF guard for demo connection hosts
    rate_limit.py         # Redis-backed per-IP request caps
  db/
    postgres.py          # asyncpg pool (lazy singleton)
    redis_client.py      # redis client (lazy singleton)
  schemas/
    schemas.py           # Pydantic request/response models
tests/
docker/init.sql          # seed data + read-only app role
docker-compose.yml
Dockerfile
```
