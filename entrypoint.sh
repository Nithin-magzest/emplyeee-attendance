#!/bin/sh
set -e

# ── SSL cert (auto-generate if missing) ─────────────────────────────────────
if [ ! -f cert.pem ] || [ ! -f key.pem ]; then
    echo "Generating self-signed SSL certificate..."
    python generate_cert.py
fi

# ── Start gunicorn via wsgi.py (handles DB init + email worker on startup) ───
GUNICORN_ARGS="
  --bind 0.0.0.0:5000
  --workers 2
  --threads 2
  --timeout 120
  --keep-alive 5
  --access-logfile -
  --error-logfile -
  --log-level info
"

if [ -f cert.pem ] && [ -f key.pem ]; then
    echo "Starting on https://0.0.0.0:5000"
    exec gunicorn $GUNICORN_ARGS \
        --certfile cert.pem \
        --keyfile  key.pem \
        wsgi:application
else
    echo "No cert found — starting on http://0.0.0.0:5000"
    exec gunicorn $GUNICORN_ARGS wsgi:application
fi
