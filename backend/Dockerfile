# ============================================================
# AUTO-V BACKEND DOCKERFILE
# Production Ready - FastAPI
# ============================================================

FROM python:3.11-slim

# ─── Build Arguments ──────────────────────────────────────────
ARG APP_VERSION=2.0.0
ARG WORKDIR=/app

# ─── Environment Variables ──────────────────────────────────
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    APP_VERSION=${APP_VERSION} \
    POETRY_VERSION=1.7.1

# ─── Set Working Directory ──────────────────────────────────
WORKDIR ${WORKDIR}

# ─── Install System Dependencies ────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# ─── Install Python Dependencies ────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ─── Copy Application Code ──────────────────────────────────
COPY . .

# ─── Create Directories ─────────────────────────────────────
RUN mkdir -p /app/uploads /app/logs /app/reports /app/models

# ─── Create Non-Root User ───────────────────────────────────
RUN addgroup --system --gid 1001 autov && \
    adduser --system --uid 1001 --gid 1001 autov && \
    chown -R autov:autov /app

USER autov

# ─── Health Check ────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# ─── Expose Port ─────────────────────────────────────────────
EXPOSE 8000

# ─── Run Application ─────────────────────────────────────────
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
