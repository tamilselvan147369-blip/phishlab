"""Production Gunicorn configuration for PhishLab on Render."""

import os

# Port binding: Render dynamically assigns PORT (defaults to 10000 on Render)
port = os.getenv("PORT", "10000")
bind = f"0.0.0.0:{port}"

# Worker processes:
# Single worker with multi-threading is optimal for Server-Sent Events (SSE)
# and in-memory event queues on Render Starter / Standard instances.
# When REDIS_URL is configured, workers can be increased via WEB_CONCURRENCY.
workers = int(os.getenv("WEB_CONCURRENCY", "1"))
worker_class = "gthread"
threads = int(os.getenv("GUNICORN_THREADS", "8"))

# Timeouts: Allow long-lived SSE connections and file analysis without premature disconnect
timeout = int(os.getenv("GUNICORN_TIMEOUT", "120"))
keepalive = 5

# Logging: Stream stdout / stderr directly to Render log viewer
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("LOG_LEVEL", "info")
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" (%(D)s µs)'

# Process naming
proc_name = "phishlab-gunicorn"

# Preload app and recycle workers periodically to prevent memory bloat
preload_app = True
max_requests = int(os.getenv("GUNICORN_MAX_REQUESTS", "1000"))
max_requests_jitter = 50

# Graceful restart
graceful_timeout = 30
