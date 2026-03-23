"""
FastStack Configuration Module

This module provides centralized configuration management using Pydantic Settings.
Configuration values are loaded from environment variables with sensible defaults.

Usage:
    from faststack.config import settings
    print(settings.DATABASE_URL)
"""

import os
import secrets
import warnings
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from pydantic import field_validator, model_validator
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
        env_file=[".env", "../.env", "../../.env"],
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Application Settings
    APP_NAME: str = "FastStack App"
    APP_ENV: str = "development"
    DEBUG: bool = False  # Changed: Default to False for security
    SECRET_KEY: str = ""  # Changed: Empty default, must be set

    # Database Configuration
    DATABASE_URL: str = "sqlite:///./faststack.db"
    DATABASE_ECHO: bool = False
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_POOL_TIMEOUT: int = 30  # New: Connection pool timeout
    DATABASE_POOL_PRE_PING: bool = True  # New: Check connection health

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
    SESSION_REGENERATE_ON_LOGIN: bool = True  # New: Prevent session fixation

    # CSRF Settings
    CSRF_ENABLED: bool = True
    CSRF_TOKEN_NAME: str = "csrf_token"
    CSRF_HEADER_NAME: str = "X-CSRF-Token"
    CSRF_COOKIE_NAME: str = "csrf_token"
    CSRF_EXPIRY: int = 3600  # 1 hour
    CSRF_BIND_TO_SESSION: bool = True  # New: Bind CSRF token to session

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 60
    RATE_LIMIT_REQUESTS_PER_HOUR: int = 1000
    RATE_LIMIT_BLOCK_DURATION: int = 300  # 5 minutes
    RATE_LIMIT_REDIS_URL: str = ""  # New: Redis URL for distributed rate limiting
    RATE_LIMIT_TRUSTED_PROXIES: list[str] = []  # New: Trusted proxy IPs for X-Forwarded-For

    # Security Headers
    SECURITY_HEADERS_ENABLED: bool = True
    HSTS_ENABLED: bool = False
    CSP_ENABLED: bool = True

    # JWT Settings
    JWT_SECRET_KEY: str = ""  # Changed: Empty default, must be set
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_ISSUER: str = "faststack"
    JWT_AUDIENCE: str = "faststack-users"
    JWT_BLACKLIST_ENABLED: bool = True  # New: Enable token blacklisting

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
    UPLOAD_VALIDATE_CONTENT: bool = True  # New: Validate file content (magic bytes)
    UPLOAD_MAX_FILES_PER_USER: int = 100  # New: Max files per user
    UPLOAD_STORAGE_QUOTA_MB: int = 100  # New: Storage quota per user in MB

    # Password Reset
    PASSWORD_RESET_EXPIRE_HOURS: int = 24
    PASSWORD_RESET_TOKEN_NAME: str = "password_reset_token"

    # Brute Force Protection (New)
    BRUTE_FORCE_ENABLED: bool = True
    BRUTE_FORCE_MAX_ATTEMPTS: int = 5
    BRUTE_FORCE_LOCKOUT_DURATION: int = 900  # 15 minutes
    BRUTE_FORCE_PROGRESSIVE_DELAY: bool = True  # Increase delay after each failed attempt

    # Admin Settings
    ADMIN_MOUNT_PATH: str = "/admin"
    ADMIN_SITE_HEADER: str = "FastStack Admin"
    ADMIN_SITE_TITLE: str = "FastStack Administration"
    ADMIN_OPTIMISTIC_LOCKING: bool = True  # New: Enable optimistic locking

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
    PASSWORD_HISTORY_COUNT: int = 5  # New: Prevent reusing last N passwords

    # Pagination
    PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    # Frontend Settings
    # Options: "fastui" (single CDN bundle) or "default" (individual libraries)
    FRONTEND_MODE: str = "fastui"

    # FastUI CDN URL (when FRONTEND_MODE = "fastui")
    FASTUI_CDN_URL: str = "https://cdn.jsdelivr.net/npm/fastt-ui@0.1.8/dist/fast-ui.min.js"

    # Individual library versions (when FRONTEND_MODE = "default")
    HTMX_CDN_URL: str = "https://cdn.jsdelivr.net/npm/htmx.org@2.0.8/dist/htmx.min.js"
    ALPINE_CDN_URL: str = "https://cdn.jsdelivr.net/npm/alpinejs@3.15.8/dist/cdn.min.js"
    ECHARTS_CDN_URL: str = "https://cdn.jsdelivr.net/npm/echarts@6.0.0/dist/echarts.min.js"
    TAILWIND_CDN_URL: str = "https://cdn.tailwindcss.com"
    FLOWBITE_CSS_URL: str = "https://cdn.jsdelivr.net/npm/flowbite@4.0.1/dist/flowbite.min.css"
    FLOWBITE_JS_URL: str = "https://cdn.jsdelivr.net/npm/flowbite@4.0.1/dist/flowbite.min.js"

    # Optional: Enable/disable specific features
    FRONTEND_ENABLE_ECHARTS: bool = True
    FRONTEND_ENABLE_FLOWBITE: bool = True

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

    @property
    def use_fastui(self) -> bool:
        """Check if using FastUI bundled mode."""
        return self.FRONTEND_MODE == "fastui"

    @property
    def frontend_settings(self) -> dict:
        """Get frontend configuration as a dict for template context."""
        return {
            "mode": self.FRONTEND_MODE,
            "fastui_cdn": self.FASTUI_CDN_URL,
            "htmx_cdn": self.HTMX_CDN_URL,
            "alpine_cdn": self.ALPINE_CDN_URL,
            "echarts_cdn": self.ECHARTS_CDN_URL,
            "tailwind_cdn": self.TAILWIND_CDN_URL,
            "flowbite_css": self.FLOWBITE_CSS_URL,
            "flowbite_js": self.FLOWBITE_JS_URL,
            "enable_echarts": self.FRONTEND_ENABLE_ECHARTS,
            "enable_flowbite": self.FRONTEND_ENABLE_FLOWBITE,
        }

    @model_validator(mode="after")
    def validate_security_settings(self) -> "Settings":
        """Validate and warn about insecure settings."""
        # Generate SECRET_KEY if not set
        if not self.SECRET_KEY:
            if self.is_production:
                raise ValueError(
                    "SECRET_KEY must be set in production! "
                    "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
                )
            # Generate a random key for development
            self.SECRET_KEY = secrets.token_urlsafe(32)
            warnings.warn(
                "SECRET_KEY not set. Using a randomly generated key. "
                "Set SECRET_KEY environment variable for production.",
                UserWarning,
            )

        # Generate JWT_SECRET_KEY if not set
        if not self.JWT_SECRET_KEY:
            if self.is_production:
                raise ValueError(
                    "JWT_SECRET_KEY must be set in production! "
                    "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
                )
            self.JWT_SECRET_KEY = secrets.token_urlsafe(32)
            warnings.warn(
                "JWT_SECRET_KEY not set. Using a randomly generated key. "
                "Set JWT_SECRET_KEY environment variable for production.",
                UserWarning,
            )

        # Warn about DEBUG=True in production
        if self.DEBUG and self.is_production:
            warnings.warn(
                "DEBUG=True is enabled in production! This is a security risk.",
                UserWarning,
            )

        # Warn about insecure session cookie in production
        if not self.SESSION_COOKIE_SECURE and self.is_production:
            warnings.warn(
                "SESSION_COOKIE_SECURE=False in production. "
                "Set SESSION_COOKIE_SECURE=True for HTTPS.",
                UserWarning,
            )

        # Validate CORS settings
        if self.CORS_ALLOW_CREDENTIALS and "*" in self.CORS_ORIGINS:
            raise ValueError(
                "CORS_ALLOW_CREDENTIALS=True cannot be used with CORS_ORIGINS=['*']. "
                "Specify explicit origins instead."
            )

        return self

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> list[str]:
        """Parse CORS origins from comma-separated string if needed."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @field_validator("RATE_LIMIT_TRUSTED_PROXIES", mode="before")
    @classmethod
    def parse_trusted_proxies(cls, v: Any) -> list[str]:
        """Parse trusted proxies from comma-separated string if needed."""
        if isinstance(v, str):
            return [ip.strip() for ip in v.split(",") if ip.strip()]
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
