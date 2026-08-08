import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.demo_sessions import close_all_sessions
from app.db.postgres import close_db_pool, get_db_pool
from app.db.redis_client import close_redis
from app.routes import demo, query, schema

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_db_pool()
    yield
    await close_all_sessions()
    await close_db_pool()
    await close_redis()


app = FastAPI(title="NL-to-SQL Generator", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(query.router)
app.include_router(schema.router)
app.include_router(demo.router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
