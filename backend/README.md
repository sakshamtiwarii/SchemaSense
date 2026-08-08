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
2. **DB-level backstop**: the app connects as `nlsql_app`, a Postgres role
   created in `docker/init.sql` with `SELECT`-only grants on the schema. Even
   a gap in the regex can't cause damage.
3. **Result size cap**: `executor.py` appends a hard `LIMIT` server-side if
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

### `GET /schema?refresh=false`

Debug endpoint — returns the introspected schema context the LLM is prompted
with. Pass `?refresh=true` to bypass the Redis cache.

### `GET /health`

Liveness check.

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

These run against mocks, not a live DB/LLM, so no Postgres/Redis/OpenAI
connection is required to run them.

## Project layout

```
app/
  main.py              # FastAPI entrypoint, CORS, lifespan (pool/redis)
  config.py            # env-driven settings
  routes/
    query.py           # POST /query
    schema.py           # GET /schema
  core/
    introspection.py   # reads Postgres schema, caches in Redis
    sql_chain.py        # prompt assembly + LLM SQL generation
    executor.py          # runs SQL, enforces row limit
    correction.py        # the self-correction retry loop
    safety.py            # read-only enforcement (SELECT-only)
    prompts.py           # system prompts
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
