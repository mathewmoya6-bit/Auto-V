# utils/logger.py

import logging
import sys
from logging.handlers import RotatingFileHandler
import os

def setup_logger(name: str, log_file: str = None) -> logging.Logger:
    """Setup logger with console and file handlers."""
    logger = logging.getLogger(name)
    
    if logger.handlers:
        return logger
    
    logger.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        try:
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=10485760,  # 10MB
                backupCount=10
            )
            file_handler.setLevel(logging.INFO)
            file_format = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(file_format)
            logger.addHandler(file_handler)
        except Exception as e:
            logger.warning(f"Could not set up file logger: {e}")
    
    return logger
