# src/config.py
"""Application configuration with environment variable loading and validation."""

import os
import logging
from typing import Optional, List
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class Settings:
    # General
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Supabase
    SUPABASE_URL: Optional[str] = os.getenv("SUPABASE_URL")
    SUPABASE_KEY: Optional[str] = os.getenv("SUPABASE_KEY")

    # MySQL
    MYSQL_HOST: str = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_PORT: int = int(os.getenv("MYSQL_PORT", "3306"))
    MYSQL_USER: Optional[str] = os.getenv("MYSQL_USER")
    MYSQL_PASSWORD: Optional[str] = os.getenv("MYSQL_PASSWORD")
    MYSQL_DATABASE: str = os.getenv("MYSQL_DATABASE", "tulkka9")
    MYSQL_POOL_NAME: str = os.getenv("MYSQL_POOL_NAME", "tulkka_pool")
    MYSQL_POOL_SIZE: int = int(os.getenv("MYSQL_POOL_SIZE", "10"))

    # Zoom
    ZOOM_CLIENT_ID: Optional[str] = os.getenv("ZOOM_CLIENT_ID")
    ZOOM_CLIENT_SECRET: Optional[str] = os.getenv("ZOOM_CLIENT_SECRET")
    ZOOM_ACCESS_TOKEN: Optional[str] = os.getenv("ZOOM_ACCESS_TOKEN")
    ZOOM_REFRESH_TOKEN: Optional[str] = os.getenv("ZOOM_REFRESH_TOKEN")
    ZOOM_TOKEN_EXPIRES_AT: Optional[str] = os.getenv(
        "ZOOM_TOKEN_EXPIRES_AT"
    )  # optional

    # AssemblyAI (optional)
    ASSEMBLYAI_API_KEY: Optional[str] = os.getenv("ASSEMBLYAI_API_KEY")
    ASSEMBLYAI_BASE_URL: str = os.getenv(
        "ASSEMBLYAI_BASE_URL", "https://api.assemblyai.com/v2"
    )

    # Groq AI
    GROQ_API_KEY: Optional[str] = os.getenv("GROQ_API_KEY")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    # Google Gemini (for transcription and content generation)
    GOOGLE_API_KEY: Optional[str] = os.getenv("GOOGLE_API_KEY") or os.getenv(
        "GEMINI_API_KEY"
    )
    GEMINI_TRANSCRIPTION_MODEL: str = os.getenv(
        "GEMINI_TRANSCRIPTION_MODEL", "gemini-2.5-flash"
    )

    # Security
    JWT_SECRET: Optional[str] = os.getenv("JWT_SECRET")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")

    # Misc
    TEMP_DIR: str = os.getenv("TEMP_DIR", "/tmp")

    # Worker settings
    WORKER_POLL_INTERVAL_SECONDS: int = int(
        os.getenv("WORKER_POLL_INTERVAL_SECONDS", "60")
    )
    WORKER_BATCH_SIZE: int = int(os.getenv("WORKER_BATCH_SIZE", "10"))
    WORKER_MAX_RETRIES: int = int(os.getenv("WORKER_MAX_RETRIES", "3"))

    # CORS settings (production-safe defaults)
    CORS_ORIGINS: List[str] = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS", "http://localhost:3000,http://localhost:8080"
        ).split(",")
        if origin.strip()
    ]
    CORS_ALLOW_ALL: bool = os.getenv("CORS_ALLOW_ALL", "false").lower() == "true"

    # Rate limiting
    RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
    RATE_LIMIT_WINDOW_SECONDS: int = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))

    def validate(self) -> List[str]:
        """Validate configuration and return list of warnings."""
        warnings: List[str] = []

        if self.ENVIRONMENT == "production":
            if not self.JWT_SECRET:
                warnings.append("JWT_SECRET not set - authentication will fail")
            if self.CORS_ALLOW_ALL:
                warnings.append(
                    "CORS_ALLOW_ALL is enabled in production - security risk"
                )
            if not self.SUPABASE_URL or not self.SUPABASE_KEY:
                warnings.append("Supabase credentials missing")

        return warnings

    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.ENVIRONMENT.lower() == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()

# Log configuration warnings on import
_warnings = settings.validate()
for _w in _warnings:
    logger.warning("Config warning: %s", _w)
