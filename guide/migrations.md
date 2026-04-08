# Миграция продакшена (no-downtime)

Этот документ описывает безопасный порядок миграции БД и включения feature flags для VXcloud.

## Предусловия

- Применен свежий код приложения (web + bot), совместимый со схемой БД.
- В `/srv/apps/vxcloud/app/.env` заполнены рабочие значения:
  - `POSTGRES_PASSWORD`
  - `MAGIC_LINK_SHARED_SECRET`
  - `ACCOUNT_MAGIC_URL_TEMPLATE`
  - для card-платежей: `PAYMENT_PROVIDER=yookassa`
  - `PAYMENT_YOOKASSA_SHOP_ID`
  - `PAYMENT_YOOKASSA_API_KEY`
  - `ENABLE_CARD_PAYMENTS=1`
  - `VPN_PUBLIC_PORT=29940`
  - `HAPROXY_FRONTEND_PORT=29940`
- Контейнеры `db`, `web`, `bot` запущены.

## Порядок SQL-миграций

Применяем только additive-миграции, в следующем порядке:

1. `sql/migrations/20260328_add_client_code_to_users.sql`
2. `sql/migrations/20260328_add_xui_sub_id_to_subscriptions.sql`
3. `sql/migrations/20260328_create_payment_events.sql`
4. `sql/migrations/20260328_expand_orders_for_card_payments.sql`
5. `sql/migrations/20260328_create_support_tables.sql`
6. `sql/migrations/20260328_create_web_login_tokens.sql`
7. `sql/migrations/20260328_add_orders_notified_at.sql`

После применения SQL выполняем healthcheck приложения.

## Порядок включения feature flags

Включаем флаги только после успешных SQL-миграций и healthcheck:

1. Проверить, что webhook endpoint для карты уже доступен и верификация подписи настроена.
2. Включить `ENABLE_CARD_PAYMENTS=1`.
3. Перезапустить только `web` и `bot` (без остановки `db`).
4. Повторить healthcheck.

Примечание: magic link авторизация не имеет отдельного boolean-флага и активируется конфигом (`MAGIC_LINK_SHARED_SECRET` и `ACCOUNT_MAGIC_URL_TEMPLATE`).

## Автоматический сценарий

Используйте:

```bash
./scripts/ops/migrate.sh
```

Скрипт делает:

1. Применение SQL-миграций по порядку.
2. Healthcheck сайта.
3. Включение feature flags в `.env`.
4. Rolling restart `web`/`bot`.
5. Финальный healthcheck.

### Полезные параметры

- Без включения флагов:

```bash
./scripts/ops/migrate.sh --skip-flags
```

- С указанием host для healthcheck:

```bash
HEALTHCHECK_HOST=vxcloud.ru ./scripts/ops/migrate.sh
```
