# ============================================================
# Dockerfile - AUTO-V API with Gunicorn
# ============================================================

FROM python:3.11-slim

# ─── Environment ──────────────────────────────────────────────
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# ─── Dependencies ─────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ─── Application ──────────────────────────────────────────────
COPY . .

# ─── User ──────────────────────────────────────────────────────
RUN addgroup --system --gid 1001 autov && \
    adduser --system --uid 1001 --gid 1001 autov && \
    chown -R autov:autov /app

USER autov

# ─── Port ──────────────────────────────────────────────────────
EXPOSE 8000

# ─── Health Check ─────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# ─── Start ─────────────────────────────────────────────────────
CMD ["gunicorn", "-c", "gunicorn.conf.py", "wsgi:app"]
