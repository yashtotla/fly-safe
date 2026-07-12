"""Runtime configuration, loaded from environment / .env."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Flight-status source (AeroDataBox). Empty until a key is provided.
    aerodatabox_api_key: str = ""

    # Disposable snapshot cache. Repopulates from sources on each poll.
    database_url: str = "sqlite+aiosqlite:///./flysafe.db"

    # Frontend origins allowed to call the API (Vite dev server by default).
    cors_origins: list[str] = ["http://localhost:5173"]


settings = Settings()
