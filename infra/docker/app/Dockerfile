FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Sistema básico (psycopg deps, curl para health/wait scripts, postgresql-client para wait_for_db)
# ⚠️ WeasyPrint eliminado - Dependencias del sistema reducidas
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libpq-dev \
    postgresql-client \
    netcat-openbsd \
    libffi-dev \
    libxml2-dev \
    libxslt1-dev \
    python3-pip \
    python3-cffi \
    && rm -rf /var/lib/apt/lists/*

# Instala deps del proyecto
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Agregar gunicorn y whitenoise para producción
RUN pip install --no-cache-dir gunicorn whitenoise

# Copia el proyecto
COPY . /app

# WhiteNoise + staticfiles: preparar STATIC_ROOT
ENV DJANGO_SETTINGS_MODULE=config.settings
RUN python manage.py collectstatic --noinput || true

# check producción (no falla si hay warnings)
RUN python manage.py check --deploy || true

# Gunicorn config
COPY infra/docker/app/gunicorn.conf.py /app/gunicorn.conf.py

# Entrypoint: migraciones + migrate_schemas + run gunicorn
COPY infra/scripts/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]
