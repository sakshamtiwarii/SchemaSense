from typing import get_args

import httpx
import openai
import pytest

from app.core import sql_chain
from app.core.sql_chain import PROVIDER_BASE_URLS, PROVIDER_DEFAULT_MODELS, LLMConfig
from app.schemas.schemas import LLMOverride


class _FakeChatOpenAI:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


@pytest.fixture(autouse=True)
def _fake_client(monkeypatch):
    monkeypatch.setattr(sql_chain, "_llm", None)
    monkeypatch.setattr(sql_chain, "ChatOpenAI", _FakeChatOpenAI)
    yield
    monkeypatch.setattr(sql_chain, "_llm", None)


def test_default_llm_is_a_cached_singleton():
    first = sql_chain.get_llm()
    second = sql_chain.get_llm()

    assert first is second
    assert first.kwargs["model"] == sql_chain.settings.chat_model
    assert "base_url" not in first.kwargs


def test_default_llm_respects_a_configured_non_openai_provider(monkeypatch):
    monkeypatch.setattr(sql_chain.settings, "default_llm_provider", "groq")
    monkeypatch.setattr(sql_chain.settings, "openai_api_key", "gsk_default")
    monkeypatch.setattr(sql_chain.settings, "chat_model", "openai/gpt-oss-120b")

    llm = sql_chain.get_llm()

    assert llm.kwargs["api_key"] == "gsk_default"
    assert llm.kwargs["base_url"] == sql_chain.PROVIDER_BASE_URLS["groq"]
    assert llm.kwargs["model"] == "openai/gpt-oss-120b"


def test_byok_groq_uses_groqs_base_url_and_default_model():
    config = LLMConfig(provider="groq", api_key="gsk_test")

    llm = sql_chain.get_llm(config)

    assert llm.kwargs["api_key"] == "gsk_test"
    assert llm.kwargs["base_url"] == sql_chain.PROVIDER_BASE_URLS["groq"]
    assert llm.kwargs["model"] == sql_chain.PROVIDER_DEFAULT_MODELS["groq"]


def test_byok_respects_an_explicit_model_override():
    config = LLMConfig(provider="groq", api_key="gsk_test", model="openai/gpt-oss-20b")

    llm = sql_chain.get_llm(config)

    assert llm.kwargs["model"] == "openai/gpt-oss-20b"


def test_byok_openai_has_no_custom_base_url():
    config = LLMConfig(provider="openai", api_key="sk-test")

    llm = sql_chain.get_llm(config)

    assert "base_url" not in llm.kwargs
    assert llm.kwargs["model"] == PROVIDER_DEFAULT_MODELS["openai"]


def test_byok_does_not_borrow_the_servers_model_across_providers(monkeypatch):
    """The server's CHAT_MODEL belongs to whichever provider its own key is
    for. A visitor bringing an OpenAI key while the server runs on Groq used
    to get a Groq model name sent to OpenAI, and a 404 that reads exactly
    like a rejected key."""
    monkeypatch.setattr(sql_chain.settings, "chat_model", "openai/gpt-oss-120b")

    llm = sql_chain.get_llm(LLMConfig(provider="openai", api_key="sk-test"))

    assert llm.kwargs["model"] == "gpt-4o-mini"


def test_every_provider_the_schema_accepts_has_a_default_model():
    """get_llm indexes PROVIDER_DEFAULT_MODELS directly, so a provider added
    to the request schema without one raises KeyError at request time — on a
    real request, not in CI. This pins the two together."""
    accepted = set(get_args(LLMOverride.model_fields["provider"].annotation))

    assert accepted == set(PROVIDER_DEFAULT_MODELS) == set(PROVIDER_BASE_URLS)
    assert all(PROVIDER_DEFAULT_MODELS.values())


def test_byok_client_is_never_cached_or_reused():
    config = LLMConfig(provider="groq", api_key="gsk_test")

    first = sql_chain.get_llm(config)
    second = sql_chain.get_llm(config)

    assert first is not second


def test_byok_does_not_affect_the_default_singleton():
    default_before = sql_chain.get_llm()
    sql_chain.get_llm(LLMConfig(provider="groq", api_key="gsk_test"))
    default_after = sql_chain.get_llm()

    assert default_before is default_after


def _provider_error(cls, status):
    """Build a real provider exception the way the openai SDK raises them."""
    request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    return cls("boom", response=httpx.Response(status, request=request), body=None)


class _RaisingClient:
    def __init__(self, exc, **kwargs):
        self._exc = exc
        self.kwargs = kwargs

    async def ainvoke(self, prompt):
        raise self._exc


