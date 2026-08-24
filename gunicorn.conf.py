"""Gunicorn production configuration."""

import os


bind = "0.0.0.0:5001"
workers = int(os.getenv("WEB_CONCURRENCY", "2"))
threads = int(os.getenv("GUNICORN_THREADS", "2"))
worker_class = "gthread"
timeout = int(os.getenv("GUNICORN_TIMEOUT", "180"))
graceful_timeout = 30
keepalive = 5
accesslog = "-"
errorlog = "-"
capture_output = True

# Gunicorn 25.1+ enables a control socket under $HOME by default. The container
# root filesystem is intentionally read-only and this service does not use
# gunicornc, so disable the socket instead of adding another writable path.
control_socket_disable = True
