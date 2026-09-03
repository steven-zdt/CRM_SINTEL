from django.apps import AppConfig


class AiKnowledgeConfig(AppConfig):
    """Vector Store tenant-scoped del AI Engine (POC pgvector, AI-VECTOR-03).

    Almacena texto de origen troceado en chunks + sus embeddings, dentro del
    schema de cada tenant (aislamiento real de PostgreSQL, mismo mecanismo que
    el resto del ERP -- nunca `public.ai_chunks + tenant_id`).

    Es una app de DATOS (TENANT_APPS). La logica de orquestacion vive en
    `apps/services/ai/` (que sigue sin modelos): un `RetrievalTool` delgado
    (AI-VECTOR-07) invocara los servicios de esta app, igual que
    `ai_project_map` invoca al EKG sin poseer su logica.

    Bitacora: docs/ai/AI_VECTOR_POC_EXECUTION.md
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.tenant.ai_knowledge"
    label = "tenant_ai_knowledge"
    verbose_name = "AI Knowledge (Vector Store)"
