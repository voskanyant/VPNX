# VXcloud Servers And Ports

Этот файл нужен как быстрая инвентаризация.

## 1. Current main production server

Roles:

- WordPress
- Django web
- Telegram bot
- HAProxy / proxy
- Postgres
- MariaDB
- current VPN node

## 2. Ports that are intentionally important

Public:

- `80/tcp` - site HTTP
- `443/tcp` - site HTTPS
- `29940/tcp` - main VPN client port
- `2096/tcp` - subscription/config delivery port

Internal/localhost:

- `8088/tcp` - local app/proxy health path
- `5432/tcp` - Postgres
- `3306/tcp` - MariaDB
- `62789/tcp` - x-ui/api internal observed

Observed and must be reviewed:

- `24886/tcp` - public on current server, do not forget this exists

## 3. Expected env values

- `VPN_PUBLIC_HOST=vxcloud.ru`
- `VPN_PUBLIC_PORT=29940`
- `HAPROXY_FRONTEND_PORT=29940`

## 4. Node strategy

Current:

- main server acts as node-1

Target future architecture:

- separate control server
- separate node-1
- node-2
- node-3

## 5. Node checklist before enabling LB

- inbound listens on expected port
- firewall open for that port
- REALITY values match pool expectations
- manual app test passes:
  - Telegram
  - normal websites
  - config import
- backfill complete
- `lb_enabled = false` until all above is true
