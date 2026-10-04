"""Gunicorn settings for the production API container."""

from __future__ import annotations

import os

bind = "0.0.0.0:8000"
workers = int(os.environ.get("WEB_CONCURRENCY", "3"))
timeout = 120

worker_tmp_dir = "/dev/shm"

accesslog = "-"
errorlog = "-"
