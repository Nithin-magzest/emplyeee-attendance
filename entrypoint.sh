#!/bin/sh
set -e

# ── SSL cert (auto-generate if missing) ─────────────────────────────────────
if [ ! -f cert.pem ] || [ ! -f key.pem ]; then
    echo "Generating self-signed SSL certificate..."
    python generate_cert.py
fi

# ── Start gunicorn via wsgi.py (handles DB init + email worker on startup) ───
# Workers/threads are env-configurable (defaults unchanged) so a memory-
# constrained deployment (e.g. compose.lowmem.yaml) can cut worker count
# without needing its own image build. Each worker duplicates the app's
# loaded libraries (face_recognition/OpenCV/dlib are the big ones) in RAM,
# so worker count is the single biggest lever on this container's footprint.
GUNICORN_ARGS="
  --bind 0.0.0.0:5000
  --workers ${GUNICORN_WORKERS:-2}
  --worker-class gthread
  --threads ${GUNICORN_THREADS:-2}
  --timeout 120
  --keep-alive 5
  --access-logfile -
  --error-logfile -
  --log-level info
"
# --worker-class gthread: gunicorn's default "sync" worker class silently
# IGNORES --threads (only gthread honors it), so before this, each worker
# handled exactly one request at a time no matter what GUNICORN_THREADS was
# set to — a CPU-bound face-recognition check-in tied up the entire worker,
# and every other request routed to it queued behind it. gthread lets other
# threads on the same worker keep serving requests (DB I/O, static-ish
# routes) while one thread is busy, without changing any app code.

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