@pytest.mark.parametrize(
    "cls, status",
    [
        (openai.AuthenticationError, 401),
        (openai.PermissionDeniedError, 403),
        (openai.NotFoundError, 404),
        (openai.BadRequestError, 400),
    ],
)
async def test_a_bad_key_or_model_becomes_an_llm_config_error(monkeypatch, cls, status):
    exc = _provider_error(cls, status)
    monkeypatch.setattr(sql_chain, "get_llm", lambda config=None: _RaisingClient(exc))

    with pytest.raises(sql_chain.LLMConfigError):
        await sql_chain.generate_sql("q", "schema", LLMConfig(provider="groq", api_key="gsk_test"))


async def test_a_blank_key_fails_before_any_network_call(monkeypatch):
    def _boom(config=None):
        raise openai.OpenAIError("The api_key client option must be set")

    monkeypatch.setattr(sql_chain, "get_llm", _boom)

    with pytest.raises(sql_chain.LLMConfigError):
        await sql_chain.generate_sql("q", "schema")


@pytest.mark.parametrize("cls, status", [(openai.RateLimitError, 429), (openai.InternalServerError, 500)])
async def test_a_provider_having_a_bad_day_is_not_a_config_error(monkeypatch, cls, status):
    """Rate limits and outages say nothing about the key — they must not be
    translated, or the caller gets told their valid key is invalid."""
    exc = _provider_error(cls, status)
    monkeypatch.setattr(sql_chain, "get_llm", lambda config=None: _RaisingClient(exc))

    with pytest.raises(cls):
        await sql_chain.generate_sql("q", "schema", LLMConfig(provider="groq", api_key="gsk_test"))


async def test_the_correction_prompt_translates_errors_the_same_way(monkeypatch):
    exc = _provider_error(openai.AuthenticationError, 401)
    monkeypatch.setattr(sql_chain, "get_llm", lambda config=None: _RaisingClient(exc))

    with pytest.raises(sql_chain.LLMConfigError):
        await sql_chain.fix_sql("q", "SELECT 1", "boom", "schema", LLMConfig(provider="groq", api_key="gsk_test"))


@pytest.mark.parametrize("bad_key", ["gsk_abc—def", "gsk_“quoted”", "gsk_café"])
async def test_a_key_that_cannot_go_in_a_header_is_caught_before_the_request(monkeypatch, bad_key):
    """An em dash or smart quote in a pasted key blows up deep inside httpx
    with a UnicodeEncodeError, which reads like an outage rather than a bad
    key. It has to be named for what it is."""
    called = False

    def _should_not_run(config=None):
        nonlocal called
        called = True
        raise AssertionError("the client must not be built with an unsendable key")

    monkeypatch.setattr(sql_chain, "get_llm", _should_not_run)

    with pytest.raises(sql_chain.LLMConfigError) as caught:
        await sql_chain.generate_sql("q", "schema", LLMConfig(provider="groq", api_key=bad_key))

    assert not called
    assert "non-ASCII" in caught.value.client_detail


async def test_the_unsendable_key_error_never_quotes_the_key(monkeypatch):
    key = "gsk_supersecrettoken—trailing"
    monkeypatch.setattr(sql_chain, "get_llm", lambda config=None: None)

    with pytest.raises(sql_chain.LLMConfigError) as caught:
        await sql_chain.generate_sql("q", "schema", LLMConfig(provider="groq", api_key=key))

    assert "supersecrettoken" not in str(caught.value)
    assert "supersecrettoken" not in caught.value.client_detail


async def test_a_provider_error_is_never_echoed_to_the_caller(monkeypatch):
    """Provider text can quote a masked form of the key, so it stays server-side."""
    exc = _provider_error(openai.AuthenticationError, 401)
    monkeypatch.setattr(sql_chain, "get_llm", lambda config=None: _RaisingClient(exc))

    with pytest.raises(sql_chain.LLMConfigError) as caught:
        await sql_chain.generate_sql("q", "schema", LLMConfig(provider="groq", api_key="gsk_test"))

    assert caught.value.client_detail is None


async def test_an_ascii_key_still_reaches_the_client(monkeypatch):
    seen = {}

    class _Ok:
        async def ainvoke(self, prompt):
            seen["called"] = True
            return type("R", (), {"content": "SELECT 1"})()

    monkeypatch.setattr(sql_chain, "get_llm", lambda config=None: _Ok())

    assert await sql_chain.generate_sql("q", "schema", LLMConfig(provider="groq", api_key="gsk_fine")) == "SELECT 1"
    assert seen["called"]
