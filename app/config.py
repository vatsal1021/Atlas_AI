"""Application configuration using pydantic-settings.

Loads all environment variables and exposes a singleton via get_settings().
"""

import logging
from functools import lru_cache

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Central configuration loaded from environment variables / .env file."""

    # --- LLM ---
    openai_api_key: str = Field(default="", description="OpenAI API key")
    anthropic_api_key: str = Field(default="", description="Anthropic API key")
    groq_api_key: str = Field(default="", description="Groq API key")
    ollama_base_url: str = Field(default="http://localhost:11434", description="Ollama API base URL")
    llm_provider: str = Field(default="groq", description="LLM provider: openai, anthropic, groq, or ollama")
    llm_model: str = Field(default="llama3-8b-8192", description="Model identifier")

    # --- External APIs ---
    amadeus_api_key: str = Field(default="", description="Amadeus API key")
    amadeus_api_secret: str = Field(default="", description="Amadeus API secret")
    google_maps_api_key: str = Field(default="", description="Google Maps API key")
    weather_api_key: str = Field(default="", description="Weather API key")

    # --- App behaviour ---
    log_level: str = Field(default="INFO", description="Logging level")
    max_planner_iterations: int = Field(default=10, description="Max planning loop iterations")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton of the application settings."""
    return Settings()


def configure_logging(level: str | None = None) -> None:
    """Configure root logger based on settings."""
    resolved_level = level or get_settings().log_level
    logging.basicConfig(
        level=getattr(logging, resolved_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
