from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized application configuration loaded from environment."""

    spotify_client_id: str
    spotify_client_secret: str
    spotify_redirect_uri: str = "http://localhost:8888/callback"

    llm_provider: Literal["groq", "ollama"] = "groq"
    groq_api_key: str | None = None
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"

    log_level: str = "INFO"
    cache_genres: bool = True
    genre_cache_ttl: int = 60 * 60 * 24  # seconds

    spotify_request_timeout: int = 30
    llm_request_timeout: int = 60
    max_retries: int = 3

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    def validate_llm(self) -> None:
        """Ensure required credentials are present for chosen LLM provider."""
        if self.llm_provider == "groq" and not self.groq_api_key:
            msg = "GROQ_API_KEY is required when LLM_PROVIDER=groq"
            raise ValueError(msg)


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    settings = Settings()
    settings.validate_llm()
    return settings
