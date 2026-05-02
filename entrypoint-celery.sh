#!/bin/bash
# Entrypoint para el contenedor Celery de SINTEL
# ⚠️ DEPRECADO: Este archivo se mantiene por compatibilidad
# El entrypoint.sh unificado ahora maneja ambos roles usando SERVICE_ROLE

# Redirigir al entrypoint unificado
export SERVICE_ROLE=celery
exec /entrypoint.sh "$@"
