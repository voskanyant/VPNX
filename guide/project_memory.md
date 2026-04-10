# VXcloud Project Memory

Этот файл нужен как короткая рабочая память по проекту.
Его надо обновлять после заметных production-изменений.

## 1. Что это за проект

VXcloud состоит из 3 основных частей:

- WordPress: публичный сайт и контент
- Django: кабинет, backoffice `/ops/`, payment/webhook/backend routes
- Telegram bot: продажи, renew, reminders, support, выдача конфигов

## 2. Текущая production topology

Сейчас основной production server совмещает:

- site
- bot
- backoffice
- payments/webhooks
- HAProxy
- databases
- и одновременно текущий VPN node

То есть сейчас main server = control plane + node-1.

Это удобно на старте, но это всё ещё single point of failure для control plane.

Current intended node management model:

- current main server should exist in `/ops/ -> VPN ноды` as `node-1`
- this lets one physical server stay both control plane and one LB-manageable VPN node
- if routing problem happens only on the VPN side of the main server, disable `lb_enabled` for `node-1`
- site, bot, backoffice and payments can still keep working on that server while new VPN traffic goes to other nodes

Важно:
- это помогает только когда сам сервер жив
- это не спасает от полного падения main server

## 3. Источник правды

Что считается source of truth:

- subscriptions / expiry / active state: app database
- 3x-ui: downstream execution layer, не главный источник правды
- bot content overrides: `/ops/bot/content/`
- публичный контент сайта: WordPress

Важно:
- ручные изменения expiry только в 3x-ui не отражаются автоматически в site/bot
- admin expiry нужно менять через `/ops/`, чтобы обновлялись и DB, и 3x-ui

## 4. Production domains and public endpoints

- public site: `https://vxcloud.ru`
- account frontend: `https://vxcloud.ru/account/`
- ops/backoffice: `https://vxcloud.ru/ops/`
- Django admin: `https://vxcloud.ru/django-admin/`

VPN/public ports:

- main VPN public port: `29940`
- subscription port: `2096`
- legacy 3x-ui/admin-like port observed on server: `24886` and must be reviewed carefully before launch exposure

## 5. Payments

Current intended payment provider:

- YooKassa

Expected env:

- `PAYMENT_PROVIDER=yookassa`
- `ENABLE_CARD_PAYMENTS=1`
- `PAYMENT_YOOKASSA_SHOP_ID` filled
- `PAYMENT_YOOKASSA_API_KEY` filled

Card checkout behavior:

- bot card flow does not require separate manual site signup
- Telegram magic-link creates or reuses a site account automatically
- abandoned card checkout should expire after 30 minutes

## 6. Bot behavior assumptions

Current intended UX:

- card is primary payment path
- Stars remain optional, not primary
- `Мой доступ` should show concrete configs, not abstract access only
- `Скопировать ссылку` in bot must copy `vless://...`, not subscription URL
- config expiry reminders must mention which config expired or is expiring

## 7. HAProxy and nodes

Current HAProxy behavior:

- balances new TCP connections
- uses structural node health, not app-specific health
- does not detect "Telegram broken but node otherwise alive"
- does not migrate already established VPN sessions

Safe node-add rule:

1. add node
2. keep `lb_enabled = false`
3. wait for health
4. complete backfill
5. verify manually
6. only then enable LB

Backoffice support now exists for node CRUD:

- `/ops/ -> VPN ноды` shows inventory
- add node
- edit node
- disable or enable LB participation
- delete node

Recommended meanings of key flags:

- `is_active = true`: node is a live cluster member
- `lb_enabled = true`: HAProxy may send new VPN connections there
- `needs_backfill = true`: do not put into LB yet; sync and manual checks are still pending

Safe node-remove rule:

1. disable `lb_enabled`
2. reload HAProxy
3. wait
4. then stop/remove node

Recommended initial values:

- current main server as `node-1`:
  - `is_active = true`
  - `lb_enabled = true` only if you want it serving LB traffic
  - `needs_backfill = false`
- brand new extra node:
  - `is_active = true`
  - `lb_enabled = false`
  - `needs_backfill = true` until sync and manual validation are complete

## 8. Current launch-critical risks

- control plane still lives on one server
- Telegram-only node failures are not automatically detected by HAProxy
- standby main server recovery is not yet a fully tested process

## 9. What not to do

- do not treat 3x-ui manual edits as primary admin workflow
- do not add a node directly into LB before backfill and manual checks
- do not leave Directus configured if it is no longer used
- do not expose unexpected admin ports publicly without clear reason

## 10. Key guide files

- [go_live_checklist.md](./go_live_checklist.md)
- [emergency_runbook.md](./emergency_runbook.md)
- [servers_and_ports.md](./servers_and_ports.md)
- [known_issues.md](./known_issues.md)
