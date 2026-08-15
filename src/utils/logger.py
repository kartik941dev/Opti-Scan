"""
Centralized logging utility for OptiScan with color formatting and file output support.
"""

import logging
import sys
from pathlib import Path
from typing import Optional


class OptiScanFormatter(logging.Formatter):
    """Custom color-coded console formatter for readable CLI output."""

    GREY = "\x1b[38;20m"
    BLUE = "\x1b[34;20m"
    GREEN = "\x1b[32;20m"
    YELLOW = "\x1b[33;20m"
    RED = "\x1b[31;20m"
    BOLD_RED = "\x1b[31;1m"
    RESET = "\x1b[0m"

    FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s"

    LEVEL_COLORS = {
        logging.DEBUG: GREY,
        logging.INFO: GREEN,
        logging.WARNING: YELLOW,
        logging.ERROR: RED,
        logging.CRITICAL: BOLD_RED,
    }

    def format(self, record: logging.LogRecord) -> str:
        color = self.LEVEL_COLORS.get(record.levelno, self.RESET)
        formatter = logging.Formatter(
            f"{color}%(asctime)s | %(levelname)-8s{self.RESET} | %(name)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        return formatter.format(record)


def get_logger(
    name: str = "optiscan",
    level: int | str = logging.INFO,
    log_file: Optional[Path | str] = None,
) -> logging.Logger:
    """
    Get or create a configured logger instance.

    Args:
        name: The name of the logger module.
        level: Minimum log level (e.g. logging.DEBUG, logging.INFO).
        log_file: Optional file path to persist log output.

    Returns:
        Configured logging.Logger instance.
    """
    logger = logging.getLogger(name)

    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(level)

    # Avoid duplicate handlers if logger was already created
    if not logger.handlers:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(OptiScanFormatter())
        logger.addHandler(console_handler)

        if log_file:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(str(log_path), encoding="utf-8")
            file_handler.setLevel(level)
            file_formatter = logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)

    return logger
