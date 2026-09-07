import json
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _load_google_oauth_credentials(credentials_file: str) -> tuple[str, str]:
    if not credentials_file:
        return "", ""
    path = Path(credentials_file)
    if not path.is_file():
        return "", ""
    data = json.loads(path.read_text(encoding="utf-8"))
    web = data.get("web") or data.get("installed") or {}
    return web.get("client_id", ""), web.get("client_secret", "")


class Settings(BaseSettings):
    database_url: str
    jwt_secret_key: str
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30
    app_version: str = "2.0.0"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    docs_enabled: bool = True
    storage_dir: str = "./storage"
    worker_poll_seconds: int = 30
    login_rate_limit_per_minute: int = 20

    # Google OAuth (client id/secret loaded from JSON credentials file)
    google_client_credentials_file: str = ""
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:3000/auth/google/callback"

    # Local LLM (OpenAI-compatible)
    llm_base_url: str = "http://localhost:8888/api/v1"
    llm_api_key: str = ""
    llm_model: str = "default"

    # Gmail sync
    email_sync_interval_seconds: int = 300

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @model_validator(mode="after")
    def _load_google_credentials(self):
        if self.google_client_credentials_file:
            client_id, client_secret = _load_google_oauth_credentials(
                self.google_client_credentials_file
            )
            self.google_client_id = client_id
            self.google_client_secret = client_secret
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
