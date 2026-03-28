#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/srv/apps/vxcloud/app"
cd "$APP_DIR"

docker compose --env-file .env exec -T db psql -U vxcloud -d vxcloud -c "
SELECT id, telegram_id, client_code, username, first_name, created_at
FROM users
ORDER BY id
LIMIT 20;
"
