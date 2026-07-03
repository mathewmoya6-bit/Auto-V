# app/core/logging.py
# Inferred from setup_logging() usage in main.py: returns a logger
# that main.py calls logger.info/warning/error on, and log_requests
# middleware passes an `extra={...}` dict — using a plain formatter
# here rather than structured JSON logging to keep this dependency-free;
# swap in python-json-logger or structlog if you want structured logs
# on Render.

import logging
import sys
from app.core.config import settings


def setup_logging() -> logging.Logger:
    level = getattr(logging, (settings.LOG_LEVEL or "info").upper(), logging.INFO)

    root_logger = logging.getLogger("app")
    root_logger.setLevel(level)

    # Avoid duplicate handlers if setup_logging() is somehow called
    # more than once (e.g. under a reload)
    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)

    # Quiet down noisy third-party loggers unless we're in debug mode
    if not settings.DEBUG:
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    return root_logger
