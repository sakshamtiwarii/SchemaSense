from dataclasses import dataclass

import openai
from langchain_openai import ChatOpenAI

from app.config import settings
from app.core.prompts import SQL_FIX_PROMPT, SQL_GENERATION_PROMPT


class LLMConfigError(Exception):
    """The API key or model this request was built with is unusable.

    Raised only for provider responses that indict the *credentials or the
    model name* — a revoked key, a key without access to that model, a model
    that no longer exists. Rate limits, timeouts and provider outages say
    nothing about how the request was configured, so they deliberately stay
    ordinary exceptions and reach the route as an upstream failure.
    """


# The provider errors that mean "what you configured is wrong", as opposed
# to "the provider is having a bad day". All are openai.APIStatusError
# subclasses, but RateLimitError and InternalServerError are siblings rather
# than children, so they fall through this tuple untouched.
CONFIG_ERRORS = (
    openai.AuthenticationError,       # 401 - key is wrong, revoked, or for another provider
    openai.PermissionDeniedError,     # 403 - key exists but can't use this model
    openai.NotFoundError,             # 404 - model doesn't exist, or was retired
    openai.BadRequestError,           # 400 - model name or params rejected
    openai.UnprocessableEntityError,  # 422
)


@dataclass(frozen=True)
class LLMConfig:
    """A bring-your-own-key override for a single request.

    `provider` is a closed set (see PROVIDER_BASE_URLS) mapped to a fixed,
    server-controlled base URL — never taken from the request directly —
    so unlike a demo database connection string, this can't be used to
    point the server at an arbitrary host.
    """

    provider: str
    api_key: str
    model: str | None = None


# Groq's API is OpenAI-compatible, so the same ChatOpenAI client works for
# both — only the base URL and default model differ.
PROVIDER_BASE_URLS = {
    "openai": None,
    "groq": "https://api.groq.com/openai/v1",
}

PROVIDER_DEFAULT_MODELS = {
    "openai": None,  # None = fall back to settings.chat_model
    "groq": "llama-3.3-70b-versatile",
}

_llm: ChatOpenAI | None = None


def get_llm(config: LLMConfig | None = None) -> ChatOpenAI:
    if config is None:
        # The server's own default — settings.default_llm_provider decides
        # which OpenAI-compatible endpoint settings.openai_api_key is for.
        # Defaults to "openai" so an unconfigured deployment behaves exactly
        # as before; set DEFAULT_LLM_PROVIDER=groq to make a Groq key the
        # default instead, same routing BYOK uses.
        global _llm
        if _llm is None:
            _llm = _build_client(settings.default_llm_provider, settings.openai_api_key, settings.chat_model)
        return _llm

    # Bring-your-own-key: a fresh client built per call. Never cached and
    # never assigned to the module-level singleton above — the key exists
    # only for the lifetime of this call, same as a demo DB connection
    # exists only for its session.
    model = config.model or PROVIDER_DEFAULT_MODELS.get(config.provider) or settings.chat_model
    return _build_client(config.provider, config.api_key, model)


def _build_client(provider: str, api_key: str, model: str) -> ChatOpenAI:
    kwargs = {"model": model, "temperature": 0, "api_key": api_key}
    base_url = PROVIDER_BASE_URLS.get(provider)
    if base_url:
        kwargs["base_url"] = base_url
    return ChatOpenAI(**kwargs)


async def _draft_sql(prompt: str, llm_config: LLMConfig | None) -> str:
    """Run one prompt through the LLM, translating configuration failures.

    Both the client construction and the call itself can fail because of a
    bad key or model, and both are funnelled into LLMConfigError so callers
    never have to know which provider SDK is underneath.
    """
    try:
        # Construction fails only when the key is missing or blank — the
        # provider SDK checks that before any network call happens.
        llm = get_llm(llm_config)
    except openai.OpenAIError as exc:
        raise LLMConfigError(str(exc)) from exc

    try:
        response = await llm.ainvoke(prompt)
    except CONFIG_ERRORS as exc:
        raise LLMConfigError(str(exc)) from exc

    return _extract_sql(response.content)


async def generate_sql(question: str, schema_context: str, llm_config: LLMConfig | None = None) -> str:
    prompt = SQL_GENERATION_PROMPT.format(schema=schema_context, question=question)
    return await _draft_sql(prompt, llm_config)


async def fix_sql(
    question: str,
    failed_sql: str,
    error: str,
    schema_context: str,
    llm_config: LLMConfig | None = None,
) -> str:
    prompt = SQL_FIX_PROMPT.format(
        schema=schema_context,
        question=question,
        failed_sql=failed_sql,
        error=error,
    )
    return await _draft_sql(prompt, llm_config)


def _extract_sql(text: str) -> str:
    # Strip markdown code fences if the model wraps its answer in ```sql ... ```
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.lower().startswith("sql"):
            text = text[3:]
    return text.strip().rstrip(";")
