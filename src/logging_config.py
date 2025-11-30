# src/logging_config.py
"""Logging configuration for Tulkka AI."""

from __future__ import annotations
import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from typing import Optional

from .config import settings

_logging_configured = False


class RequestIdFilter(logging.Filter):
    """Add request ID to log records if available."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, 'request_id'):
            record.request_id = '-'
        return True


def configure_logging(
    log_file: Optional[str] = None,
    json_format: bool = False
) -> None:
    """
    Configure application logging.
    
    Args:
        log_file: Optional path to log file. Defaults to 'tulkka.log' or disabled in production.
        json_format: If True, use JSON format for logs (useful for log aggregation).
    
    Safe to call multiple times - only configures once.
    """
    global _logging_configured
    if _logging_configured:
        return
    
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Clear existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Format string
    if json_format or settings.is_production():
        # Structured format for production (easier to parse)
        fmt = '{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","file":"%(filename)s:%(lineno)d","request_id":"%(request_id)s","message":"%(message)s"}'
    else:
        # Human-readable format for development
        fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(filename)s:%(lineno)d | %(message)s"
    
    formatter = logging.Formatter(fmt, datefmt="%Y-%m-%d %H:%M:%S")

    # Console handler (always enabled)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(RequestIdFilter())
    root_logger.addHandler(console_handler)

    # File handler (optional, disabled in containerized environments by default)
    enable_file_logging = os.getenv("ENABLE_FILE_LOGGING", "false").lower() == "true"
    
    if enable_file_logging or not settings.is_production():
        log_path = log_file or os.getenv("LOG_FILE", "tulkka.log")
        try:
            file_handler = RotatingFileHandler(
                log_path,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5,
                encoding="utf-8"
            )
            file_handler.setFormatter(formatter)
            file_handler.addFilter(RequestIdFilter())
            root_logger.addHandler(file_handler)
        except (OSError, PermissionError) as e:
            # Don't fail if we can't write to log file
            root_logger.warning("Could not create log file %s: %s", log_path, e)

    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    
    _logging_configured = True
    
    root_logger.info(
        "Logging configured: level=%s, environment=%s",
        settings.LOG_LEVEL,
        settings.ENVIRONMENT
    )
