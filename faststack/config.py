"""
FastStack Configuration Module

This module provides centralized configuration management using Pydantic Settings.
Configuration values are loaded from environment variables with sensible defaults.

Usage:
    from faststack.config import settings
    print(settings.DATABASE_URL)
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    All settings can be overridden via:
    1. Environment variables (uppercase)
    2. .env file in the project root
    3. Direct assignment in code
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Application Settings
    APP_NAME: str = "FastStack App"
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "change-this-secret-key-in-production"

    # Database Configuration
    DATABASE_URL: str = "sqlite:///./faststack.db"
    DATABASE_ECHO: bool = False
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10

    # Server Configuration
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    RELOAD: bool = True

    # Session Settings
    SESSION_MAX_AGE: int = 86400  # 24 hours
    SESSION_COOKIE_NAME: str = "session_id"
    SESSION_COOKIE_SECURE: bool = False
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: str = "lax"

    # CSRF Settings
    CSRF_ENABLED: bool = True
    CSRF_TOKEN_NAME: str = "csrf_token"
    CSRF_HEADER_NAME: str = "X-CSRF-Token"
    CSRF_COOKIE_NAME: str = "csrf_token"
    CSRF_EXPIRY: int = 3600  # 1 hour

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 60
    RATE_LIMIT_REQUESTS_PER_HOUR: int = 1000
    RATE_LIMIT_BLOCK_DURATION: int = 300  # 5 minutes

    # Security Headers
    SECURITY_HEADERS_ENABLED: bool = True
    HSTS_ENABLED: bool = False
    CSP_ENABLED: bool = True

    # JWT Settings
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_ISSUER: str = "faststack"
    JWT_AUDIENCE: str = "faststack-users"

    # CORS Settings (must be after JWT settings)
    CORS_ORIGINS: list[str] = ["http://localhost:8000", "http://localhost:3000"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list[str] = ["*"]
    CORS_ALLOW_HEADERS: list[str] = ["*"]

    # Email Settings
    EMAIL_ENABLED: bool = False
    EMAIL_HOST: str = "localhost"
    EMAIL_PORT: int = 25
    EMAIL_USE_TLS: bool = False
    EMAIL_USE_SSL: bool = False
    EMAIL_HOST_USER: str = ""
    EMAIL_HOST_PASSWORD: str = ""
    EMAIL_FROM: str = "noreply@example.com"
    EMAIL_FROM_NAME: str = "FastStack"

    # File Upload Settings
    UPLOAD_DIR: str = "uploads"
    UPLOAD_MAX_SIZE: int = 10 * 1024 * 1024  # 10 MB
    UPLOAD_ALLOWED_EXTENSIONS: list[str] = [
        "jpg", "jpeg", "png", "gif", "webp",  # Images
        "pdf", "doc", "docx", "xls", "xlsx",  # Documents
        "mp3", "mp4", "wav", "avi",  # Media
    ]
    UPLOAD_IMAGE_MAX_WIDTH: int = 1920
    UPLOAD_IMAGE_MAX_HEIGHT: int = 1080

    # Password Reset
    PASSWORD_RESET_EXPIRE_HOURS: int = 24
    PASSWORD_RESET_TOKEN_NAME: str = "password_reset_token"

    # Admin Settings
    ADMIN_MOUNT_PATH: str = "/admin"
    ADMIN_SITE_HEADER: str = "FastStack Admin"
    ADMIN_SITE_TITLE: str = "FastStack Administration"

    # Template Settings
    TEMPLATES_DIR: str = "templates"
    TEMPLATES_AUTO_RELOAD: bool = True

    # Static Files
    STATIC_DIR: str = "static"
    STATIC_URL: str = "/static"

    # Apps Configuration
    APPS_DIR: str = "apps"
    APPS_PREFIX: str = ""

    # Security Settings
    PASSWORD_MIN_LENGTH: int = 8
    PASSWORD_REQUIRE_UPPERCASE: bool = True
    PASSWORD_REQUIRE_LOWERCASE: bool = True
    PASSWORD_REQUIRE_DIGITS: bool = True
    PASSWORD_REQUIRE_SPECIAL: bool = False

    # Pagination
    PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.APP_ENV == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.APP_ENV == "production"

    @property
    def is_testing(self) -> bool:
        """Check if running in testing mode."""
        return self.APP_ENV == "testing"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> list[str]:
        """Parse CORS origins from comma-separated string if needed."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @property
    def base_dir(self) -> Path:
        """Get the base directory of the project."""
        return Path.cwd()

    @property
    def apps_dir(self) -> Path:
        """Get the apps directory path."""
        return self.base_dir / self.APPS_DIR

    @property
    def templates_dir(self) -> Path:
        """Get the templates directory path."""
        return self.base_dir / self.TEMPLATES_DIR

    @property
    def static_dir(self) -> Path:
        """Get the static files directory path."""
        return self.base_dir / self.STATIC_DIR

    @property
    def upload_dir(self) -> Path:
        """Get the upload directory path."""
        return self.base_dir / self.UPLOAD_DIR

    def get_database_url(self, async_driver: bool = False) -> str:
        """
        Get the database URL with optional async driver.

        Args:
            async_driver: If True, converts sqlite:// to sqlite+aiosqlite://
                         and postgresql:// to postgresql+asyncpg://

        Returns:
            Database connection URL
        """
        url = self.DATABASE_URL

        if async_driver:
            if url.startswith("sqlite://"):
                return url.replace("sqlite://", "sqlite+aiosqlite://", 1)
            elif url.startswith("postgresql://"):
                return url.replace("postgresql://", "postgresql+asyncpg://", 1)
            elif url.startswith("mysql://"):
                return url.replace("mysql://", "mysql+aiomysql://", 1)

        return url


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.

    This function returns a cached Settings instance to avoid
    re-reading environment variables on every access.

    Returns:
        Settings: Application settings instance
    """
    return Settings()


# Global settings instance
settings = get_settings()
