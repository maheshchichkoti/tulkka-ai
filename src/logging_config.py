# src/logging_config.py
import logging
from logging.handlers import RotatingFileHandler
from .config import settings

_logging_configured = False


def configure_logging():
    """Configure logging once. Safe to call multiple times."""
    global _logging_configured
    if _logging_configured:
        return
    
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    logger = logging.getLogger()
    logger.setLevel(level)

    fmt = "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
    formatter = logging.Formatter(fmt)

    # Console handler
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # Rotating file handler (safe default)
    fh = RotatingFileHandler("tulkka.log", maxBytes=10 * 1024 * 1024, backupCount=5)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    
    _logging_configured = True
