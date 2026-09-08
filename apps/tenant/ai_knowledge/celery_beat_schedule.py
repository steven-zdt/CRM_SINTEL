"""Celery Beat Schedule para el Vector Store (AI-VECTOR-11, L4).

Registrar en config/celery.py:
    from apps.tenant.ai_knowledge.celery_beat_schedule import CELERY_BEAT_SCHEDULE
    app.conf.beat_schedule.update(CELERY_BEAT_SCHEDULE)

Mismo patron que apps/tenant/dashboard/celery_beat_schedule.py.
"""
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    "ai-knowledge-reindex-enabled-tenants": {
        "task": "apps.tenant.ai_knowledge.tasks.reindex_enabled_tenants",
        "schedule": crontab(minute=0, hour="*/6"),  # cada 6 horas
        "options": {
            "expires": 3600,  # expira en 1 hora si no corre
        },
    },
}
