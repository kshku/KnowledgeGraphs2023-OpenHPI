from pydantic_settings import BaseSettings, SettingsConfigDict

from . import config


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=f"{config.PROJECT_ROOT}/.env",
        env_prefix="KG_",
        extra="ignore",
    )

    model_provider: str = "openai"
    model_name: str = "gpt-4o-mini"
    read_only: bool = True
    max_sparql_rows: int = 50


settings = Settings()
