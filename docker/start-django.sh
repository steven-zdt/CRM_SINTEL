#!/bin/bash
# docker/start-django.sh -- arranca Django dentro del contenedor unico de
# desarrollo. Reemplaza la logica que antes vivia en entrypoint.sh (ahora
# ese archivo solo arranca supervisord) -- migraciones/collectstatic/tenant
# publico se ejecutan aqui, una sola vez, antes de `runserver`.
set -e

export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-config.settings}"

/app/docker/wait-for.sh postgres localhost "${DATABASE_PORT:-5432}"
/app/docker/wait-for.sh tcp localhost 6379

cd /app

echo "django: aplicando migraciones del esquema public..."
python manage.py migrate_schemas --shared

echo "django: aplicando migraciones a todos los tenants..."
python manage.py migrate_schemas --tenant

PUBLIC_PRIMARY_DOMAIN="${TENANT_DOMAIN_BASE:-sintel.net.co}"
export PUBLIC_TENANT_DOMAINS="${PUBLIC_TENANT_DOMAINS:-${PUBLIC_PRIMARY_DOMAIN},localhost,127.0.0.1}"

echo "django: garantizando tenant publico y dominios (${PUBLIC_TENANT_DOMAINS})..."
python manage.py create_public_tenant --domain "${PUBLIC_PRIMARY_DOMAIN}"
python manage.py ensure_public_domains --primary "${PUBLIC_PRIMARY_DOMAIN}"

echo "django: recolectando archivos estaticos..."
python manage.py collectstatic --noinput --clear 2>&1 | tail -5 || echo "django: collectstatic con advertencias (no fatal)"

exec python manage.py runserver 0.0.0.0:8000
