"""
Logger Utility for FastAPI Applications
Configurable logging with console, file, and JSON formats
"""

import logging
import sys
import json
import os
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path


# ─── JSON Formatter ─────────────────────────────────────────────

class JSONFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.
    Outputs logs in JSON format for easy parsing by log aggregators.
    """
    
    def __init__(self, include_fields: Optional[list] = None):
        super().__init__()
        self.include_fields = include_fields or [
            'timestamp', 'level', 'name', 'module', 'function',
            'line', 'message', 'request_id', 'user_id', 'ip'
        ]
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'name': record.name,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'message': record.getMessage(),
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields from record
        for key, value in record.__dict__.items():
            if key not in ['args', 'asctime', 'created', 'exc_info', 'exc_text', 
                          'filename', 'funcName', 'levelname', 'levelno', 
                          'lineno', 'module', 'msecs', 'message', 'msg', 
                          'name', 'pathname', 'process', 'processName', 
                          'relativeCreated', 'stack_info', 'thread', 'threadName']:
                if key in self.include_fields:
                    log_data[key] = value
        
        return json.dumps(log_data)


class ColoredFormatter(logging.Formatter):
    """
    Colored console formatter for development.
    """
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m'       # Reset
    }
    
    def format(self, record: logging.LogRecord) -> str:
        # Get color for level
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']
        
        # Format message
        formatted = super().format(record)
        
        # Add color to level name
        levelname = f"{color}{record.levelname}{reset}"
        formatted = formatted.replace(record.levelname, levelname)
        
        return formatted


# ─── Logger Factory ─────────────────────────────────────────────

class LoggerFactory:
    """
    Factory for creating configured loggers.
    Supports console, file, and JSON logging.
    """
    
    def __init__(self):
        self._loggers = {}
        self._default_config = {
            'level': logging.INFO,
            'format': 'console',
            'log_dir': 'logs',
            'max_bytes': 10485760,  # 10MB
            'backup_count': 10,
            'when': 'midnight',
            'interval': 1,
        }
    
    def setup_logger(
        self,
        name: str,
        level: str = 'INFO',
        format_type: str = 'console',
        log_file: Optional[str] = None,
        log_dir: Optional[str] = None,
        max_bytes: int = 10485760,
        backup_count: int = 10,
        include_fields: Optional[list] = None
    ) -> logging.Logger:
        """
        Setup a logger with the specified configuration.
        
        Args:
            name: Logger name
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            format_type: 'console', 'json', 'colored'
            log_file: Log file name (optional)
            log_dir: Log directory (default: 'logs')
            max_bytes: Maximum file size for rotation
            backup_count: Number of backup files to keep
            include_fields: Fields to include in JSON output
        
        Returns:
            logging.Logger: Configured logger instance
        """
        # Return existing logger if already configured
        if name in self._loggers:
            return self._loggers[name]
        
        # Create logger
        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, level.upper(), logging.INFO))
        
        # Clear existing handlers
        logger.handlers.clear()
        
        # Setup console handler
        console_handler = self._create_console_handler(format_type)
        logger.addHandler(console_handler)
        
        # Setup file handler if log_file is specified
        if log_file:
            file_handler = self._create_file_handler(
                log_file,
                log_dir or self._default_config['log_dir'],
                format_type,
                max_bytes,
                backup_count,
                include_fields
            )
            if file_handler:
                logger.addHandler(file_handler)
        
        # Store logger
        self._loggers[name] = logger
        
        return logger
    
    def _create_console_handler(self, format_type: str) -> logging.Handler:
        """Create a console handler with the specified format."""
        handler = logging.StreamHandler(sys.stdout)
        
        if format_type == 'json':
            formatter = JSONFormatter()
        elif format_type == 'colored':
            formatter = ColoredFormatter(
                '%(asctime)s - %(levelname)s - %(name)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(name)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        
        handler.setFormatter(formatter)
        return handler
    
    def _create_file_handler(
        self,
        log_file: str,
        log_dir: str,
        format_type: str,
        max_bytes: int,
        backup_count: int,
        include_fields: Optional[list]
    ) -> Optional[logging.Handler]:
        """Create a file handler with rotation."""
        try:
            # Ensure log directory exists
            log_path = Path(log_dir)
            log_path.mkdir(parents=True, exist_ok=True)
            
            # Full log file path
            log_file_path = log_path / log_file
            
            # Create rotating file handler
            handler = RotatingFileHandler(
                log_file_path,
                maxBytes=max_bytes,
                backupCount=backup_count
            )
            
            # Set formatter
            if format_type == 'json':
                formatter = JSONFormatter(include_fields=include_fields)
            else:
                formatter = logging.Formatter(
                    '%(asctime)s - %(levelname)s - %(name)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                )
            
            handler.setFormatter(formatter)
            return handler
            
        except Exception as e:
            # Log to stderr if file handler fails
            print(f"Failed to create file handler: {e}", file=sys.stderr)
            return None


# ─── Default Logger Factory ─────────────────────────────────────

_logger_factory = LoggerFactory()


def setup_logger(
    name: str,
    level: str = 'INFO',
    format_type: str = 'console',
    log_file: Optional[str] = None,
    log_dir: Optional[str] = None,
    max_bytes: int = 10485760,
    backup_count: int = 10,
    include_fields: Optional[list] = None
) -> logging.Logger:
    """
    Setup a logger with the specified configuration.
    
    Args:
        name: Logger name
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: 'console', 'json', 'colored'
        log_file: Log file name (optional)
        log_dir: Log directory (default: 'logs')
        max_bytes: Maximum file size for rotation
        backup_count: Number of backup files to keep
        include_fields: Fields to include in JSON output
    
    Returns:
        logging.Logger: Configured logger instance
    
    Usage:
        # Basic logger
        logger = setup_logger('my_app')
        
        # JSON logger with file output
        logger = setup_logger(
            'my_app',
            format_type='json',
            log_file='app.log',
            log_dir='logs'
        )
        
        # Colored console logger
        logger = setup_logger('my_app', format_type='colored')
    """
    return _logger_factory.setup_logger(
        name=name,
        level=level,
        format_type=format_type,
        log_file=log_file,
        log_dir=log_dir,
        max_bytes=max_bytes,
        backup_count=backup_count,
        include_fields=include_fields
    )


# ─── FastAPI Logger Middleware ─────────────────────────────────

from fastapi import Request
import time


async def logger_middleware(request: Request, call_next):
    """
    FastAPI middleware for request logging.
    
    Usage:
        app.middleware("http")(logger_middleware)
    """
    logger = get_logger('request')
    
    start_time = time.time()
    
    # Get client IP
    client_ip = request.client.host if request.client else "unknown"
    forwarded = request.headers.get('X-Forwarded-For')
    if forwarded:
        client_ip = forwarded.split(',')[0].strip()
    
    # Log request
    logger.info(
        f"Request: {request.method} {request.url.path}",
        extra={
            'method': request.method,
            'path': request.url.path,
            'ip': client_ip,
            'user_agent': request.headers.get('User-Agent', ''),
            'request_id': request.headers.get('X-Request-ID', '')
        }
    )
    
    try:
        response = await call_next(request)
        
        duration = time.time() - start_time
        
        # Log response
        logger.info(
            f"Response: {request.method} {request.url.path} - {response.status_code} ({duration:.3f}s)",
            extra={
                'method': request.method,
                'path': request.url.path,
                'status': response.status_code,
                'duration': duration,
                'ip': client_ip,
                'request_id': request.headers.get('X-Request-ID', '')
            }
        )
        
        return response
        
    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            f"Error: {request.method} {request.url.path} - {str(e)} ({duration:.3f}s)",
            extra={
                'method': request.method,
                'path': request.url.path,
                'error': str(e),
                'duration': duration,
                'ip': client_ip,
                'request_id': request.headers.get('X-Request-ID', '')
            },
            exc_info=True
        )
        raise


# ─── Logging Context Managers ──────────────────────────────────

import contextlib


@contextlib.contextmanager
def log_context(logger: logging.Logger, operation: str, **kwargs):
    """
    Context manager for logging operation start and finish.
    
    Usage:
        with log_context(logger, "database_query", table="users"):
            result = db.query("SELECT * FROM users")
    """
    logger.info(f"Starting {operation}", extra=kwargs)
    start_time = time.time()
    
    try:
        yield
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Failed {operation} after {duration:.3f}s: {str(e)}", extra=kwargs, exc_info=True)
        raise
    else:
        duration = time.time() - start_time
        logger.info(f"Completed {operation} in {duration:.3f}s", extra=kwargs)


# ─── Get Logger ─────────────────────────────────────────────────

def get_logger(name: str = 'app') -> logging.Logger:
    """Get a logger by name."""
    return logging.getLogger(name)


# ─── Exports ──────────────────────────────────────────────────

__all__ = [
    'setup_logger',
    'get_logger',
    'logger_middleware',
    'log_context',
    'JSONFormatter',
    'ColoredFormatter',
    'LoggerFactory',
    'logging',
]

# ─── Default Logger Configuration ──────────────────────────────

# Setup default logger for the application
_default_logger = None


def get_default_logger() -> logging.Logger:
    """Get the default application logger."""
    global _default_logger
    if _default_logger is None:
        log_level = os.getenv('LOG_LEVEL', 'INFO')
        log_format = os.getenv('LOG_FORMAT', 'console')
        log_file = os.getenv('LOG_FILE')
        log_dir = os.getenv('LOG_DIR', 'logs')
        
        _default_logger = setup_logger(
            name='app',
            level=log_level,
            format_type=log_format,
            log_file=log_file,
            log_dir=log_dir
        )
    return _default_logger
