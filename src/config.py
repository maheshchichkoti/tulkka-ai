# src/config.py
import os
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


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
    ZOOM_TOKEN_EXPIRES_AT: Optional[str] = os.getenv("ZOOM_TOKEN_EXPIRES_AT")  # optional

    # AssemblyAI (optional)
    ASSEMBLYAI_API_KEY: Optional[str] = os.getenv("ASSEMBLYAI_API_KEY")
    ASSEMBLYAI_BASE_URL: str = os.getenv("ASSEMBLYAI_BASE_URL", "https://api.assemblyai.com/v2")

    # n8n integration
    N8N_WEBHOOK_URL: Optional[str] = os.getenv("N8N_WEBHOOK_URL")

    # Groq AI
    GROQ_API_KEY: Optional[str] = os.getenv("GROQ_API_KEY")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama3-70b-8192")

    # Worker tuning
    WORKER_POLL_INTERVAL_SECONDS: int = int(os.getenv("WORKER_POLL_INTERVAL_SECONDS", "300"))
    WORKER_BATCH_SIZE: int = int(os.getenv("WORKER_BATCH_SIZE", "10"))
    WORKER_MAX_RETRIES: int = int(os.getenv("WORKER_MAX_RETRIES", "5"))

    # Security
    JWT_SECRET: Optional[str] = os.getenv("JWT_SECRET")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")

    # Misc
    TEMP_DIR: str = os.getenv("TEMP_DIR", "/tmp")


settings = Settings()
