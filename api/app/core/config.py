from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "WorthIt API"
    env: str = "dev"
    database_url: str = Field(default="sqlite:///./worthit.db")
    redis_url: str = Field(default="redis://localhost:6379/0")
    cache_enabled: bool = True
    admin_token: str = "dev-admin-token"
    cache_schema_version: str = "1"

    model_config = SettingsConfigDict(env_file=".env", env_prefix="WORTHIT_")


@lru_cache
def get_settings() -> Settings:
    return Settings()
