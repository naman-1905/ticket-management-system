from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str
    jwt_secret_key: str
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30
    app_version: str = "1.0.0"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
