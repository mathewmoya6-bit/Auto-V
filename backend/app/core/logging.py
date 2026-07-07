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
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields from record
        if hasattr(record, "extra"):
            log_data.update(record.extra)
        
        # Add request_id if present
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        
        # Add user_id if present
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
        # Add color coding for different levels
        colors = {
            "DEBUG": "\033[36m",     # Cyan
            "INFO": "\033[32m",      # Green
            "WARNING": "\033[33m",   # Yellow
            "ERROR": "\033[31m",     # Red
            "CRITICAL": "\033[35m",  # Magenta
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
        
        # Add context to log record
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
    # Get log level from settings
    log_level = LOG_LEVELS.get(
        settings.LOG_LEVEL.upper(),
        logging.INFO
    )
    
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Determine format based on environment
    if settings.is_production:
        formatter = JSONFormatter()
    else:
        formatter = TextFormatter()
    
    # ─── Console Handler ─────────────────────────────────────────────
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # ─── File Handler (Rotating) ────────────────────────────────────
    if settings.is_production:
        file_handler = RotatingFileHandler(
            log_dir / "autov.log",
            maxBytes=10_485_760,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(JSONFormatter())
        root_logger.addHandler(file_handler)
        
        # ─── Error File Handler ──────────────────────────────────────
        error_handler = RotatingFileHandler(
            log_dir / "autov_error.log",
            maxBytes=5_242_880,  # 5MB
            backupCount=3
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(JSONFormatter())
        root_logger.addHandler(error_handler)
    
    # ─── Silence noisy loggers ──────────────────────────────────────
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    
    # Log startup message
    logger = get_logger(__name__)
    logger.info(
        f"🚀 Logging initialized",
        extra={
            "environment": settings.ENV,
            "log_level": settings.LOG_LEVEL,
            "format": "json" if settings.is_production else "text"
        }
    )


# ─── Request Logging Middleware ────────────────────────────────────
class RequestLogger:
    """Logging middleware for FastAPI requests."""
    
    def __init__(self, app):
        self.app = app
        self.logger = get_logger("request")
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Generate request ID
        import uuid
        request_id = str(uuid.uuid4())
        
        # Create context logger for this request
        context_logger = self.logger.with_context(request_id=request_id)
        
        # Log request
        method = scope.get("method", "UNKNOWN")
        path = scope.get("path", "/")
        client = scope.get("client", ("unknown", 0))
        
        context_logger.info(
            f"➡️ {method} {path}",
            extra={
                "client_ip": client[0] if client else "unknown",
                "client_port": client[1] if client else 0,
                "method": method,
                "path": path,
            }
        )
        
        # Store context in scope for later use
        scope["request_id"] = request_id
        
        # Process request
        await self.app(scope, receive, send)


# ─── Module-Level Logger ────────────────────────────────────────────
logger = get_logger(__name__)


# ─── Auto-setup on import ──────────────────────────────────────────
setup_logging()
