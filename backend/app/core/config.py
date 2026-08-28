from functools import lru_cache
from urllib.parse import quote_plus
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False)
    app_name: str = "Ticket Management System Backend"; app_version: str = "0.1.0"; environment: str = "development"
    postgres_user: str = "ticketing"; postgres_password: str = "ticketing"; postgres_host: str = "localhost"; postgres_port: int = 5432; postgres_db: str = "ticketing"
    jwt_secret: str = ""; jwt_algorithm: str = "HS256"; access_token_minutes: int = 15; refresh_token_days: int = 7
    redis_url: str = "redis://localhost:6379/0"; rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"; cors_origins: str = "http://localhost:3000"
    login_rate_limit: int = 5; login_rate_window_seconds: int = 60
    @field_validator("jwt_secret")
    @classmethod
    def validate_secret(cls, value: str, info):
        environment = info.data.get("environment", "development")
        if not value and environment in {"development", "test"}:
            return "development-only-secret-change-me-123456"
        if len(value) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters outside development")
        return value
    @property
    def database_url(self) -> str: return f"postgresql+psycopg://{quote_plus(self.postgres_user)}:{quote_plus(self.postgres_password)}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
    @property
    def cors_list(self) -> list[str]: return [x.strip() for x in self.cors_origins.split(",") if x.strip()]
@lru_cache
def get_settings() -> Settings: return Settings()
settings = get_settings()
