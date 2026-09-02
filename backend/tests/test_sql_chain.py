import httpx
import openai
import pytest

from app.core import sql_chain
from app.core.sql_chain import LLMConfig


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
    monkeypatch.setattr(sql_chain.settings, "chat_model", "llama-3.3-70b-versatile")

    llm = sql_chain.get_llm()

    assert llm.kwargs["api_key"] == "gsk_default"
    assert llm.kwargs["base_url"] == sql_chain.PROVIDER_BASE_URLS["groq"]
    assert llm.kwargs["model"] == "llama-3.3-70b-versatile"


def test_byok_groq_uses_groqs_base_url_and_default_model():
    config = LLMConfig(provider="groq", api_key="gsk_test")

    llm = sql_chain.get_llm(config)

    assert llm.kwargs["api_key"] == "gsk_test"
    assert llm.kwargs["base_url"] == sql_chain.PROVIDER_BASE_URLS["groq"]
    assert llm.kwargs["model"] == sql_chain.PROVIDER_DEFAULT_MODELS["groq"]


def test_byok_respects_an_explicit_model_override():
    config = LLMConfig(provider="groq", api_key="gsk_test", model="llama-3.1-8b-instant")

    llm = sql_chain.get_llm(config)

    assert llm.kwargs["model"] == "llama-3.1-8b-instant"


def test_byok_openai_has_no_custom_base_url():
    config = LLMConfig(provider="openai", api_key="sk-test")

    llm = sql_chain.get_llm(config)

    assert "base_url" not in llm.kwargs
    assert llm.kwargs["model"] == sql_chain.settings.chat_model


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
