"""Application configuration."""

import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

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
    api_keys: list[str] = os.getenv("MARKITDOWN_API_KEYS", "").split(",") if os.getenv("MARKITDOWN_API_KEYS") else []

    class Config:
        env_prefix = "MARKITDOWN_"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()