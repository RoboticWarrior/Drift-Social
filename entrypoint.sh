#!/bin/sh
# Container entrypoint: prepare the storage volume, seed the demo feed once,
# then hand the process over to gunicorn.
set -eu

APP_DIR=$(cd "$(dirname "$0")" && pwd)
cd "$APP_DIR/backend"

STORAGE_DIR="${STORAGE_DIR:-$APP_DIR}"
export STORAGE_DIR
mkdir -p "$STORAGE_DIR/data" "$STORAGE_DIR/uploads"

if [ "${SEED_DEMO:-1}" = "1" ] && [ ! -f "$STORAGE_DIR/data/.seeded" ]; then
  echo "seeding demo feed into $STORAGE_DIR"
  if python seed.py; then
    : # seed.py skips itself when posts already exist
  else
    echo "seed failed — starting with an empty feed" >&2
  fi
  touch "$STORAGE_DIR/data/.seeded"
fi

exec gunicorn \
  --workers "${WEB_CONCURRENCY:-1}" \
  --threads "${WEB_THREADS:-4}" \
  --timeout "${WEB_TIMEOUT:-60}" \
  --bind "0.0.0.0:${PORT:-8080}" \
  --access-logfile - \
  --error-logfile - \
  app:app
