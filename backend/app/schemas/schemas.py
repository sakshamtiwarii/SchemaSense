from typing import Any

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, description="Natural language question to answer")
    session_id: str | None = Field(
        None,
        description="Demo session id from POST /demo/connect. Omit to query the default database.",
    )


class QueryResponse(BaseModel):
    sql: str
    rows: list[dict[str, Any]]
    attempts: int


class QueryErrorResponse(BaseModel):
    error: str
    sql: str | None = None
    last_sql_tried: str | None = None
    last_error: str | None = None


class SchemaResponse(BaseModel):
    schema_context: str


class DemoConnectRequest(BaseModel):
    connection_string: str = Field(
        ...,
        min_length=1,
        description="A Postgres connection URI, ideally for a read-only user. Used only for this session, never persisted.",
    )


class DemoConnectResponse(BaseModel):
    session_id: str
    expires_in_seconds: int
