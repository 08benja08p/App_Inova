from pydantic_settings import BaseSettings
from pydantic import Field
import os


class Settings(BaseSettings):
    app_name: str = "Inova Docs API"
    debug: bool = True
    database_url: str = Field(
        default_factory=lambda: f"sqlite:///"
        + os.path.abspath("backend/data/app_v2.sqlite3")
    )
    storage_dir: str = Field(default_factory=lambda: os.path.abspath("backend/storage"))

    class Config:
        env_file = ".env"
        extra = "ignore"


def get_settings() -> Settings:
    settings = Settings()
    os.makedirs(settings.storage_dir, exist_ok=True)
    os.makedirs(
        os.path.dirname(settings.database_url.replace("sqlite:///", "")), exist_ok=True
    )
    return settings
