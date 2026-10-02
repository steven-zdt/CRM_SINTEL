"""
URLs de `SintelMCPView` para el contexto TENANT
(PLAN_MCP_OPERACIONAL_PRIVADO_SINTEL_ERP.md). Se monta en
`config/urls_tenant.py` bajo `mcp/` -- reemplaza el mount directo a
`djangorestframework_mcp.urls`.

Importar `registration` aqui (composition root, mismo patron que
`apps/tenant/proyectos/api/urls.py`) es lo que dispara el registro de los
3 ViewSets piloto (Proyectos/Compras/Clientes, solo list/retrieve) en el
`MCPRegistry` del paquete -- antes de que cualquier request a `tools/list`
pueda verlos.
"""

from django.urls import path

from . import registration  # noqa: F401 -- side effect: registra los ViewSets piloto
from .gateway import SintelMCPView

urlpatterns = [
    path("", SintelMCPView.as_view(), name="sintel-mcp-endpoint"),
]
