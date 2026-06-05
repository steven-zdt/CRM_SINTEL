"""
Configuración de Celery para el proyecto SINTEL.

WARNING: IMPORTANTE: 
- La cola puede ser compartida entre tenants
- El worker debe cambiar connection.schema_name usando schema_context en las tareas
- Usar @shared_task para tareas que pueden ejecutarse en cualquier tenant
- Import explícito de módulos fuera de INSTALLED_APPS para evitar "unregistered task"
"""
import os

from celery import Celery

# Establecer el módulo de configuración de Django por defecto
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Crear instancia de Celery
app = Celery('config')  # Usar 'config' para consistencia con -A config.celery

# Cargar configuración desde settings.py
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-descubrir tareas en todas las apps instaladas
app.autodiscover_tasks()

# WARNING: IMPORT EXPLÍCITO: Módulos fuera de INSTALLED_APPS (apps/services)
# Esto asegura que las tareas se registren aunque no estén en una app Django
app.conf.imports = (
    "apps.services.maildigester.tasks",  # Tarea crítica de ingesta de correo
    "apps.tenant.dashboard.tasks",       # Dashboard: snapshots + caché
    "apps.public.core.tasks",            # Email transaccional (invitacion, reset, codigo activacion)
)

# ============================================================================
# Celery Beat Schedule — Tareas Periódicas
# ============================================================================
from apps.tenant.dashboard.celery_beat_schedule import CELERY_BEAT_SCHEDULE

# Merge dashboard schedule con schedule existente (si existe)
if not hasattr(app.conf, 'beat_schedule'):
    app.conf.beat_schedule = {}

app.conf.beat_schedule.update(CELERY_BEAT_SCHEDULE)


@app.task(bind=True)
def debug_task(self):
    """Tarea de debug para probar Celery."""
    print(f'Request: {self.request!r}')
