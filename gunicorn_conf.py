"""Gunicorn configuration file."""

import logging
import os

from app.core.config import settings
from app.core.logger import setup_logging

# Gunicorn config variables
loglevel = os.getenv("LOG_LEVEL").lower()
workers = settings.workers
bind = os.getenv("GUNICORN_BIND", "0.0.0.0:8000")
worker_class = "uvicorn.workers.UvicornWorker"


def on_starting(_server):
    """
    Hook executed once by the master process before forking workers.
    """
    setup_logging()
    logger = logging.getLogger("gunicorn.error")
    logger.info(f"🚀 Gunicorn master process started. Spawning {workers} workers.")