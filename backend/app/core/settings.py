from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Visual Alpha Data Parser"
    api_prefix: str = "/api"
    data_dir: Path = Path("data")
    database_url: str = "sqlite:///data/visual_alpha.db"
    cors_origins: str = "http://localhost:5173,http://localhost:8080"
    mistral_api_key: str | None = None
    mistral_ocr_model: str = "mistral-ocr-latest"
    remote_timeout_seconds: float = 45.0

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
