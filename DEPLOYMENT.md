# Deployment

## Frontend — done, live

Deployed via the Vercel CLI, already authenticated on this machine:

```
https://frontend-pearl-nine-hu5nqtwm3d.vercel.app
```

It renders correctly but can't reach a backend yet — `VITE_API_BASE_URL`
isn't set, so it falls back to `http://localhost:8000`, which only exists
on this machine. Once the backend is deployed (below), set
`VITE_API_BASE_URL` to its real URL as a Vercel project environment
variable and redeploy (`vercel --prod` from `frontend/`).

## Backend — needs one manual step: connecting a Render account

I can't create or authenticate into a hosting account on your behalf — no
CLI was installed for Render/Railway/Fly, and account creation needs your
own OAuth/login. Everything short of that is ready.

### Option A — Blueprint (faster if it works)

1. Commit and push the changes made in this session (`render.yaml`, the
   `Dockerfile` update, rate limiting, CORS). Render deploys from what's
   actually on GitHub.
2. [render.com](https://render.com) → sign in with GitHub → **New >
   Blueprint** → select `sakshamtiwarii/SchemaSense`. Render should detect
   `render.yaml` at the repo root and propose: a Postgres instance, a
   Redis instance, and a Docker web service for `backend/`.
3. It'll prompt for `OPENAI_API_KEY` (the only secret marked `sync: false`
   in the blueprint, so Render asks rather than storing a value from git).
4. Apply. Wait for all three services to go healthy.

`render.yaml` is a best-effort file — I wrote it without a Render account
to test against, so if the dashboard flags a field, fix it there directly
rather than fighting the YAML; Option B below works regardless.

### Option B — Manual dashboard setup (reliable fallback)

1. **New > PostgreSQL** — name `schemasense-db`, database name `nlsql`,
   user `nlsql`, free plan. Note the **Internal Database URL** once it's up.
2. **New > Redis** — name `schemasense-redis`, free plan. Note its
   **Internal Redis URL**.
3. **New > Web Service** → connect the repo → Runtime: **Docker** →
   Dockerfile path `backend/Dockerfile`, Docker context `backend`. Set
   environment variables from `backend/.env.example`, with:
   - `DATABASE_URL` = the Postgres Internal Database URL from step 1
   - `REDIS_URL` = the Redis Internal URL from step 2
   - `OPENAI_API_KEY` = your real key
   - `CORS_ALLOWED_ORIGINS` = `https://frontend-pearl-nine-hu5nqtwm3d.vercel.app`
   - everything else can keep the defaults from `.env.example`

### After either option: seed the database (one-time, required either way)

Render's managed Postgres is a bare instance — it doesn't auto-run
`docker/init.sql` the way the official `postgres` Docker image does in
local `docker compose`. Without this step there's no `orders`/`products`
data and no `nlsql_app` read-only role, so `/query` has nothing to query.

Before running this against a real deployment, change the hardcoded
password in `docker/init.sql`'s `CREATE ROLE nlsql_app ... PASSWORD
'nlsql_app'` line to something random — it's a read-only role backed by
the transaction-level safety in `executor.py` either way, but there's no
reason to leave a guessable password on it in production.

```bash
# From the Postgres instance's page in Render's dashboard, copy the
# External Database URL (not Internal — you're connecting from your own
# machine here, not from another Render service), then:
psql "$EXTERNAL_DATABASE_URL" -f backend/docker/init.sql
```

Then update the web service's `DATABASE_URL` env var to use the
`nlsql_app` role instead of the admin one Render gave you — same host,
port, database name; just swap the user/password to `nlsql_app`/whatever
you set — and trigger a manual redeploy so it picks up the change.

### Once the backend has a public URL

Check `https://<your-service>.onrender.com/health` returns `{"status":
"ok"}`, then tell me the URL — I'll set `VITE_API_BASE_URL` in Vercel and
redeploy the frontend, and confirm `CORS_ALLOWED_ORIGINS` on the backend
matches the live Vercel URL exactly.

### Worth knowing about Render's free tier

Free web services spin down after periods of inactivity — the first
request after idling will be slow (cold start) rather than broken. Free
Postgres/Redis have their own retention limits; check Render's current
terms if this needs to stay up reliably rather than as a demo.
