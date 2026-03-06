FROM python:3.12-slim

# Instalar dependencias del sistema para compilar psycopg y herramientas de conexión
# ⚠️ WeasyPrint eliminado - Dependencias del sistema reducidas
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    postgresql-client \
    netcat-openbsd \
    libffi-dev \
    libxml2-dev \
    libxslt1-dev \
    python3-pip \
    python3-cffi \
    && rm -rf /var/lib/apt/lists/*

# Variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Directorio de trabajo
WORKDIR /app

# Instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el proyecto
COPY . .

# Crear directorios necesarios para evitar warnings de staticfiles
# ⚠️ CRÍTICO: Estos directorios deben existir antes de que Django arranque
RUN mkdir -p /app/static /app/media /app/staticfiles

# Copiar y hacer ejecutable los entrypoints
COPY entrypoint.sh /entrypoint.sh
COPY entrypoint-celery.sh /entrypoint-celery.sh
RUN chmod +x /entrypoint.sh /entrypoint-celery.sh

# Entrypoint por defecto (para web)
ENTRYPOINT ["/entrypoint.sh"]
