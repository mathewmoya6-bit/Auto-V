# ============================================================
# gunicorn.conf.py - Gunicorn Configuration
# Production WSGI Server Settings
# ============================================================

import os
import multiprocessing

# ─── Server Socket ─────────────────────────────────────────────
bind = f"0.0.0.0:{os.getenv('PORT', 8000)}"
backlog = 2048

# ─── Worker Processes ──────────────────────────────────────────
workers = int(os.getenv('WORKERS', multiprocessing.cpu_count() * 2 + 1))
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
timeout = 60
graceful_timeout = 30
keepalive = 5

# ─── Threads ────────────────────────────────────────────────────
threads = int(os.getenv('THREADS', 2))

# ─── Logging ───────────────────────────────────────────────────
accesslog = "-"
errorlog = "-"
loglevel = os.getenv('LOG_LEVEL', 'info').lower()
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# ─── Preload Application ──────────────────────────────────────
preload_app = True

# ─── Worker Temp Directory ────────────────────────────────────
worker_tmp_dir = "/dev/shm"

# ─── SSL (Optional) ────────────────────────────────────────────
if os.getenv('SSL_ENABLED', 'false').lower() == 'true':
    ssl_keyfile = os.getenv('SSL_KEY_PATH')
    ssl_certfile = os.getenv('SSL_CERT_PATH')

# ─── Startup Info ──────────────────────────────────────────────
def on_starting(server):
    print("=" * 60)
    print("🚀 AUTO-V API Server Starting (Gunicorn)")
    print("=" * 60)
    print(f"📡 Workers: {workers}")
    print(f"📡 Threads: {threads}")
    print(f"📡 Port: {os.getenv('PORT', 8000)}")
    print(f"📡 Environment: {os.getenv('ENV', 'production')}")
    print("=" * 60)


def on_exit(server):
    print("\n🛑 AUTO-V API Server Shutting Down")
