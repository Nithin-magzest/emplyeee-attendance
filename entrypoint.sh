#!/bin/sh
set -e

# Run DB migrations and seed on every start
python - <<'EOF'
from app import init_db
init_db()
EOF

exec gunicorn \
  --bind 0.0.0.0:5000 \
  --workers 2 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile - \
  app:app
