"""
Logging configuration for the application.

Sets up structured logging with rotating file handlers.
"""

import logging
import logging.handlers
import os
from backend.config import get_settings

settings = get_settings()


def setup_logger(name: str) -> logging.Logger:
    """
    Configure and return a logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        logging.Logger: Configured logger instance

    Note:
        Logs are written to both console and file with rotation.
    """
    logger = logging.getLogger(name)
    logger.setLevel(settings.log_level)

    # Create logs directory if it doesn't exist
    log_dir = os.path.dirname(settings.log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(settings.log_level)
    console_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(console_format)

    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        settings.log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=10,
    )
    file_handler.setLevel(settings.log_level)
    file_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
    )
    file_handler.setFormatter(file_format)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger
