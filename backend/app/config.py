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

    # Live polling. OFF by default so dev/reload never spends AeroDataBox units;
    # the API serves fixture-seeded data. Turn on for the live end-to-end check / prod.
    poll_enabled: bool = False

    # Failure alerts -> auto-filed GitHub issue (needs a repo-scoped token).
    github_token: str = ""
    github_repo: str = "yashtotla/fly-safe"
    failure_alert_threshold: int = 3

    # Freshness (max_age) + poll cadence per source, in seconds.
    # Flight status is budget-bound (~6 units/call, ~100/month) -> ~1x/day.
    flight_max_age_seconds: int = 30 * 3600
    flight_poll_seconds: int = 24 * 3600
    advisory_max_age_seconds: int = 24 * 3600
    advisory_poll_seconds: int = 24 * 3600
    czib_max_age_seconds: int = 24 * 3600
    czib_poll_seconds: int = 24 * 3600


settings = Settings()
