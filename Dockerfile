FROM python:3.12-slim

# Variables de entorno de Python (optimización)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Directorio de trabajo
WORKDIR /app

# ⚠️ OPTIMIZACIÓN DE CACHÉ: Copiar requirements.txt primero
# Esto permite que Docker cachee esta capa y solo la reconstruya si cambian las dependencias
COPY requirements.txt /app/requirements.txt

# ⚠️ OPTIMIZACIÓN: Un solo bloque RUN para instalar dependencias del sistema, pip install, purgar gcc y limpiar apt
# Esto reduce el número de capas y el tamaño final de la imagen
#
# ⚠️ BAK-02 (docs/production/BACKUP_RESTORE_RUNBOOK.md): el repo default de
# Debian trixie (base de python:3.12-slim) solo empaqueta postgresql-client
# v17, pero docker-compose.yaml pin ea el servicio `db` a postgres:16-alpine.
# pg_restore v17 antepone `SET transaction_timeout = 0;` (GUC introducido en
# PG17) al restaurar, que un servidor v16 rechaza con "unrecognized
# configuration parameter" -- CUALQUIER restauracion real fallaba en este
# entorno antes de este fix (confirmado en vivo durante el drill de BAK-02).
# Se instala postgresql-client-16 desde el repo oficial PGDG para que el
# cliente coincida con la version del servidor.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
        netcat-openbsd \
        libffi-dev \
        libxml2-dev \
        libxslt1-dev \
        curl \
        ca-certificates \
        gnupg && \
    install -d /usr/share/postgresql-common/pgdg && \
    curl -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc --fail https://www.postgresql.org/media/keys/ACCC4CF8.asc && \
    echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] https://apt.postgresql.org/pub/repos/apt trixie-pgdg main" > /etc/apt/sources.list.d/pgdg.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends postgresql-client-16 && \
    pip install --no-cache-dir -r requirements.txt && \
    apt-get purge -y gcc gnupg && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

# Copiar el resto del código del proyecto
COPY . /app

# Crear directorios necesarios para evitar warnings de staticfiles
# .fastembed_cache: cache de modelos ONNX de embeddings (AI-VECTOR-04). Se crea
# con owner appuser aqui para que el named volume que se monta encima herede el
# owner correcto (UID 1000) en lugar de root.
RUN mkdir -p /app/static /app/media /app/staticfiles /app/.fastembed_cache

# ⚠️ Recolectar staticfiles durante el BUILD (defensa en profundidad para
# imagenes de produccion sin bind-mount, donde nadie corre collectstatic a
# mano). Seguro en build time: SECRET_KEY y DATABASES tienen defaults en
# settings.py, collectstatic no necesita conexion real a la BD.
# ⚠️ En DESARROLLO (bind-mount ./:/app) esto queda sobre-escrito por el
# volumen del host al arrancar el contenedor -- entrypoint.sh ya vuelve a
# correr collectstatic en cada arranque/restart para ese caso; sigue siendo
# necesario reiniciar el contenedor tras editar JS/CSS en dev.
RUN python manage.py collectstatic --noinput

# Copiar y hacer ejecutable el entrypoint
COPY entrypoint.sh entrypoint-celery.sh /app/
RUN chmod +x /app/entrypoint.sh /app/entrypoint-celery.sh

# DEVOPS-A1: no correr como root. UID/GID fijos (1000) para que archivos creados
# dentro del contenedor (staticfiles/media generados por collectstatic/uploads)
# queden con un propietario predecible.
# ⚠️ NO VERIFICADO EN RUNTIME (sin Docker funcional en este entorno de edicion) —
# probar `docker compose build && docker compose up` completo antes de desplegar:
# collectstatic, migraciones y (en dev) el bind mount `.:/app` deben seguir
# funcionando con este usuario. Ver PLAN_UNICO_CORRECCIONES.md Fase 8 / DEVOPS-A1.
RUN groupadd -g 1000 appuser && \
    useradd -u 1000 -g appuser -m -s /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

# Entrypoint por defecto
ENTRYPOINT ["/app/entrypoint.sh"]

# CMD limpio para el servidor web (puede ser sobrescrito por docker-compose)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
