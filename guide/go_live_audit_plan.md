# VXcloud Go-Live Audit Plan

This checklist is for the final pre-launch pass on the current architecture:

- main server hosts Django, bot, HAProxy, and local `x-ui`/Xray
- optional extra VPN nodes may be added later through `/ops`
- `3x-ui` has a known limitation: the last client in an inbound cannot be deleted, so VXcloud keeps a disabled reserved placeholder

## 1. Production Env

Goal: confirm the app cannot boot in an unsafe mode.

Check on the server:

```bash
cd /srv/apps/vxcloud/app
grep -E '^(DJANGO_SECRET_KEY|DJANGO_DEBUG|DJANGO_ALLOWED_HOSTS|DJANGO_CSRF_TRUSTED_ORIGINS|DATABASE_URL|VPN_PUBLIC_HOST|VPN_PUBLIC_PORT|XUI_BASE_URL|XUI_USERNAME|XUI_INBOUND_ID|PAYMENT_PROVIDER|ENABLE_CARD_PAYMENTS)=' .env
```

Expected:

- `DJANGO_SECRET_KEY` is set
- `DJANGO_DEBUG=0`
- `DJANGO_ALLOWED_HOSTS` is not `*`
- `DJANGO_CSRF_TRUSTED_ORIGINS` matches the public domain
- `DATABASE_URL` points to PostgreSQL in production
- payment secrets are present if card payments are enabled

## 2. Deploy + Tests

Goal: confirm the deployed revision is healthy and test suite is green.

Local/workspace:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

Server:

```bash
cd /srv/apps/vxcloud/app
./scripts/ops/deploy-auto.sh
docker compose --env-file .env ps
```

Expected:

- test suite passes
- deploy finishes without drift or healthcheck failures
- `web`, `bot`, `haproxy`, `proxy`, `db`, `wpdb`, `wordpress` are up

## 3. Subscription Lifecycle

Goal: verify the full customer path, not just create.

Test manually:

1. Create a trial or paid subscription.
2. Confirm it appears in `/ops -> Подписки`.
3. Confirm the same client appears in `3x-ui`.
4. Expire or revoke it.
5. Delete it from VXcloud.
6. Confirm it disappears from VXcloud DB.
7. Confirm it disappears from `3x-ui`, or the final remaining slot becomes `_vxcloud_reserved`.

Verification commands:

```bash
cd /srv/apps/vxcloud/app
docker compose --env-file .env exec -T web python /app/web/manage.py shell -c "from cabinet.models import BotSubscription; print(list(BotSubscription.objects.values('id','display_name','client_email','xui_sub_id','is_active').order_by('id')))"
docker compose --env-file .env exec -T web python - <<'PY'
import asyncio, os
from src.xui_client import XUIClient
async def main():
    xui = XUIClient(os.environ['XUI_BASE_URL'], os.environ['XUI_USERNAME'], os.environ['XUI_PASSWORD'])
    await xui.start()
    try:
        for c in await xui.list_clients(int(os.environ.get('XUI_INBOUND_ID','1'))):
            print({"uuid": c.client_uuid, "email": c.email, "enabled": c.enabled, "sub_id": c.sub_id, "comment": c.comment})
    finally:
        await xui.close()
asyncio.run(main())
PY
```

Expected:

- active subscriptions in DB match active managed clients in `3x-ui`
- no stale customer ghosts remain after delete
- `_vxcloud_reserved` may exist and is acceptable

## 4. Payment Flows

Goal: confirm no silent payment/provisioning drift.

Check:

1. Create a test card payment or provider-side payment.
2. Confirm one order row is created.
3. Confirm duplicate webhook delivery does not create duplicate subscriptions.
4. Confirm paid order leads to exactly one provisioned config.

Useful checks:

```bash
cd /srv/apps/vxcloud/app
docker compose --env-file .env exec -T web python /app/web/manage.py shell -c "from cabinet.models import BotOrder, PaymentEvent; print('orders', BotOrder.objects.count()); print('events', PaymentEvent.objects.count())"
```

## 5. HAProxy + Node Routing

Goal: confirm public VPN traffic hits the intended backend.

Render config:

```bash
cd /srv/apps/vxcloud/app
docker compose --env-file .env exec -T web python /app/scripts/ops/render_haproxy_cfg.py --env-file /app/.env --dry-run
```

Expected:

- single-node mode: one backend only
- multi-node mode: correct backend list, weights, sticky config

Live traffic check:

```bash
sudo tail -n 50 /usr/local/x-ui/access.log
```

Expected:

- traffic reaches the intended inbound
- in multi-node mode, a single client should not spray across nodes unexpectedly

## 6. Performance / Network Sanity

Goal: separate stack issues from upstream routing issues.

Check:

```bash
uptime
vmstat 1 5
docker stats --no-stream
ss -s
```

And destination tests:

```bash
curl -4 -L --max-time 20 -o /dev/null -w 'youtube time=%{time_total} speed=%{speed_download}\n' https://www.youtube.com
curl -4 -L --max-time 20 -o /dev/null -w 'cloudflare time=%{time_total} speed=%{speed_download}\n' https://www.cloudflare.com
```

If a specific app is slow, inspect real destination IPs from `access.log` first, then run `mtr` to those exact IPs.

## 7. Backup / DR

Goal: verify you can recover the main server, not just back it up.

Create backup:

```bash
cd /srv/apps/vxcloud/app
sudo ./scripts/ops/backup-main-server.sh
```

Verify latest backup:

```bash
sudo ls -lah /srv/backups/vxcloud/$(find /srv/backups/vxcloud -mindepth 1 -maxdepth 1 -type d | sort | tail -n1)
```

Expected artifacts:

- `vxcloud.env`
- `git-revision.txt`
- `postgres-vxcloud.dump`
- `mariadb-wordpress.sql`
- `wordpress-data.tar.gz`
- `x-ui-etc.tar.gz`
- `x-ui-usr-local.tar.gz`
- `SHA256SUMS`

Also confirm one copy exists off-server.

## 8. Go / No-Go

Go only if all of the below are true:

- production env is explicitly set and safe
- full test suite passes
- deploy is healthy
- subscription create / expire / delete path is consistent in both DB and `3x-ui`
- payment flow provisions exactly once
- current traffic path is stable
- latest DR backup exists and is stored off the server

No-go if any of the below are true:

- `DJANGO_DEBUG=1` in production
- `ALLOWED_HOSTS=*` in production
- subscription deletion leaves live managed clients behind
- payment flow can duplicate subscriptions
- no recent restorable backup exists
