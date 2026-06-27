# app/core/logging.py
import logging
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
import os

from app.core.config import settings

class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""
    
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        if hasattr(record, "extra"):
            log_data.update(record.extra)
            
        return json.dumps(log_data)

def setup_logging():
    """Configure logging for the application"""
    
    # Create logs directory if it doesn't exist
    log_dir = Path(settings.LOG_DIR)
    log_dir.mkdir(exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    
    # Clear any existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    if settings.LOG_FORMAT == "json":
        console_handler.setFormatter(JSONFormatter())
    else:
        console_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
    root_logger.addHandler(console_handler)
    
    # File handler
    log_file = log_dir / "app.log"
    file_handler = logging.FileHandler(log_file)
    if settings.LOG_FORMAT == "json":
        file_handler.setFormatter(JSONFormatter())
    else:
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
    root_logger.addHandler(file_handler)
    
    # Create error log file
    error_log_file = log_dir / "error.log"
    error_handler = logging.FileHandler(error_log_file)
    error_handler.setLevel(logging.ERROR)
    if settings.LOG_FORMAT == "json":
        error_handler.setFormatter(JSONFormatter())
    else:
        error_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
    root_logger.addHandler(error_handler)
    
    # Set third-party loggers to WARNING
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    
    return root_logger

def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name"""
    return logging.getLogger(name)

class LoggerContext:
    """Context manager for adding extra data to logs"""
    
    def __init__(self, logger: logging.Logger, extra: Dict[str, Any]):
        self.logger = logger
        self.extra = extra
        self.old_extra = getattr(logger, "extra", {})
    
    def __enter__(self):
        self.logger.extra = {**self.old_extra, **self.extra}
        return self.logger
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logger.extra = self.old_extra
