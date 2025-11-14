# src/logging_config.py
import logging
from logging.handlers import RotatingFileHandler
from .config import settings

def configure_logging():
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

# Configure on import
configure_logging()
