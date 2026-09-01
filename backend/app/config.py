from pydantic_settings import BaseSettings, SettingsConfigDict


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

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
