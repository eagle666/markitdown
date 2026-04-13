"""Application configuration."""

import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="MARKITDOWN_",
        case_sensitive=False,
    )

    # API Settings
    app_name: str = "MarkItDown API"
    app_version: str = "0.1.0"
    debug: bool = False

    # Server Settings
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4  # uvicorn workers per instance

    # MarkItDown Pool Settings
    markitdown_pool_size: int = 2  # instances per worker
    markitdown_enable_plugins: bool = False

    # File Upload Settings
    max_file_size_mb: int = 1024  # 1GB
    max_file_size_bytes: int = 1024 * 1024 * 1024
    allowed_extensions: list[str] = [
        ".pdf", ".pptx", ".docx", ".xlsx", ".xls",
        ".html", ".htm", ".csv", ".json", ".xml",
        ".zip", ".epub", ".ipynb", ".md",
        # Media (metadata/OCR)
        ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".tif",
        # Audio
        ".mp3", ".wav", ".flac", ".m4a", ".ogg",
        # YouTube
    ]

    # Rate Limiting
    rate_limit_requests: int = 100  # per window
    rate_limit_window_seconds: int = 60

    # CORS
    cors_origins: list[str] = ["*"]

    # Authentication
    # API keys as comma-separated string (e.g., "key1,key2,key3")
    api_keys: str = ""  # Will be parsed from env or comma-separated
    api_keys_required: bool = False

    def model_post_init(self, *args, **kwargs):
        """Parse api_keys after initialization."""
        # Parse comma-separated API keys from the api_keys field
        if self.api_keys:
            # If api_keys is a comma-separated string, split it
            if "," in self.api_keys:
                self._api_keys_list = [k.strip() for k in self.api_keys.split(",") if k.strip()]
            else:
                self._api_keys_list = [self.api_keys.strip()] if self.api_keys.strip() else []
        else:
            self._api_keys_list = []

    @property
    def api_keys_list(self) -> list[str]:
        """Get the list of API keys."""
        return self._api_keys_list


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()