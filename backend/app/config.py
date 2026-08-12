from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://nlsql_app:nlsql_app@localhost:5432/nlsql"
    redis_url: str = "redis://localhost:6379/0"

    # The server's own default LLM (used whenever a request doesn't bring
    # its own key). openai_api_key holds whatever key that provider needs —
    # it's still named for the common case, but with default_llm_provider
    # set to "groq" it holds a Groq key instead, same routing BYOK uses.
    openai_api_key: str = ""
    chat_model: str = "gpt-4o-mini"
    default_llm_provider: str = "openai"

    schema_cache_ttl_seconds: int = 3600
    max_correction_attempts: int = 3
    max_result_rows: int = 200

    # Demo mode: visitors can try the service against their own Postgres
    # database for a single, unpersisted session.
    demo_session_ttl_seconds: int = 1800
    max_demo_sessions: int = 20
    allow_private_demo_hosts: bool = False

    # Comma-separated list of origins allowed to call this API from a
    # browser. Defaults to the local Vite dev server; a real deployment
    # should set this to the actual frontend origin(s), not "*".
    cors_allowed_origins: str = "http://localhost:5173"

    # Per-client-IP request caps, backed by Redis so they hold correctly
    # across multiple backend replicas. /query is the expensive one (it
    # burns LLM API calls, up to 3x per request via the correction loop),
    # so it gets the tightest limit.
    rate_limit_query_per_minute: int = 10
    rate_limit_demo_connect_per_minute: int = 5
    rate_limit_schema_per_minute: int = 30


settings = Settings()
