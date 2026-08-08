from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://nlsql_app:nlsql_app@localhost:5432/nlsql"
    redis_url: str = "redis://localhost:6379/0"

    openai_api_key: str = ""
    chat_model: str = "gpt-4o-mini"

    schema_cache_ttl_seconds: int = 3600
    max_correction_attempts: int = 3
    max_result_rows: int = 200

    # Demo mode: visitors can try the service against their own Postgres
    # database for a single, unpersisted session.
    demo_session_ttl_seconds: int = 1800
    max_demo_sessions: int = 20
    allow_private_demo_hosts: bool = False


settings = Settings()
