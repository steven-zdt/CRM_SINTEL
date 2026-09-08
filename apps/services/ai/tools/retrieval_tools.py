"""AI-VECTOR-07 -- RetrievalTool: recuperacion semantica del Vector Store.

Tool DELGADA, mismo patron que `ProjectMapTool` (ai_project_map) invoca al
EKG sin poseer su logica: aqui se invoca `RetrievalService` de
`apps/tenant/ai_knowledge/` sin que `apps/services/ai/` posea nada del
Vector Store. `AIEngine.run_tool()` no se toca.

Routing (mandato AI-VECTOR-07): esta tool es para preguntas ABIERTAS /
exploratorias sobre texto libre ("que sabemos de...", "busca documentos
relacionados con..."). NUNCA para un dato transaccional exacto (saldo,
estado, monto, consecutivo): para eso estan las READ Tools deterministas
(`buscar_cliente`, `consultar_factura`, ...). El texto recuperado es
CONTEXTO candidato, no la fuente de verdad de un dato.

Seguridad: el alcance organizacional se aplica EXPLICITAMENTE aqui via
`RetrievalService.search_for_context(context, ...)` -- no se confia en
`risk=SENSITIVE_READ` (que no tiene enforcement automatico, ver
AI_SECURITY_MODEL.md). Los campos FORBIDDEN/MASKED nunca estan en el Vector
Store (allowlist de AI-VECTOR-06).
"""

from __future__ import annotations

import logging

from django.conf import settings

from apps.services.ai.context import AIContext

from .base import BaseTool, ToolKind, ToolResult, ToolRisk

logger = logging.getLogger("ai_engine")

MAX_K = 10


class RetrievalTool(BaseTool):
    name = "buscar_conocimiento"
    description = (
        "Recupera fragmentos de texto libre del tenant relevantes a una "
        "pregunta ABIERTA o exploratoria (ej. 'que informacion tenemos sobre "
        "las condiciones comerciales de este cliente', 'busca notas "
        "relacionadas con esta politica'). Busqueda semantica sobre "
        "observaciones de clientes y descripciones de productos. NO usar para "
        "datos exactos (saldos, estados, montos, fechas): para eso usar las "
        "herramientas deterministas del dominio correspondiente. Solo lectura, "
        "respeta el alcance organizacional (sede/area) del usuario."
    )
    domain = "ai_knowledge"
    kind = ToolKind.READ
    # SAFE_READ: coherente con buscar_cliente/buscar_producto, que ya exponen
    # observaciones/descripcion como SAFE. La garantia real es la allowlist
    # (AI-VECTOR-06): FORBIDDEN/MASKED nunca entran al Vector Store.
    risk = ToolRisk.SAFE_READ
    confirmation_required = False
    idempotent = True

    def run(
        self,
        context: AIContext,
        *,
        query: str = "",
        k: int = 5,
        source_types: list[str] | None = None,
    ) -> ToolResult:
        # Sub-flag propio (AI-VECTOR-07): kind=READ ya lo gatea el engine con
        # AI_READ_ENABLED; este chequeo permite apagar SOLO retrieval en el
        # rollout de AI-VECTOR-11 sin tocar las demas tools READ.
        if not bool(getattr(settings, "AI_RETRIEVAL_ENABLED", False)):
            return ToolResult(
                status="PERMISSION_DENIED",
                message="La recuperacion semantica esta deshabilitada en este entorno.",
            )

        # Control incremental por tenant del rollout (AI-VECTOR-11). El flag
        # global de arriba es el kill switch instantaneo de todo el entorno;
        # este es el que avanza tenant por tenant (piloto -> 2 -> 25% -> ...).
        from apps.tenant.ai_knowledge.models import AIKnowledgeSettings

        if not AIKnowledgeSettings.objects.filter(
            empresa_id=context.empresa_id, retrieval_enabled=True
        ).exists():
            return ToolResult(
                status="PERMISSION_DENIED",
                message="La recuperacion semantica no esta habilitada para este tenant.",
            )

        if not query or not query.strip():
            return ToolResult(status="VALIDATION_ERROR", message="query es obligatorio.")
        if not (1 <= int(k) <= MAX_K):
            return ToolResult(
                status="VALIDATION_ERROR", message=f"k debe estar entre 1 y {MAX_K}."
            )
        if source_types is not None and not isinstance(source_types, list):
            return ToolResult(
                status="VALIDATION_ERROR", message="source_types debe ser una lista."
            )

        # Import diferido -- no arrastrar el arbol de apps tenant en procesos
        # que solo importan apps.services.ai (mismo criterio que buscar_cliente).
        from apps.tenant.ai_knowledge.services import RetrievalService

        hits = RetrievalService().search_for_context(
            context, query, k=int(k), source_types=source_types
        )

        data = [
            {
                "content": h.content,
                "source_type": h.source_type,
                "source_id": h.source_id,
                "document_uuid": h.document_uuid,
                "score": round(h.score, 4),
            }
            for h in hits
        ]
        return ToolResult(status="OK", data=data)
