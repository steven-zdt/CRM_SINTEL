"""
Configuración de Gunicorn para producción.

Referencia: https://docs.gunicorn.org/en/stable/settings.html
"""
import multiprocessing
import os

# Bind address
bind = os.getenv("GUNICORN_BIND", "0.0.0.0:8000")

# Workers: (2 x CPU cores) + 1
workers = int(os.getenv("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))

# Worker class: sync (default) o gevent/uvicorn según necesidad
worker_class = os.getenv("GUNICORN_WORKER_CLASS", "sync")

# Timeout: tiempo máximo para procesar una request
timeout = int(os.getenv("GUNICORN_TIMEOUT", 60))

# Keepalive: tiempo de espera para conexiones keep-alive
keepalive = int(os.getenv("GUNICORN_KEEPALIVE", 5))

# Logging
accesslog = "-"  # stdout
errorlog = "-"   # stderr
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")
# [WARNING] OBSERVABILIDAD: Access log sin query string (omite %(q)s para evitar exponer parámetros)
# %(U)s = path sin query string
access_logformat = '%(h)s %(t)s "%(m)s %(U)s HTTP/%(H)s" %(s)s %(B)s'

# Process naming
proc_name = "sintel_gunicorn"

# Preload app: carga la app antes de forking workers (mejor rendimiento)
preload_app = True

# Max requests: reinicia worker después de N requests (previene memory leaks)
max_requests = int(os.getenv("GUNICORN_MAX_REQUESTS", 1000))
max_requests_jitter = int(os.getenv("GUNICORN_MAX_REQUESTS_JITTER", 50))

# Graceful timeout: tiempo para terminar workers gracefulmente
graceful_timeout = int(os.getenv("GUNICORN_GRACEFUL_TIMEOUT", 30))
