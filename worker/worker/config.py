from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    database_url: str = "sqlite:///./worthit.db"

    model_config = SettingsConfigDict(env_file=".env", env_prefix="WORTHIT_")


@lru_cache
def get_settings() -> WorkerSettings:
    return WorkerSettings()
