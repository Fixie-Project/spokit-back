#!/bin/sh
set -o errexit
set -o nounset

python manage.py migrate
if [ "${RUN_COLLECTSTATIC-1}" = "1" ]; then
  python manage.py collectstatic --noinput
fi

gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000}
