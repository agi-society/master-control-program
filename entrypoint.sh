#!/bin/sh
set -e
python manage.py check
python manage.py migrate --noinput
python manage.py collectstatic --noinput
if [ ! -f /app/staticfiles/work/app.css ] || [ ! -f /app/staticfiles/work/app.js ]; then
  echo "ERROR: required work UI static assets were not collected" >&2
  exit 1
fi
if [ "${SEED_DATA:-1}" = "1" ]; then
  python manage.py seed_data
fi
exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 2 --timeout 60
