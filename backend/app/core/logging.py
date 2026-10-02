"""Logging configuration for Document Assistant Backend.

Ensures structured, privacy-preserving logging without leaking sensitive document
content or raw OCR text into console or log files.
"""

import logging
import sys
from typing import Optional


def setup_logger(
    name: str = "document_assistant",
    level: str = "INFO",
    log_file: Optional[str] = None,
) -> logging.Logger:
    """Configures and returns an application logger.

    Args:
        name: Name of the logger instance.
        level: Logging level ('DEBUG', 'INFO', 'WARNING', 'ERROR').
        log_file: Optional file path to output logs to.

    Returns:
        Configured logging.Logger instance.
    """
    logger = logging.getLogger(name)

    # Avoid duplicate handlers if setup_logger is called repeatedly
    if logger.handlers:
        return logger

    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(numeric_level)

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


# Default application-wide logger
logger = setup_logger()
