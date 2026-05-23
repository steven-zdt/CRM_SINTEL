"""
Celery Beat Schedule para Dashboard v3.9.4
Define periodic tasks para snapshots históricos y mantenimiento.

Registrar en config/celery.py:
    from apps.tenant.dashboard.celery_beat_schedule import CELERY_BEAT_SCHEDULE
    app.conf.beat_schedule = {
        **app.conf.beat_schedule,
        **CELERY_BEAT_SCHEDULE,
    }
"""
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'dashboard-crear-snapshots-diarios': {
        'task': 'apps.tenant.dashboard.tasks.crear_snapshot_metricas_diarias',
        'schedule': crontab(hour=2, minute=0),  # 2:00 AM every day
        'options': {
            'expires': 3600,  # Expires in 1 hour if not run
        }
    },
    'dashboard-limpiar-snapshots-antiguos': {
        'task': 'apps.tenant.dashboard.tasks.limpiar_snapshots_antiguos',
        'schedule': crontab(hour=3, minute=0, day_of_month=1),  # 3:00 AM on 1st of month
        'options': {
            'expires': 3600,
            'kwargs': {'dias': 90}  # Keep 90 days of history
        }
    },
}

"""
Instrucciones de integración:

1. En config/celery.py, agregar:

    from apps.tenant.dashboard.celery_beat_schedule import CELERY_BEAT_SCHEDULE

    # Después de definir app.conf.beat_schedule:
    app.conf.beat_schedule.update(CELERY_BEAT_SCHEDULE)

2. Iniciar Celery Beat:
    celery -A config beat --loglevel=info

3. Verificar que tasks se ejecutan:
    celery -A config inspect active
    celery -A config inspect scheduled

4. Logs:
    tail -f celery_beat.log
"""
