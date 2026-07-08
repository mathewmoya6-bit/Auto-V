# app/main.py
# =============================================================================
# AUTO-V API - Application Entrypoint
# =============================================================================
"""
Render (and any uvicorn/gunicorn host) points at this file as:
    uvicorn app.main:app --host 0.0.0.0 --port $PORT
"""
import logging

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.project_name,
    version="1.0.0",
    debug=settings.debug,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    logger.warning(f"Validation error on {request.url.path}: {exc.errors()}")
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.get("/", tags=["health"])
async def root():
    return {"status": "ok", "service": settings.project_name}


@app.get("/health", tags=["health"])
async def health():
    return {"status": "healthy"}


# Import here (not at module top) so any import-time error in the router
# tree surfaces with a clear traceback pointing at this exact line,
# rather than being buried under FastAPI's own import chain.
from app.api.v1.api import api_router  # noqa: E402

app.include_router(api_router, prefix=settings.api_v1_prefix)

logger.info(f"{settings.project_name} started in {settings.environment} mode")
