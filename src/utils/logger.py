import logging
import sys
from pathlib import Path

def setup_logger(name: str = "TelegramFleet", level: int = logging.INFO) -> logging.Logger:
    """
    Configures a cross-platform logger working cleanly on Windows, Termux/Android, and GitHub Actions.
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(level)
    
    # Standard stream handler with UTF-8 support
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger
