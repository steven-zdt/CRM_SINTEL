# Docker Compose - Entorno Producción

Este directorio contiene la configuración Docker Compose para un entorno "prod-like" del proyecto SINTEL.

## Estructura

- `docker-compose.yml`: Stack completo de producción (app, db, redis, celery, beat, opensearch, traefik)
- `docker-compose.test.yml`: Override para ejecutar tests
- `.env.example`: Variables de entorno de ejemplo

## Servicios

### app
- **Imagen**: Construida desde `infra/docker/app/Dockerfile`
- **Puerto**: 8000
- **WSGI Server**: Gunicorn
- **Staticfiles**: WhiteNoise
- **Healthcheck**: `/health`

### db
- **Imagen**: `postgres:16`
- **Puerto**: 5432
- **Healthcheck**: `pg_isready`

### redis
- **Imagen**: `redis:7-alpine`
- **Puerto**: 6379
- **Healthcheck**: `redis-cli ping`

### celery
- **Comando**: `celery -A config worker -l INFO`
- **Concurrencia**: 2 workers

### beat
- **Comando**: `celery -A config beat -l INFO`

### opensearch
- **Imagen**: `opensearchproject/opensearch:latest`
- **Modo**: single-node (desarrollo)
- **Puertos**: 9200 (HTTP), 9600 (monitoring)
- **Memoria**: 512MB heap

### traefik (opcional)
- **Imagen**: `traefik:v3.3`
- **Puertos**: 80 (HTTP), 8080 (dashboard)
- **Función**: Reverse proxy para rutado por hostname (tenants)

## Uso

### 1. Configurar variables de entorno

```bash
cp .env.example .env
# Editar .env con tus valores
```

### 2. Construir y levantar stack

```bash
docker compose -f docker-compose.yml --env-file .env up -d --build
```

### 3. Ver logs

```bash
docker compose -f docker-compose.yml logs -f app
```

### 4. Ejecutar comandos Django

```bash
docker compose -f docker-compose.yml exec app python manage.py shell
docker compose -f docker-compose.yml exec app python manage.py createsuperuser
```

### 5. Ejecutar tests

```bash
docker compose -f docker-compose.yml -f docker-compose.test.yml --env-file .env up --abort-on-container-exit --build
```

### 6. Verificar health

```bash
curl http://localhost:8000/health
```

## Variables de Entorno Importantes

- `DEBUG=False`: Obligatorio en producción
- `ALLOWED_HOSTS`: Lista de dominios permitidos (separados por coma)
- `SECRET_KEY`: Clave secreta fuerte (generar con `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`)
- `OPENSEARCH_PASSWORD`: Contraseña de admin de OpenSearch (default: `Admin123!`)

## Troubleshooting

### Staticfiles no cargan
- Verificar que `collectstatic` se ejecutó en el build
- Verificar `STATIC_ROOT` y `WHITENOISE_USE_FINDERS=False`

### 404 en /health
- Verificar que el endpoint está registrado en `config/urls.py`

### OpenSearch no inicia
- Verificar `vm.max_map_count` en el host: `sysctl vm.max_map_count=262144`
- Verificar memoria disponible (mínimo 512MB)

### Celery no procesa tareas
- Verificar `CELERY_BROKER_URL` y `CELERY_RESULT_BACKEND`
- Verificar que Redis está accesible desde el contenedor celery

## Referencias

- [Django + Gunicorn](https://docs.djangoproject.com/en/stable/howto/deployment/wsgi/gunicorn/)
- [WhiteNoise](https://whitenoise.readthedocs.io/)
- [Docker Compose](https://docs.docker.com/compose/)
- [django-tenants](https://django-tenants.readthedocs.io/)
