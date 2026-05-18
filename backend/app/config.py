from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="DIP_", extra="ignore")

    app_name: str = "Data Integration Platform"
    environment: str = "development"
    database_url: str = "sqlite+aiosqlite:///./dip.db"
    secret_key: str = "change-me-in-production"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    log_level: str = "INFO"
    scheduler_enabled: bool = True
    # Where YAML pipeline definitions live. Relative paths are resolved
    # against the backend's working directory.
    definitions_dir: str = "definitions"
    # If true, the loader runs once on startup; reload on demand via the
    # `POST /api/definitions/reload` endpoint.
    autoload_definitions: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
