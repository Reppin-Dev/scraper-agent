"""Application configuration management."""
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Anthropic API Configuration
    anthropic_api_key: str = ""  # Required - set via ANTHROPIC_API_KEY env var

    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True

    # Storage Configuration
    storage_base_path: str = "/app/data"  # Changed from ~/Downloads for container compatibility

    # Agent Configuration
    max_parallel_extractions: int = 3
    default_timeout: int = 30

    # Model Configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @property
    def storage_path(self) -> Path:
        """Get the resolved storage path."""
        return Path(self.storage_base_path).expanduser().resolve()


# Global settings instance
settings = Settings()
