from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./assistant.db"
    secret_key: SecretStr = Field(min_length=32)
    algorithm: Literal["HS256"] = "HS256"
    access_token_expire_minutes: int = Field(default=30, gt=0)

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
