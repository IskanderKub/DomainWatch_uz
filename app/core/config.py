# Application settings, populated from environment variables / .env file.
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    postgres_url: str = "postgresql://user:password@localhost/domainwatch"

    mongo_url: str = "mongodb://localhost:27017"
    mongo_db_name: str = "domainwatch"

    check_timeout_seconds: int = 5  # how long to wait before treating a domain as unavailable
    content_change_threshold: float = 0.4  # similarity below this vs previous snapshot => has_global_changes
    check_interval_minutes: int = 60  # how often the scheduler re-checks all active domains
    snapshot_ttl_days: int = 30 # how long page snapshots are kept before Mongo expires them

    # env_file tells pydantic-settings to also read values from a local .env file
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


# Single settings instance imported everywhere else in the app
settings = Settings()
