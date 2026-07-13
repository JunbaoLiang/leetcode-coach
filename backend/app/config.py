from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    database_url: str = f"sqlite:///{BACKEND_DIR / 'data' / 'app.db'}"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-5"
    # §9.4.3 — share of new-problem slots biased toward weak patterns
    weakness_weight: float = 0.4


settings = Settings()
