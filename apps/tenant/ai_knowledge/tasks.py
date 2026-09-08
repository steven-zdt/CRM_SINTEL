"""Celery -- (re)indexacion asincrona del Vector Store por tenant (AI-VECTOR-08).

Mismo patron probado en `apps/services/maildigester/tasks.py` /
`apps/services/document_ingest/tasks.py`:
- `schema_context(schema_name)` envuelve TODO el trabajo de ORM.
- `autoretry_for` acotado a errores transitorios de RED (nunca de programacion).
- Errores del proveedor de embeddings: se reintentan SOLO si `transient=True`.
- Cola `default` (via CELERY_TASK_ROUTES '*'), nunca `high_priority`.
- Idempotencia real: `EmbeddingService.index_text` salta por `source_version`.
"""

from __future__ import annotations

import logging

from celery import shared_task
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.utils import IntegrityError, ProgrammingError
from django_tenants.utils import schema_context

from apps.services.ai.providers.embedding_base import EmbeddingProviderError

logger = logging.getLogger("ai_engine")


def _clasificar_excepcion(exc: Exception) -> str:
    """transient | security | programming | domain | validation | unknown.

    Nunca decide SI se loguea -- solo COMO. programming/security siempre
    `logger.error(exc_info=True)`; el resto `logger.warning`.
    """
    # PermissionError es subclase de OSError -- se clasifica ANTES del catch-all.
    if isinstance(exc, PermissionError):
        return "security"
    if isinstance(exc, (ConnectionError, TimeoutError, OSError)):
        return "transient"
    if isinstance(exc, EmbeddingProviderError):
        return "transient" if exc.transient else "unknown"
    if isinstance(exc, (ImportError, AttributeError, ProgrammingError, NameError, TypeError)):
        return "programming"
    if isinstance(exc, IntegrityError):
        return "domain"
    if isinstance(exc, (DjangoValidationError, ValueError, KeyError)):
        return "validation"
    return "unknown"


@shared_task(
    bind=True,
    name="apps.tenant.ai_knowledge.tasks.reindex_tenant_knowledge",
    # SOLO transitorios de red. NO AttributeError/ValueError/etc.
    autoretry_for=(ConnectionError, TimeoutError, OSError),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=4,
)
def reindex_tenant_knowledge(self, schema_name: str, source_types: list[str] | None = None) -> dict:
    """(Re)indexa el Vector Store del tenant `schema_name` a partir de la allowlist.

    Fire-and-forget desde una vista/comando -- nunca bloquea una escritura del
    ERP esperando al proveedor de embeddings.
    """
    task_id = getattr(self.request, "id", None)
    logger.info(
        "[reindex_tenant_knowledge] start schema=%s source_types=%s task_id=%s",
        schema_name, source_types or "*", task_id,
    )

    with schema_context(schema_name):
        from apps.tenant.ai_knowledge.services import IndexingService
        from apps.tenant.empresa.models import Empresa

        empresa = Empresa.objects.only("id").first()
        if empresa is None:
            logger.warning("[reindex_tenant_knowledge] schema=%s sin Empresa -- nada que indexar", schema_name)
            return {"schema": schema_name, "status": "NO_EMPRESA"}

        try:
            result = IndexingService().reindex_all(empresa=empresa, source_types=source_types)
        except EmbeddingProviderError as exc:
            if exc.transient:
                logger.warning("[reindex_tenant_knowledge] proveedor transitorio, reintento: %s", exc)
                raise self.retry(exc=exc)
            logger.error("[reindex_tenant_knowledge] proveedor NO transitorio", exc_info=True)
            raise
        except Exception as exc:  # noqa: BLE001 -- clasificamos, no silenciamos
            categoria = _clasificar_excepcion(exc)
            if categoria in ("programming", "security"):
                logger.error("[reindex_tenant_knowledge] %s error schema=%s", categoria, schema_name, exc_info=True)
            else:
                logger.warning("[reindex_tenant_knowledge] %s error schema=%s: %s", categoria, schema_name, exc)
            raise

    payload = {
        "schema": schema_name,
        "status": "OK",
        "totals": result.totals(),
        "by_source": [s.as_dict() for s in result.stats],
    }
    logger.info("[reindex_tenant_knowledge] done schema=%s %s", schema_name, payload["totals"])
    return payload


@shared_task(bind=True, name="apps.tenant.ai_knowledge.tasks.reindex_enabled_tenants")
def reindex_enabled_tenants(self) -> dict:
    """Orquestador de Celery Beat (AI-VECTOR-11, L4): dispara `reindex_tenant_knowledge`
    solo para los tenants con `AIKnowledgeSettings.retrieval_enabled=True`.

    Liviano a proposito -- delega el trabajo real (chunking + embeddings) a
    `reindex_tenant_knowledge.delay(schema)` por tenant, nunca lo hace inline.
    """
    from apps.public.tenants.models import Client

    scheduled = []
    for tenant in Client.objects.exclude(schema_name="public").only("schema_name"):
        with schema_context(tenant.schema_name):
            from apps.tenant.ai_knowledge.models import AIKnowledgeSettings

            if AIKnowledgeSettings.objects.filter(retrieval_enabled=True).exists():
                reindex_tenant_knowledge.delay(tenant.schema_name)
                scheduled.append(tenant.schema_name)

    logger.info("[reindex_enabled_tenants] tenants programados=%s", scheduled)
    return {"scheduled": scheduled}
