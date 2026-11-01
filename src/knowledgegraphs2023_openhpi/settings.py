from pathlib import Path

from dotenv import load_dotenv
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


def load_provider_environment(
    env_file: Path = config.PROJECT_ROOT / ".env",
) -> bool:
    """Expose provider API keys from .env for LangChain provider clients."""
    return load_dotenv(env_file, override=False)


load_provider_environment()
settings = Settings()
