#!/usr/bin/env python3
"""
Tulkka AI - Main Application Entry Point

Production-ready FastAPI server for AI-powered language learning exercises.
"""

import os
import sys
import logging

import uvicorn

from src.api.app import app
from src.config import settings
from src.logging_config import configure_logging


def get_app_port() -> int:
    """Return server port, defaulting to 8000."""
    try:
        return int(os.getenv("APP_PORT", "8000"))
    except ValueError:
        return 8000


def get_workers() -> int:
    """Return number of workers based on environment."""
    if settings.is_production():
        # Use 2-4 workers in production
        return int(os.getenv("UVICORN_WORKERS", "2"))
    return 1


def main() -> None:
    """Run the application server."""
    configure_logging()
    logger = logging.getLogger(__name__)
    
    port = get_app_port()
    workers = get_workers()
    host = os.getenv("APP_HOST", "0.0.0.0")
    
    logger.info("=" * 50)
    logger.info("Starting Tulkka AI Server")
    logger.info("Environment: %s", settings.ENVIRONMENT)
    logger.info("Host: %s, Port: %d, Workers: %d", host, port, workers)
    logger.info("=" * 50)
    
    # Validate configuration
    warnings = settings.validate()
    for warning in warnings:
        logger.warning("Config: %s", warning)
    
    if settings.is_production():
        # Production: use multiple workers
        uvicorn.run(
            "src.api.app:app",
            host=host,
            port=port,
            workers=workers,
            log_level="info",
            access_log=True,
            proxy_headers=True,
            forwarded_allow_ips="*",
        )
    else:
        # Development: single worker with reload
        uvicorn.run(
            app,
            host=host,
            port=port,
            reload=os.getenv("UVICORN_RELOAD", "true").lower() == "true",
            log_level="debug",
        )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nServer stopped by user")
        sys.exit(0)
    except Exception as e:
        logging.exception("Server failed to start: %s", e)
        sys.exit(1)
