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
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
        postgresql-client \
        netcat-openbsd \
        libffi-dev \
        libxml2-dev \
        libxslt1-dev \
        curl && \
    pip install --no-cache-dir -r requirements.txt && \
    apt-get purge -y gcc && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

# Copiar el resto del código del proyecto
COPY . /app

# Crear directorios necesarios para evitar warnings de staticfiles
RUN mkdir -p /app/static /app/media /app/staticfiles

# Copiar y hacer ejecutable el entrypoint
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Entrypoint por defecto
ENTRYPOINT ["/app/entrypoint.sh"]

# CMD limpio para el servidor web (puede ser sobrescrito por docker-compose)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
