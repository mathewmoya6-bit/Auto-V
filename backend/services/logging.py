# logging.py - AUTO-V Logging Module
import os
import sys
import json
import logging
import logging.config
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import traceback

from config import config

# ─── Log Levels ──────────────────────────────────────────────────

LOG_LEVELS = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL
}

# ─── Custom Formatters ──────────────────────────────────────────

class JsonFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.
    """
    
    def __init__(self, include_fields: list = None, exclude_fields: list = None):
        super().__init__()
        self.include_fields = include_fields
        self.exclude_fields = exclude_fields or []
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'message': record.getMessage(),
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        # Add extra fields
        if hasattr(record, 'extra'):
            log_data['extra'] = record.extra
        
        # Filter fields
        if self.include_fields:
            log_data = {k: v for k, v in log_data.items() if k in self.include_fields}
        
        for field in self.exclude_fields:
            log_data.pop(field, None)
        
        return json.dumps(log_data, default=str)

class ColoredFormatter(logging.Formatter):
    """
    Colored formatter for console output.
    """
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors."""
        color = self.COLORS.get(record.levelname, '')
        reset = self.COLORS['RESET']
        
        # Add color to level name
        record.levelname = f"{color}{record.levelname}{reset}"
        
        # Get formatted message
        formatted = super().format(record)
        
        return formatted

# ─── Log Filters ─────────────────────────────────────────────────

class RequestIdFilter(logging.Filter):
    """Add request ID to log records."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add request ID to record."""
        try:
            from flask import g
            if hasattr(g, 'request_id'):
                record.request_id = g.request_id
            else:
                record.request_id = '-'
        except:
            record.request_id = '-'
        return True

class UserIdFilter(logging.Filter):
    """Add user ID to log records."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add user ID to record."""
        try:
            from flask import g
            if hasattr(g, 'user_id'):
                record.user_id = g.user_id
            else:
                record.user_id = '-'
        except:
            record.user_id = '-'
        return True

