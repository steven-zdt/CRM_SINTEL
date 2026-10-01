"""
Tools del root_agent (Fase 4 -- spike minimo, ver
PLAN_MAESTRO_INTEGRACION_GOOGLE_ADK_ASISTENTE_IA_SINTEL.md Seccion 62:
"un agente minimo que haga: saludar, buscar_cliente, usando una tool
existente. No WRITE.").

`schema_name`/`user_id` NUNCA son parametros que el LLM decide -- vienen
del `session.state` (inyectado por quien crea la sesion ADK, que en este
diseno es siempre un endpoint/vista Django ya autenticado, nunca el
modelo). `tool_context: ToolContext` es un tipo especial que ADK reconoce
e inyecta el solo -- no aparece en el schema que el LLM ve.

CRITICO (bug real encontrado y corregido durante la Fase 4, ver
docs/adk/ADK_STATUS.md): `build_context_from_session()` y
`AIEngine.run_tool()` deben ejecutarse DENTRO del mismo
`with schema_context(...)` -- este proceso (Django + ADK en el mismo
entorno) no esta posicionado en el schema del tenant por una peticion
HTTP normal, asi que si el schema_context se cierra antes de ejecutar la
tool, esta corre contra el schema equivocado (UndefinedTable real).
"""

from __future__ import annotations

from asgiref.sync import sync_to_async
from django_tenants.utils import schema_context
from google.adk.tools import ToolContext

from apps.services.ai.context import PermissionDeniedError
from apps.services.ai.engine import AIEngine

from .context import build_context_from_session


def _contexto_sesion(tool_context: ToolContext) -> tuple[str, int]:
    schema_name = tool_context.state.get("sintel_schema_name")
    user_id = tool_context.state.get("sintel_user_id")
    return schema_name, user_id


def _buscar_cliente_sync(schema_name: str, user_id: int, query: str):
    """
    Parte sincrona real (ORM/AIEngine) -- las tools de ADK son `async def`
    por convencion de la libreria, pero Django prohibe ORM sincrono dentro
    de un contexto async (SynchronousOnlyOperation, hallazgo real de esta
    sesion). Se aisla aqui y se invoca via sync_to_async desde la tool.
    """
    with schema_context(schema_name):
        context = build_context_from_session(schema_name=schema_name, user_id=user_id)
        return AIEngine.run_tool("buscar_cliente", request=None, context=context, search=query)


async def saludar() -> dict:
    """Saluda al usuario -- tool trivial, no requiere contexto de tenant, solo para
    verificar que el agente responde."""
    return {
        "ok": True,
        "message": "Hola, soy el Asistente IA de SINTEL (spike ADK, sin escritura habilitada).",
    }


async def buscar_cliente(query: str, tool_context: ToolContext) -> dict:
    """
    Busca clientes del tenant actual por razon social, NIT o nombre
    comercial. Solo lectura -- envuelve la tool real `buscar_cliente`
    del AIToolRegistry via AIEngine.run_tool(), nunca consulta la base
    de datos directamente.

    Args:
      query: texto de busqueda (razon social, NIT o nombre comercial).
    """
    schema_name, user_id = _contexto_sesion(tool_context)
    if not schema_name or not user_id:
        return {
            "ok": False,
            "status": "PERMISSION_DENIED",
            "message": "Sesion ADK sin contexto de tenant real.",
        }

    try:
        result = await sync_to_async(_buscar_cliente_sync, thread_sensitive=True)(
            schema_name, user_id, query
        )
    except PermissionDeniedError as exc:
        return {"ok": False, "status": "PERMISSION_DENIED", "message": str(exc)}

    if result.status != "OK":
        return {"ok": False, "status": result.status, "message": result.message}
    return {"ok": True, "status": "OK", "clientes": result.data}
