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
