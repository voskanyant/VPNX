# VXcloud Runbook: Add New VPN Node

Этот runbook фиксирует реальный рабочий порядок добавления новой VPN-ноды в кластер VXcloud.

Цель:

- поднять новую 3x-ui/Xray ноду
- добавить её в `/ops/`
- дождаться sync
- включить в HAProxy pool без поломки существующих клиентов

Исходные допущения:

- main server уже работает
- production path уже такой:
  - `client -> HAProxy:29940 -> Xray backend:29941`
- 3x-ui inbound на всех нодах использует `VLESS + TCP + REALITY`
- `Proxy Protocol = on`
- `.env` на main server содержит `HAPROXY_BACKEND_SEND_PROXY=1`
- HAProxy уже контейнеризирован и использует sticky routing:
  - `balance leastconn`
  - `stick-table`
  - `stick on src`

## 1. Что подготовить заранее

Нужно знать:

- IP main server
- IP новой ноды
- доступ `root` или `sudo` к новой ноде
- доступ в `/ops/`
- доступ в panel 3x-ui на main node

В примерах ниже:

- main server: `82.21.117.154`
- new node: `91.99.99.51`
- backend VPN port: `29941`
- new node 3x-ui panel port: `2053`

## 2. Подготовить новую ноду

Подключиться к новой ноде:

```bash
ssh root@91.99.99.51
```

Проверить базовое состояние:

```bash
hostnamectl
ip -4 addr show
curl -4 ifconfig.me
ufw status verbose || true
```

Обновить систему и поставить базовые пакеты:

```bash
apt update
apt -y upgrade
apt -y install curl wget unzip socat ca-certificates gnupg lsb-release jq ufw
reboot
```

После reboot подключиться снова:

```bash
ssh root@91.99.99.51
```

## 3. Включить firewall на новой ноде

Открыть только SSH и будущий backend port:

```bash
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp
ufw allow 29941/tcp
ufw enable
ufw status verbose
```

Ожидается:

- `22/tcp` открыт
- `29941/tcp` открыт
- всё остальное inbound закрыто

## 4. Поставить 3x-ui

Запустить install:

```bash
bash <(curl -Ls https://raw.githubusercontent.com/mhsanaei/3x-ui/master/install.sh)
```

Во время install использовать:

- panel port: `2053`
- random web base path
- random username/password
- не использовать случайный panel port

## 5. Сделать self-signed cert для panel

Если install требует custom certificate:

```bash
mkdir -p /etc/x-ui/ssl

openssl req -x509 -nodes -newkey rsa:2048 \
  -keyout /etc/x-ui/ssl/panel.key \
  -out /etc/x-ui/ssl/panel.crt \
  -days 825 \
  -subj "/CN=91.99.99.51"
```

Потом снова пройти install и указать:

- cert path: `/etc/x-ui/ssl/panel.crt`
- key path: `/etc/x-ui/ssl/panel.key`

## 6. Проверить, что panel и x-ui живы

На новой ноде:

```bash
systemctl status x-ui --no-pager
ss -ltnp | grep 2053 || true
ss -ltnp | grep 29941 || true
```

Ожидается:

- x-ui running
- panel слушает `2053`
- VPN inbound ещё может не слушать `29941`, если inbound не импортирован

## 7. Ограничить panel firewall-ом

Сразу ограничить panel доступом только с main server:

```bash
ufw allow from 82.21.117.154 to any port 2053 proto tcp
ufw status verbose
```

Если нужно временно открыть panel для ручной настройки из домашнего IP, сделать это осознанно и потом убрать.

Временное открытие для всех:

```bash
ufw allow 2053/tcp
ufw status verbose
```

Потом обязательно вернуть обратно.

## 8. Импортировать production inbound с main node

Лучший способ:

- открыть 3x-ui panel main node
- экспортировать working production inbound
- открыть 3x-ui panel new node
- импортировать этот inbound

Что должно получиться:

- inbound type: `VLESS + TCP + REALITY`
- inbound port: `29941`
- `Proxy Protocol = on`
- те же REALITY-compatible значения, что и на main node

После импорта проверить:

```bash
ss -ltnp | grep 29941 || true
```

Ожидается:

- `xray` слушает `29941`

## 9. Включить access log на новой ноде

Это обязательно для отладки распределения между нодами.

В 3x-ui -> `Xray Configs` задать:

- `Access log path`: `/usr/local/x-ui/access.log`
- `Error log path`: `/usr/local/x-ui/error.log`

После сохранения перезапустить x-ui/Xray.

Проверить:

```bash
ls -l /usr/local/x-ui/access.log /usr/local/x-ui/error.log
```

## 10. Проверить reachability новой ноды с main server

На main server:

```bash
nc -vz 91.99.99.51 29941
```

Ожидается:

- `succeeded`

## 11. Добавить новую ноду в `/ops/`

Открыть `/ops/ -> VPN ноды` и создать запись.

Типовые значения:

