from dataclasses import dataclass

from langchain_openai import ChatOpenAI

from app.config import settings
from app.core.prompts import SQL_FIX_PROMPT, SQL_GENERATION_PROMPT


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
        global _llm
        if _llm is None:
            _llm = ChatOpenAI(model=settings.chat_model, temperature=0, api_key=settings.openai_api_key)
        return _llm

    # Bring-your-own-key: a fresh client built per call. Never cached and
    # never assigned to the module-level singleton above — the key exists
    # only for the lifetime of this call, same as a demo DB connection
    # exists only for its session.
    model = config.model or PROVIDER_DEFAULT_MODELS.get(config.provider) or settings.chat_model
    kwargs = {"model": model, "temperature": 0, "api_key": config.api_key}
    base_url = PROVIDER_BASE_URLS.get(config.provider)
    if base_url:
        kwargs["base_url"] = base_url
    return ChatOpenAI(**kwargs)


async def generate_sql(question: str, schema_context: str, llm_config: LLMConfig | None = None) -> str:
    prompt = SQL_GENERATION_PROMPT.format(schema=schema_context, question=question)
    response = await get_llm(llm_config).ainvoke(prompt)
    return _extract_sql(response.content)


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
    response = await get_llm(llm_config).ainvoke(prompt)
    return _extract_sql(response.content)


def _extract_sql(text: str) -> str:
    # Strip markdown code fences if the model wraps its answer in ```sql ... ```
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.lower().startswith("sql"):
            text = text[3:]
    return text.strip().rstrip(";")
