"""
URLs de UI para la app proyectos.

WARNING: v3.5: UI URLs para HTMX y templates.
"""

from django.urls import path

from apps.tenant.proyectos.api.viewsets import ProyectoViewSet
from apps.tenant.proyectos.views import ProyectoKpisView, TareaCortaTableView

app_name = "proyectos"

urlpatterns = [
    # Lista de proyectos (UI)
    path("", ProyectoViewSet.as_view({"get": "list", "post": "create"}), name="proyecto-list"),
    # KPIs del listado (HTMX) -- la tabla la sirve POST /api/v1/proyectos/dt/
    # + DataTables JS, ver docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md
    path("tabla/", ProyectoKpisView.as_view(), name="proyecto-tabla"),
    # Idem para el panel "Nueva Tarea" (tareas cortas) — reemplaza la
    # inicializacion de Tabulator en nueva_tarea_list.js
    path("tareas-cortas/tabla/", TareaCortaTableView.as_view(), name="tarea-corta-tabla"),
    # Detalle de proyecto (UI) - Para editar/obtener un proyecto especifico
    path(
        "<int:pk>/",
        ProyectoViewSet.as_view({"get": "retrieve", "put": "update", "patch": "partial_update"}),
        name="proyecto-detail",
    ),
    path(
        "gestor-offcanvas/",
        ProyectoViewSet.as_view({"get": "gestor_offcanvas"}),
        name="proyecto-gestor-offcanvas",
    ),
]
