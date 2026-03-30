#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/srv/apps/vxcloud/app"
cd "$APP_DIR"

wait_for_http() {
  local url="$1"
  local max_attempts="${2:-45}"
  local sleep_seconds="${3:-2}"
  local code=""
  local attempt=1

  while [[ "$attempt" -le "$max_attempts" ]]; do
    code="$(curl -sS -o /dev/null -w "%{http_code}" "$url" || true)"
    if [[ -n "$code" && "$code" != "000" && "$code" -lt 500 ]]; then
      echo "web healthcheck OK (HTTP=$code)"
      return 0
    fi
    sleep "$sleep_seconds"
    attempt=$((attempt + 1))
  done

  echo "ERROR: web healthcheck failed, HTTP=${code:-000}"
  return 1
}

echo "[1/8] Fetch latest..."
git fetch origin main

LOCAL="$(git rev-parse HEAD)"
REMOTE="$(git rev-parse origin/main)"
echo "LOCAL=$LOCAL"
echo "REMOTE=$REMOTE"

echo "[2/8] Auto-stash local/untracked changes (if any)..."
git stash push -u -m "auto-stash-before-deploy-$(date +%F_%H%M%S)" >/dev/null || true

echo "[3/8] Fast-forward pull..."
git pull --ff-only origin main

echo "[4/8] Rebuild/start containers..."
docker compose --env-file .env up -d --build db web
docker compose --env-file .env --profile bot up -d --build bot

echo "[5/8] Apply Django migrations + static..."
docker compose --env-file .env exec -T web python /app/web/manage.py migrate --noinput
docker compose --env-file .env exec -T web python /app/web/manage.py collectstatic --noinput

echo "[6/8] Check migration drift (makemigrations --check)..."
if ! docker compose --env-file .env exec -T web python /app/web/manage.py makemigrations --check --dry-run; then
  echo "ERROR: model changes detected without migration files."
  echo "Create and commit migrations first (manage.py makemigrations), then redeploy."
  exit 1
fi

echo "[7/8] Health checks..."
wait_for_http "http://127.0.0.1:8088/"
docker compose --env-file .env ps

echo "[8/8] Done."
echo "If needed, stashes are here:"
git stash list | head -n 3 || true
