"""Application configuration with environment variable support."""

from functools import lru_cache
from typing import Literal, Set

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    # Application
    app_name: str = "Media Converter"
    app_env: Literal["development", "production", "testing"] = "development"
    debug: bool = False

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # File handling
    upload_dir: str = "./uploads"
    max_file_size_mb: int = 100
    allowed_extensions: Set[str] = {".ppt", ".pptx"}
    allowed_pdf_extensions: Set[str] = {".pdf"}

    # Conversion settings
    image_dpi: int = Field(default=200, ge=72, le=600)
    image_format: Literal["JPEG", "PNG"] = "JPEG"
    jpeg_quality: int = Field(default=90, ge=1, le=100)

    # Concurrency
    max_workers: int = Field(default=3, ge=1, le=10)
    job_timeout_seconds: int = 300

    # Cleanup
    job_ttl_hours: int = 24

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
