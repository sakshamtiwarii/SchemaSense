import pytest

from app.core import correction
from app.core.sql_chain import LLMConfig


@pytest.mark.asyncio
async def test_succeeds_on_first_attempt(monkeypatch):
    async def fake_generate_sql(question, schema_context, llm_config=None):
        return "SELECT * FROM orders"

    async def fake_execute_query(pool, sql):
        return [{"id": 1}]

    async def fake_fix_sql(*args, **kwargs):
        raise AssertionError("fix_sql should not be called when the first attempt succeeds")

    monkeypatch.setattr(correction, "generate_sql", fake_generate_sql)
    monkeypatch.setattr(correction, "execute_query", fake_execute_query)
    monkeypatch.setattr(correction, "fix_sql", fake_fix_sql)

    result = await correction.answer_question("how many orders?", "Table orders: id (integer)", pool=None)

    assert result == {"sql": "SELECT * FROM orders", "rows": [{"id": 1}], "attempts": 1}


@pytest.mark.asyncio
async def test_recovers_after_one_bad_query(monkeypatch):
    attempts = {"n": 0}

    async def fake_generate_sql(question, schema_context, llm_config=None):
        return "SELECT prod_name FROM products"

    async def fake_execute_query(pool, sql):
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise RuntimeError('column "prod_name" does not exist')
        return [{"product_name": "Widget A"}]

    fix_calls = []

    async def fake_fix_sql(question, failed_sql, error, schema_context, llm_config=None):
        fix_calls.append((failed_sql, error))
        return "SELECT product_name FROM products"

    monkeypatch.setattr(correction, "generate_sql", fake_generate_sql)
    monkeypatch.setattr(correction, "execute_query", fake_execute_query)
    monkeypatch.setattr(correction, "fix_sql", fake_fix_sql)

    result = await correction.answer_question("list products", "Table products: product_name (text)", pool=None)

    assert result["attempts"] == 2
    assert result["sql"] == "SELECT product_name FROM products"
    assert len(fix_calls) == 1
    assert fix_calls[0][0] == "SELECT prod_name FROM products"
    assert "prod_name" in fix_calls[0][1]


@pytest.mark.asyncio
async def test_gives_up_after_max_attempts(monkeypatch):
    async def fake_generate_sql(question, schema_context, llm_config=None):
        return "SELECT * FROM does_not_exist"

    async def fake_execute_query(pool, sql):
        raise RuntimeError('relation "does_not_exist" does not exist')

    fix_calls = []

    async def fake_fix_sql(question, failed_sql, error, schema_context, llm_config=None):
        fix_calls.append(failed_sql)
        return failed_sql

    monkeypatch.setattr(correction, "generate_sql", fake_generate_sql)
    monkeypatch.setattr(correction, "execute_query", fake_execute_query)
    monkeypatch.setattr(correction, "fix_sql", fake_fix_sql)

    result = await correction.answer_question("bogus question", "Table orders: id (integer)", pool=None)

    assert result["error"].startswith("Could not produce a working query")
    assert result["last_sql_tried"] == "SELECT * FROM does_not_exist"
    assert len(fix_calls) == correction.MAX_ATTEMPTS - 1


@pytest.mark.asyncio
async def test_rejects_non_read_only_sql_before_execution(monkeypatch):
    async def fake_generate_sql(question, schema_context, llm_config=None):
        return "DROP TABLE orders"

    async def fake_execute_query(pool, sql):
        raise AssertionError("execute_query should never run for a non-read-only query")

    monkeypatch.setattr(correction, "generate_sql", fake_generate_sql)
    monkeypatch.setattr(correction, "execute_query", fake_execute_query)

    result = await correction.answer_question("drop the orders table", "Table orders: id (integer)", pool=None)

    assert result == {"error": "Generated query was not read-only — rejected.", "sql": "DROP TABLE orders"}


@pytest.mark.asyncio
async def test_llm_config_is_forwarded_to_generate_and_fix(monkeypatch):
    seen = {}
    config = LLMConfig(provider="groq", api_key="gsk_test", model="openai/gpt-oss-120b")
    attempts = {"n": 0}

    async def fake_generate_sql(question, schema_context, llm_config=None):
        seen["generate"] = llm_config
        return "SELECT prod_name FROM products"

    async def fake_execute_query(pool, sql):
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise RuntimeError('column "prod_name" does not exist')
        return [{"product_name": "Widget A"}]

    async def fake_fix_sql(question, failed_sql, error, schema_context, llm_config=None):
        seen["fix"] = llm_config
        return "SELECT product_name FROM products"

    monkeypatch.setattr(correction, "generate_sql", fake_generate_sql)
    monkeypatch.setattr(correction, "execute_query", fake_execute_query)
    monkeypatch.setattr(correction, "fix_sql", fake_fix_sql)

    await correction.answer_question("list products", "Table products: product_name (text)", pool=None, llm_config=config)

    assert seen["generate"] is config
    assert seen["fix"] is config
