#!/usr/bin/env bash
# update.sh — pull the latest code and rebuild the container in place.
# The SQLite database and uploads live in ./data, outside the image, so they
# survive this.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_DIR"

echo "==> pulling"
git pull --ff-only

echo "==> rebuilding"
docker compose up -d --build

echo "==> pruning old images"
docker image prune -f

echo "==> health"
for attempt in $(seq 1 24); do
  if curl -fsS --max-time 5 http://127.0.0.1:8080/api/health >/dev/null 2>&1; then
    echo "    app is healthy"
    exit 0
  fi
  sleep 5
done

echo "app did not become healthy; check: docker compose logs --tail=100" >&2
exit 1
