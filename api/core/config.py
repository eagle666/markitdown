"""Application configuration."""

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
        # Documents
        ".pdf", ".pptx", ".docx", ".xlsx", ".xls",
        # Web
        ".html", ".htm",
        # Data
        ".csv", ".json", ".xml",
        # Archives
        ".zip", ".epub", ".ipynb", ".md",
        # Images
        ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".tif",
        # Audio/Video
        ".mp3", ".wav", ".flac", ".m4a", ".ogg", ".mp4", ".avi", ".mkv", ".mov", ".wmv",
    ]

    # CORS
    cors_origins: list[str] = ["*"]


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