- `name`: `node-2-hetzner`
- `region`: `Germany`
- `xui_base_url`: `https://91.99.99.51:2053/<panel-path>`
- `xui_username`: `<panel-username>`
- `xui_password`: `<panel-password>`
- `xui_inbound_id`: `1`
- `backend_host`: `91.99.99.51`
- `backend_port`: `29941`
- `backend_weight`: `100`
- `is_active`: `true`
- `lb_enabled`: `false`
- `needs_backfill`: `true`

Сохранять именно в таком состоянии:

- нода активна
- в LB ещё не включена
- backfill ещё нужен

## 12. Проверить dry-run HAProxy до admission в LB

На main server:

```bash
cd /srv/apps/vxcloud/app
docker compose --env-file .env exec -T web python /app/scripts/ops/render_haproxy_cfg.py --env-file /app/.env --dry-run
```

Ожидается:

- новая нода ещё не появилась в backend pool
- в pool пока только старые `lb_enabled=true` и healthy nodes

## 13. Проверить Node Sync

В `/ops/ -> Node sync` дождаться:

- `sync = ok`
- `desired` и `observed` совпадают

Это доказывает:

- main server умеет логиниться в panel новой ноды
- читает inbound
- синхронизирует клиентов

## 14. Снять `needs_backfill` и включить ноду в LB

После того как sync и ручные проверки пройдены:

- снять `needs_backfill`
- включить `lb_enabled`
- сохранить

После этого на main server:

```bash
cd /srv/apps/vxcloud/app
docker compose --env-file .env exec -T web python /app/scripts/ops/render_haproxy_cfg.py --env-file /app/.env --dry-run
docker compose --env-file .env logs --tail=100 haproxy
```

Ожидается:

- `# Nodes in pool: 2`
- в backend есть строки для `node-1-main` и новой ноды
- в логах HAProxy нет ошибок reload

## 15. Применить обновлённый production deploy

На main server:

```bash
cd /srv/apps/vxcloud/app
git pull origin main
chmod +x scripts/ops/deploy-auto.sh
./scripts/ops/deploy-auto.sh
```

После deploy:

```bash
docker compose --env-file .env ps
docker compose --env-file .env exec -T web python /app/scripts/ops/render_haproxy_cfg.py --env-file /app/.env --dry-run
```

Ожидается в backend:

```haproxy
balance leastconn
stick-table type ip size 200k expire 20m
stick on src
```

## 16. Проверить реальное распределение клиентов

Открыть два окна логов.

На main server:

```bash
sudo tail -f /usr/local/x-ui/access.log | grep "inbound-29941"
```

На node-2:

```bash
tail -f /usr/local/x-ui/access.log | grep "inbound-29941"
```

Потом:

1. отключить VPN на тестовых устройствах
2. подождать около минуты
3. подключить устройство 1
4. через 20-30 секунд подключить устройство 2

Правильное поведение после sticky-fix:

- один и тот же клиент не должен одновременно появляться на двух нодах
- один клиент может оказаться на `node-1`
- другой клиент может оказаться на `node-2`

## 17. Как интерпретировать traffic counters в panel

Разный traffic на main node и node-2 — это нормально.

Почему:

- у каждой ноды свой локальный inbound usage counter
- sticky routing закрепляет клиента за одной нодой
- поэтому usage естественно различается между панелями

Плохой признак:

- один и тот же клиент одновременно растёт по traffic на обеих нодах без осознанного failover

## 18. Финально закрыть panel node-2 обратно

Если panel временно открывали наружу:

```bash
ufw delete allow 2053/tcp
ufw status verbose
```

Ожидается:

- `2053/tcp` доступен только с `82.21.117.154`
- `22/tcp` открыт
- `29941/tcp` открыт

## 19. Быстрый rollback

Если новая нода ведёт себя плохо:

1. в `/ops/ -> VPN ноды` выключить у неё `lb_enabled`
2. сохранить
3. на main server проверить dry-run:

```bash
cd /srv/apps/vxcloud/app
docker compose --env-file .env exec -T web python /app/scripts/ops/render_haproxy_cfg.py --env-file /app/.env --dry-run
docker compose --env-file .env logs --tail=100 haproxy
```

Ожидается:

- новая нода исчезла из HAProxy backend pool
- старые клиенты на других нодах продолжают жить
- новые подключения в проблемную ноду больше не идут

## 20. Итоговая рабочая схема

После успешного добавления новой ноды production модель такая:

- public frontend: `29940`
- HAProxy: Docker, `network_mode: host`
- backend Xray nodes:
  - `node-1-main -> 127.0.0.1:29941`
  - `node-2-hetzner -> 91.99.99.51:29941`
- routing policy:
  - `leastconn` for first placement
  - temporary stickiness by source IP
  - `expire 20m`

Это даёт:

- новый клиент попадает на менее загруженную ноду
- дальше не размазывается между нодами
- после периода неактивности может быть перераспределён заново
