from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_name: str = "Ticket Management System Backend"; app_version: str = "0.1.0"; environment: str = "development"
    postgres_user: str = "ticketing"; postgres_password: str = "ticketing"; postgres_host: str = "localhost"; postgres_port: int = 5432; postgres_db: str = "ticketing"
    jwt_secret: str = "change-me-in-production"; jwt_algorithm: str = "HS256"; access_token_minutes: int = 15; refresh_token_days: int = 7
    redis_url: str = "redis://localhost:6379/0"; rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"; cors_origins: str = "*"
    @property
    def database_url(self) -> str: return f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
    @property
    def cors_list(self) -> list[str]: return [x.strip() for x in self.cors_origins.split(",")]
@lru_cache
def get_settings() -> Settings: return Settings()
settings = get_settings()
