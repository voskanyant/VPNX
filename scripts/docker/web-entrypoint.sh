#!/usr/bin/env sh
set -eu

cd /app/web
mkdir -p /app/web/staticfiles
python manage.py migrate --noinput
python manage.py collectstatic --noinput
exec gunicorn vxcloud_site.wsgi:application --bind 0.0.0.0:8088 --workers 3 --timeout 60
