# VXcloud Known Issues And Rules

Этот файл нужен не для паники, а чтобы не наступать на уже известные грабли.

## 1. Known behavior

### 3x-ui expiry edits

Если поменять expiry только в 3x-ui:

- site and bot не обновятся автоматически
- правильный admin path: менять expiry через `/ops/`

### Node can be "alive but bad for Telegram"

Node может:

- нормально открывать сайты
- но не иметь нормальной reachability до Telegram

В этом случае:

- HAProxy может считать его healthy
- такой node надо вручную убирать из LB

### Main server is still control-plane SPOF

Если умирает main server, падают:

- bot
- site
- ops
- payments/webhooks
- HAProxy on main server

## 2. Practical rules

- new configs must use public port `29940`
- bot copy action must copy `vless://...`
- card checkout from bot must open checkout directly, not just account dashboard
- stale card pending older than 30 minutes should not be treated as active checkout

## 3. Operational rules

- before launch, keep Directus disabled unless intentionally used
- before enabling a new node in LB, manually test Telegram through it
- if one node behaves strangely, remove it from LB first and investigate second
- do not do incident response by editing random production rows without understanding source of truth

## 4. When returning to this project later

First re-read:

- [project_memory.md](./project_memory.md)
- [go_live_checklist.md](./go_live_checklist.md)
- [emergency_runbook.md](./emergency_runbook.md)