class SensitiveDataFilter(logging.Filter):
    """Filter sensitive data from logs."""
    
    SENSITIVE_FIELDS = [
        'password', 'token', 'api_key', 'secret', 'auth',
        'authorization', 'credit_card', 'card_number', 'cvv',
        'mpesa', 'pin', 'passkey'
    ]
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Filter sensitive data from record."""
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            for field in self.SENSITIVE_FIELDS:
                if field in record.msg.lower():
                    record.msg = self._redact_sensitive(record.msg)
        return True
    
    def _redact_sensitive(self, message: str) -> str:
        """Redact sensitive data from message."""
        for field in self.SENSITIVE_FIELDS:
            pattern = f'({field}[=:][^\\s,]+)'
            import re
            message = re.sub(pattern, f'{field}=[REDACTED]', message, flags=re.IGNORECASE)
        return message

# ─── Logger Factory ─────────────────────────────────────────────

def setup_logging(
    log_level: str = None,
    log_file: str = None,
    log_format: str = None,
    json_logging: bool = False
) -> None:
    """
    Setup logging configuration.
    
    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Log file path
        log_format: Log format (text or json)
        json_logging: Enable JSON logging
    """
    # Get settings from config or environment
    log_level = log_level or config.LOG_LEVEL
    log_file = log_file or config.LOG_FILE
    log_format = log_format or config.LOG_FORMAT
    json_logging = json_logging or (log_format.lower() == 'json')
    
    # Convert to logging level
    level = LOG_LEVELS.get(log_level.upper(), logging.INFO)
    
    # Create logs directory
    if log_file:
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
    
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Create formatters
    if json_logging:
        console_formatter = JsonFormatter()
        file_formatter = JsonFormatter()
    else:
        console_formatter = ColoredFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    # ─── Console Handler ──────────────────────────────────────────
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # ─── File Handler ─────────────────────────────────────────────
    if log_file:
        try:
            # Use RotatingFileHandler for production
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=10485760,  # 10MB
                backupCount=10
            )
            file_handler.setLevel(level)
            file_handler.setFormatter(file_formatter)
            root_logger.addHandler(file_handler)
        except Exception as e:
            print(f"Warning: Could not set up file logging: {e}")
    
    # ─── Add Filters ──────────────────────────────────────────────
    root_logger.addFilter(RequestIdFilter())
    root_logger.addFilter(UserIdFilter())
    root_logger.addFilter(SensitiveDataFilter())
    
    # ─── Third-party Loggers ─────────────────────────────────────
    # Set third-party loggers to WARNING to reduce noise
    for logger_name in ['urllib3', 'requests', 'supabase', 'asyncio']:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.WARNING)
    
    # ─── Log startup ──────────────────────────────────────────────
    logger = logging.getLogger(__name__)
    logger.info(f"✅ Logging initialized (level={log_level}, json={json_logging})")

# ─── Logger Class ────────────────────────────────────────────────

class Logger:
    """
    Custom logger class with additional functionality.
    """
    
    def __init__(self, name: str = __name__):
        self.logger = logging.getLogger(name)
    
    def debug(self, message: str, extra: Dict[str, Any] = None):
        """Log debug message."""
        self.logger.debug(message, extra={'extra': extra} if extra else {})
    
    def info(self, message: str, extra: Dict[str, Any] = None):
        """Log info message."""
        self.logger.info(message, extra={'extra': extra} if extra else {})
    
    def warning(self, message: str, extra: Dict[str, Any] = None):
        """Log warning message."""
        self.logger.warning(message, extra={'extra': extra} if extra else {})
    
    def error(self, message: str, extra: Dict[str, Any] = None):
        """Log error message."""
        self.logger.error(message, extra={'extra': extra} if extra else {})
    
    def critical(self, message: str, extra: Dict[str, Any] = None):
        """Log critical message."""
        self.logger.critical(message, extra={'extra': extra} if extra else {})
    
    def exception(self, message: str, extra: Dict[str, Any] = None):
        """Log exception message with traceback."""
        self.logger.exception(message, extra={'extra': extra} if extra else {})
    
    def log_api_call(self, endpoint: str, method: str, status_code: int, duration: float):
        """Log API call details."""
        self.info(
            f"API: {method} {endpoint} → {status_code} ({duration:.3f}s)",
            extra={
                'endpoint': endpoint,
                'method': method,
                'status_code': status_code,
                'duration': duration
            }
        )
    
    def log_payment(self, payment_id: str, status: str, amount: float, reference: str = None):
        """Log payment details."""
        self.info(
            f"Payment: {payment_id} → {status} (KES {amount})",
            extra={
                'payment_id': payment_id,
                'status': status,
                'amount': amount,
                'reference': reference
            }
        )
    
    def log_auth(self, user_id: str, action: str, success: bool):
        """Log authentication details."""
        self.info(
            f"Auth: {user_id} → {action} ({'success' if success else 'failed'})",
            extra={
                'user_id': user_id,
                'action': action,
                'success': success
            }
        )
    
    def log_validation(self, vin: str, valid: bool, errors: list = None):
        """Log validation details."""
        self.info(
            f"Validation: {vin} → {'valid' if valid else 'invalid'}",
            extra={
                'vin': vin,
                'valid': valid,
                'errors': errors
            }
        )

# ─── Context Managers ────────────────────────────────────────────

class LogContext:
    """
    Context manager for logging with context.
    
    Usage:
        with LogContext('operation_name', extra={'user_id': user_id}):
            # Do something
            pass
    """
    
    def __init__(self, operation: str, extra: Dict[str, Any] = None):
        self.operation = operation
        self.extra = extra or {}
        self.logger = logging.getLogger(__name__)
    
    def __enter__(self):
        self.start_time = datetime.now()
        self.logger.info(f"Starting: {self.operation}", extra={'extra': self.extra})
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.now() - self.start_time).total_seconds()
        if exc_type:
            self.logger.error(
                f"Failed: {self.operation} ({duration:.3f}s)",
                extra={'extra': {**self.extra, 'error': str(exc_val)}}
            )
        else:
            self.logger.info(
                f"Completed: {self.operation} ({duration:.3f}s)",
                extra={'extra': self.extra}
            )

class Timer:
    """
    Timer context manager for logging execution time.
    
    Usage:
        with Timer('database_query'):
            # Run query
            pass
    """
    
    def __init__(self, operation: str, threshold: float = 1.0):
        self.operation = operation
        self.threshold = threshold
        self.logger = logging.getLogger(__name__)
    
    def __enter__(self):
        self.start_time = datetime.now()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.now() - self.start_time).total_seconds()
        if duration > self.threshold:
            self.logger.warning(
                f"Slow operation: {self.operation} took {duration:.3f}s"
            )
        else:
            self.logger.debug(
                f"Operation: {self.operation} completed in {duration:.3f}s"
            )

# ─── Helper Functions ────────────────────────────────────────────

def get_logger(name: str = None) -> Logger:
    """
    Get a logger instance.
    
    Args:
        name: Logger name (default: __name__)
        
    Returns:
        Logger instance
    """
    if name is None:
        import inspect
        frame = inspect.currentframe().f_back
        name = frame.f_globals.get('__name__', __name__)
    
    return Logger(name)

def log_exception(logger: logging.Logger, e: Exception, message: str = None):
    """
    Log an exception with full details.
    
    Args:
        logger: Logger instance
        e: Exception instance
        message: Optional message
    """
    error_msg = message or f"Exception occurred: {str(e)}"
    logger.error(f"{error_msg}\n{traceback.format_exc()}")

# ─── Setup Default Logger ────────────────────────────────────────

# Setup logging when module is imported
setup_logging()

# Create default logger
default_logger = get_logger(__name__)

# ─── Quick Test ──────────────────────────────────────────────────

if __name__ == "__main__":
    print("🔍 Testing Logging Module...")
    
    # Test setup
    setup_logging(log_level='DEBUG')
    
    # Get logger
    logger = get_logger(__name__)
    
    # Test logging
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
    
    # Test with extra data
    logger.info("User action", extra={'user_id': 'user123', 'action': 'login'})
    
    # Test API logging
    logger.log_api_call('/api/test', 'GET', 200, 0.123)
    
    # Test payment logging
    logger.log_payment('PAY-123', 'completed', 100.50, 'REF-456')
    
    # Test context manager
    with LogContext('test_operation', {'test': 'value'}):
        pass
    
    # Test timer
    import time
    with Timer('test_timer'):
        time.sleep(0.1)
    
    print("✅ Logging module test complete")
