#!/bin/sh
set -e

# ── DB initialisation ────────────────────────────────────────────────────────
python - <<'EOF'
from app import init_master_db, init_db
init_master_db()
init_db()
EOF

# ── SSL cert (auto-generate if missing) ─────────────────────────────────────
if [ ! -f cert.pem ] || [ ! -f key.pem ]; then
    echo "Generating self-signed SSL certificate..."
    python generate_cert.py
fi

# ── Start gunicorn (with SSL if certs present) ───────────────────────────────
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
    echo "🔒  Starting on https://0.0.0.0:5000"
    exec gunicorn $GUNICORN_ARGS \
        --certfile cert.pem \
        --keyfile  key.pem \
        app:app
else
    echo "⚠   No cert found — starting on http://0.0.0.0:5000"
    echo "    Run: python generate_cert.py  to enable HTTPS / fingerprint"
    exec gunicorn $GUNICORN_ARGS app:app
fi
