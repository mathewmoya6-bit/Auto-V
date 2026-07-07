# app/core/logging.py
# =============================================================================
# AUTO-V API - Logging Configuration
# =============================================================================

import logging
import sys
import json
from datetime import datetime
from typing import Optional, Dict, Any
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.core.config import settings


# ─── Log Levels ─────────────────────────────────────────────────────

LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


# ─── JSON Formatter ─────────────────────────────────────────────────

class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        if hasattr(record, "extra"):
            log_data.update(record.extra)
        
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        
        return json.dumps(log_data)


# ─── Text Formatter ─────────────────────────────────────────────────

class TextFormatter(logging.Formatter):
    """Human-readable text formatter for development."""
    
    def __init__(self):
        super().__init__(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with color for development."""
        colors = {
            "DEBUG": "\033[36m",
            "INFO": "\033[32m",
            "WARNING": "\033[33m",
            "ERROR": "\033[31m",
            "CRITICAL": "\033[35m",
        }
        reset = "\033[0m"
        
        if record.levelname in colors:
            record.levelname = f"{colors[record.levelname]}{record.levelname}{reset}"
        
        return super().format(record)


# ─── Contextual Logger ─────────────────────────────────────────────

class ContextLogger:
    """Logger with context support (request_id, user_id, etc.)."""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self._context: Dict[str, Any] = {}
    
    def with_context(self, **kwargs) -> "ContextLogger":
        """Add context to the logger."""
        self._context.update(kwargs)
        return self
    
    def _log(self, level: int, msg: str, *args, **kwargs):
        """Internal log method with context."""
        extra = kwargs.pop("extra", {})
        extra.update(self._context)
        
        for key, value in self._context.items():
            if hasattr(self.logger, key):
                setattr(self.logger, key, value)
        
        self.logger.log(level, msg, *args, extra=extra, **kwargs)
    
    def debug(self, msg: str, *args, **kwargs):
        self._log(logging.DEBUG, msg, *args, **kwargs)
    
    def info(self, msg: str, *args, **kwargs):
        self._log(logging.INFO, msg, *args, **kwargs)
    
    def warning(self, msg: str, *args, **kwargs):
        self._log(logging.WARNING, msg, *args, **kwargs)
    
    def error(self, msg: str, *args, **kwargs):
        self._log(logging.ERROR, msg, *args, **kwargs)
    
    def critical(self, msg: str, *args, **kwargs):
        self._log(logging.CRITICAL, msg, *args, **kwargs)
    
    def exception(self, msg: str, *args, **kwargs):
        self._log(logging.ERROR, msg, *args, exc_info=True, **kwargs)


# ─── Logger Factory ─────────────────────────────────────────────────

def get_logger(name: str) -> ContextLogger:
    """
    Get a contextual logger instance.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        ContextLogger instance
    """
    return ContextLogger(name)


# ─── Setup Logging ──────────────────────────────────────────────────

def setup_logging() -> None:
    """
    Setup logging configuration based on settings.
    """
    log_level = LOG_LEVELS.get(
        settings.LOG_LEVEL.upper(),
        logging.INFO
    )
    
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    if settings.is_production:
        formatter = JSONFormatter()
    else:
        formatter = TextFormatter()
    
    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File Handler (Production only)
    if settings.is_production:
        file_handler = RotatingFileHandler(
            log_dir / "autov.log",
            maxBytes=10_485_760,
            backupCount=5
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(JSONFormatter())
        root_logger.addHandler(file_handler)
        
        error_handler = RotatingFileHandler(
            log_dir / "autov_error.log",
            maxBytes=5_242_880,
            backupCount=3
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(JSONFormatter())
        root_logger.addHandler(error_handler)
    
    # Silence noisy loggers
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


# ─── Module Logger ──────────────────────────────────────────────────

logger = get_logger(__name__)


__all__ = [
    "get_logger",
    "setup_logging",
    "ContextLogger",
]
