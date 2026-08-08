from typing import Any

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, description="Natural language question to answer")


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
