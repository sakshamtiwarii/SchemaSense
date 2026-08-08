from app.config import settings
from app.core.executor import execute_query
from app.core.safety import is_read_only
from app.core.sql_chain import LLMConfig, fix_sql, generate_sql

MAX_ATTEMPTS = settings.max_correction_attempts


async def answer_question(question: str, schema_context: str, pool, llm_config: LLMConfig | None = None) -> dict:
    sql = await generate_sql(question, schema_context, llm_config)
    last_error = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        if not is_read_only(sql):
            return {"error": "Generated query was not read-only — rejected.", "sql": sql}

        try:
            rows = await execute_query(pool, sql)
            return {"sql": sql, "rows": rows, "attempts": attempt}
        except Exception as e:
            last_error = str(e)
            if attempt == MAX_ATTEMPTS:
                break
            # Feed the actual DB error back to the LLM and ask it to fix the query
            sql = await fix_sql(question, sql, last_error, schema_context, llm_config)

    return {
        "error": f"Could not produce a working query after {MAX_ATTEMPTS} attempts.",
        "last_sql_tried": sql,
        "last_error": last_error,
    }
