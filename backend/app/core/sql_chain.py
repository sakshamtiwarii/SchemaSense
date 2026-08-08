from langchain_openai import ChatOpenAI

from app.config import settings
from app.core.prompts import SQL_FIX_PROMPT, SQL_GENERATION_PROMPT

_llm: ChatOpenAI | None = None


def get_llm() -> ChatOpenAI:
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(model=settings.chat_model, temperature=0, api_key=settings.openai_api_key)
    return _llm


async def generate_sql(question: str, schema_context: str) -> str:
    prompt = SQL_GENERATION_PROMPT.format(schema=schema_context, question=question)
    response = await get_llm().ainvoke(prompt)
    return _extract_sql(response.content)


async def fix_sql(question: str, failed_sql: str, error: str, schema_context: str) -> str:
    prompt = SQL_FIX_PROMPT.format(
        schema=schema_context,
        question=question,
        failed_sql=failed_sql,
        error=error,
    )
    response = await get_llm().ainvoke(prompt)
    return _extract_sql(response.content)


def _extract_sql(text: str) -> str:
    # Strip markdown code fences if the model wraps its answer in ```sql ... ```
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.lower().startswith("sql"):
            text = text[3:]
    return text.strip().rstrip(";")
