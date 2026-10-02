"""
Registro de ViewSets expuestos como herramientas MCP reales
(PLAN_MCP_OPERACIONAL_PRIVADO_SINTEL_ERP.md, Seccion 47 "Primer
entregable"). Unico lugar del repo que importa
`djangorestframework_mcp.decorators` -- `apps/tenant/*` nunca conoce esta
dependencia alpha (Seccion 1.4 del plan).

Piloto READ-ONLY (`list`/`retrieve` unicamente, Wave 1 de FASE 34): mismas
3 apps que el plan recomienda para validar primero las relaciones
Proyecto <-> OrdenCompra <-> Cliente (Seccion 47): Proyectos, Compras
(OrdenCompra), Clientes. Sin `create`/`update`/`destroy`/acciones de
dominio todavia -- esas requieren antes definir la matriz de politica CRUD
(Fase 3 del plan), fuera de alcance de este primer entregable.

Nombres de tool resultantes (naming del paquete: `<accion>_<basename>`,
NO coincide todavia con la convencion `<resource>_<operation>` de la
Seccion 31 del plan -- DEFERRED, cosmetico, no bloquea lectura real):
`list_projects`/`retrieve_projects`, `list_purchase_orders`/
`retrieve_purchase_orders`, `list_clients`/`retrieve_clients`.
"""

from djangorestframework_mcp.decorators import mcp_viewset

from apps.tenant.clientes.api.viewsets import ClienteViewSet
from apps.tenant.compras.api.viewsets import OrdenCompraViewSet
from apps.tenant.proyectos.api.viewsets import ProyectoViewSet

READ_ONLY_ACTIONS = ["list", "retrieve"]

mcp_viewset(basename="projects", actions=READ_ONLY_ACTIONS)(ProyectoViewSet)
mcp_viewset(basename="purchase_orders", actions=READ_ONLY_ACTIONS)(OrdenCompraViewSet)
mcp_viewset(basename="clients", actions=READ_ONLY_ACTIONS)(ClienteViewSet)
