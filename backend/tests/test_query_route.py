"""Status-code mapping for POST /query.

The distinction under test is which side is at fault. A 400 accuses the
caller's own key; a 502 owns the failure as the server's. Getting that wrong
is not cosmetic — it sends someone off to regenerate a perfectly good API key
while the actual outage is in the backend.
"""

import httpx
import openai
import pytest
from fastapi.testclient import TestClient

from app.core.sql_chain import LLMConfigError
from app.main import app
from app.routes import query as query_route

client = TestClient(app)

BYOK = {"provider": "groq", "api_key": "gsk_test"}


@pytest.fixture(autouse=True)
def _stub_pipeline(monkeypatch):
    """Everything up to the LLM call succeeds, so each test controls exactly
    one failure."""

    async def _no_rate_limit(*args, **kwargs):
        return None

    async def _resolve(session_id):
        return ("pool", "cache-key")

    async def _schema(pool, ttl, cache_key=None):
        return "Table products: id (integer)"

    monkeypatch.setattr(query_route, "enforce_rate_limit", _no_rate_limit)
    monkeypatch.setattr(query_route, "resolve_pool_and_cache_key", _resolve)
    monkeypatch.setattr(query_route, "get_cached_schema_context", _schema)


def _answers_with(monkeypatch, exc):
    async def _boom(question, schema_context, pool, llm_config=None):
        raise exc

    monkeypatch.setattr(query_route, "answer_question", _boom)


def test_a_rejected_byok_key_is_the_callers_fault(monkeypatch):
    _answers_with(monkeypatch, LLMConfigError("invalid api key"))

    response = client.post("/query", json={"question": "count products", "llm": BYOK})

    assert response.status_code == 400
    assert "API key/model" in response.json()["detail"]


def test_the_servers_own_broken_key_is_not_blamed_on_the_caller(monkeypatch):
    """The caller supplied no key, so a credentials failure is entirely the
    server's — a 400 here would be accusing them of something they didn't do."""
    _answers_with(monkeypatch, LLMConfigError("The api_key client option must be set"))

    response = client.post("/query", json={"question": "count products"})

    assert response.status_code == 502
    assert "server-side" in response.json()["detail"]


def test_a_backend_failure_is_not_blamed_on_a_valid_byok_key(monkeypatch):
    """The regression this mapping exists to prevent: with a key on the
    request, any pipeline failure at all used to come back as "check that your
    API key is valid", which is a lie when Redis or Postgres is the thing that
    fell over."""
    _answers_with(monkeypatch, ConnectionError("redis is down"))

    response = client.post("/query", json={"question": "count products", "llm": BYOK})

    assert response.status_code == 502
    assert "API key" not in response.json()["detail"]


def test_a_provider_rate_limit_is_not_reported_as_a_bad_key(monkeypatch):
    request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    _answers_with(
        monkeypatch,
        openai.RateLimitError("slow down", response=httpx.Response(429, request=request), body=None),
    )

    response = client.post("/query", json={"question": "count products", "llm": BYOK})

    assert response.status_code == 502


def test_a_missing_demo_session_still_wins_over_the_llm_mapping(monkeypatch):
    async def _expired(session_id):
        return None

    monkeypatch.setattr(query_route, "resolve_pool_and_cache_key", _expired)

    response = client.post("/query", json={"question": "count products", "session_id": "gone", "llm": BYOK})

    assert response.status_code == 404


def test_a_working_request_passes_the_body_straight_through(monkeypatch):
    async def _ok(question, schema_context, pool, llm_config=None):
        return {"sql": "SELECT count(*) FROM products", "rows": [{"count": 3}], "attempts": 1}

    monkeypatch.setattr(query_route, "answer_question", _ok)

    response = client.post("/query", json={"question": "count products", "llm": BYOK})

    assert response.status_code == 200
    assert response.json()["attempts"] == 1


def test_an_unsendable_key_tells_the_caller_what_is_actually_wrong(monkeypatch):
    """The generic wording sent people off to regenerate a key that was fine —
    when the real problem is a character they pasted along with it."""
    _answers_with(
        monkeypatch,
        LLMConfigError("non-ASCII", client_detail="The API key contains a non-ASCII character ('—', U+2014)."),
    )

    response = client.post("/query", json={"question": "count products", "llm": BYOK})

    assert response.status_code == 400
    assert "non-ASCII" in response.json()["detail"]


def test_a_provider_rejection_falls_back_to_the_generic_wording(monkeypatch):
    _answers_with(monkeypatch, LLMConfigError("401 from groq, key sk-ab***xyz"))

    response = client.post("/query", json={"question": "count products", "llm": BYOK})

    assert response.status_code == 400
    assert "API key/model" in response.json()["detail"]
    assert "sk-ab" not in response.json()["detail"]
