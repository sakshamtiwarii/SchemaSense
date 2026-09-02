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

    `client_detail` is the subset of the reason that is safe to show the
    caller. It stays None for anything the provider wrote, because those
    messages quote a partially masked form of the submitted key back — only
    text this module composed itself is ever echoed out.
    """

    def __init__(self, message: str, *, client_detail: str | None = None) -> None:
        super().__init__(message)
        self.client_detail = client_detail


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

# Every provider names its own default. Deliberately *not* falling back to
# settings.chat_model here: that is the model for whichever provider the
# server's own key belongs to, so inheriting it sends one provider's model
# name to another's endpoint the moment the two differ — a 404 that reads
# exactly like a rejected key. These values are what the UI advertises in
# LLMKeyPanel.jsx; keep the two in step.
PROVIDER_DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    # Groq retires models on a rolling basis and a retired name comes back
    # as a 404 that reads exactly like a bad key — llama-3.3-70b-versatile
    # sat here until its shutdown on 2026-08-16. Check
    # console.groq.com/docs/deprecations before trusting this default.
    "groq": "openai/gpt-oss-120b",
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
    # No settings.chat_model tail: provider is a closed set (validated by the
    # request schema), so a default always exists, and borrowing the server's
    # model here is exactly the cross-provider mismatch described above.
    model = config.model or PROVIDER_DEFAULT_MODELS[config.provider]
    return _build_client(config.provider, config.api_key, model)


def _build_client(provider: str, api_key: str, model: str) -> ChatOpenAI:
    kwargs = {"model": model, "temperature": 0, "api_key": api_key}
    base_url = PROVIDER_BASE_URLS.get(provider)
    if base_url:
        kwargs["base_url"] = base_url
    return ChatOpenAI(**kwargs)


def _assert_key_is_transmittable(api_key: str) -> None:
    """Reject a key that can't survive being put in an HTTP header.

    The key goes out as `Authorization: Bearer <key>`, and httpx encodes
    header values as ASCII. A key pasted with surrounding prose, or one
    that has been through an editor that turns "--" into an em dash, blows
    up inside the provider SDK with a UnicodeEncodeError — far from
    anything that names the key as the culprit. Checking here turns that
    into the same honest "your key is unusable" answer as a rejected one.
    """
    if api_key.isascii():
        return

    bad = next(ch for ch in api_key if not ch.isascii())
    reason = (
        f"The API key contains a non-ASCII character ({bad!r}, U+{ord(bad):04X}) and can't be "
        "sent in a request header. Copy the key on its own, with no surrounding text."
    )
    # Names the offending character but never the key, so it is safe to show.
    raise LLMConfigError(reason, client_detail=reason)


async def _draft_sql(prompt: str, llm_config: LLMConfig | None) -> str:
    """Run one prompt through the LLM, translating configuration failures.

    Both the client construction and the call itself can fail because of a
    bad key or model, and both are funnelled into LLMConfigError so callers
    never have to know which provider SDK is underneath.
    """
    if llm_config is not None:
        _assert_key_is_transmittable(llm_config.api_key)

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
    except UnicodeEncodeError as exc:
        # Belt and braces behind _assert_key_is_transmittable: any other
        # unencodable header value would otherwise surface as a generic
        # upstream failure, which points debugging in the wrong direction.
        raise LLMConfigError(f"Request headers could not be encoded: {exc.reason}") from exc

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
