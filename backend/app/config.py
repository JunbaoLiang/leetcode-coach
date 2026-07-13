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

    # M5 — GitHub OAuth multi-user mode. Off by default: local dev stays
    # single-user with no login. Enable in production.
    auth_enabled: bool = False
    github_client_id: str = ""
    github_client_secret: str = ""
    session_secret: str = ""  # required when auth_enabled
    # public URL of the app (scheme + host) for the OAuth redirect_uri;
    # empty = derive from the incoming request (fine behind the Vercel proxy)
    public_base_url: str = ""


settings = Settings()
