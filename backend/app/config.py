from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="DIP_", extra="ignore")

    app_name: str = "Data Integration Platform"
    environment: str = "development"
    database_url: str = "sqlite+aiosqlite:///./dip.db"
    secret_key: str = "change-me-in-production"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    # ``flutter run -d chrome`` picks a random port each launch; allow any
    # localhost/127.0.0.1 origin so the dev workflow doesn't need CORS
    # tweaks on every restart. Tighten this for production.
    cors_origin_regex: str = r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"
    log_level: str = "INFO"
    scheduler_enabled: bool = True
    # How often the freshness checker scans assets. 60s is a sensible
    # default for v1; large deployments may want a longer interval.
    freshness_check_interval_seconds: int = 60
    # Where YAML pipeline definitions live. Relative paths are resolved
    # against the backend's working directory.
    definitions_dir: str = "definitions"
    # If true, the loader runs once on startup; reload on demand via the
    # `POST /api/definitions/reload` endpoint.
    autoload_definitions: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
