"""
Vista HTML server-rendered para el reporte "Resumen de Ventas" -- consume
el Reporting Hub (apps/services/reporting/), no re-implementa la agregacion.

Mismo patron que views.py::VentaTableView (LoginRequiredMixin + fragmento
HTMX), pero la fuente de datos es ReportQueryEngine (dataset
`ventas.resumen`) en vez de VentaSelector directo -- este es el reporte
transversal, no el listado operativo de Ventas.

WARNING: la tabla de resultados se renderiza como HTML plano (no
django_tables2.Table) porque las columnas son dinamicas por request
(dependen de `group_by`, elegido por el usuario) -- una Table de
django-tables2 declara sus columnas de forma estatica en Python, ajena a
un dataset declarativo. Ver docs/reporting/FRONTEND_REPORTING_ARCHITECTURE.md
para la justificacion completa de esta decision de diseño.
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views.generic import View

from apps.services.reporting.contracts import ReportRequest
from apps.services.reporting.query_engine import ReportQueryEngine, ReportValidationError
from apps.services.reporting.scope import ScopeViolationError

_DATASET_ID = "ventas.resumen"
_ALL_MEASURES = ("cantidad_ventas", "subtotal", "impuestos", "total")


class VentaReportesContainerView(LoginRequiredMixin, View):
    """Contenedor completo (filtros + panel) -- lo que la landing page de
    Reportes (apps/tenant/core) swap-ea via HTMX cuando el usuario elige
    'Resumen de Ventas' en el catalogo."""

    def get(self, request, *args, **kwargs):
        return render(request, "tenant/ventas/reportes_ventas_container.html", {})


class VentaReportesView(LoginRequiredMixin, View):
    template_name = "tenant/ventas/partials/reportes_ventas.html"

    def get(self, request, *args, **kwargs):
        group_by = request.GET.get("group_by") or "fecha"
        if group_by not in ("fecha", "cliente", "estado"):
            group_by = "fecha"

        filters = {}
        for key in ("fecha_inicio", "fecha_fin", "estado", "cliente_id"):
            value = request.GET.get(key)
            if value:
                filters[key] = value

        context = {
            "group_by": group_by,
            "filters": filters,
            "dataset_id": _DATASET_ID,
        }

        report_request = ReportRequest(
            dataset_id=_DATASET_ID,
            filters=filters,
            group_by=(group_by,),
            measures=_ALL_MEASURES,
            order_by=f"-{group_by}" if group_by == "fecha" else None,
            page_size=200,
        )

        try:
            result = ReportQueryEngine().execute(report_request, request)
        except ScopeViolationError as exc:
            context["error_kind"] = "forbidden"
            context["error_message"] = str(exc)
            return render(request, self.template_name, context)
        except ReportValidationError as exc:
            context["error_kind"] = "invalid"
            context["error_message"] = str(exc)
            return render(request, self.template_name, context)

        context["result"] = result
        context["is_empty"] = result.count == 0
        # WARNING: Django templates no soportan lookup dinamico row[column] --
        # se precomputa aqui como lista de listas, en el mismo orden que
        # result.columns, para que el template solo itere sin lookup.
        context["rows_as_lists"] = [
            [row.get(col, "") for col in result.columns] for row in result.rows
        ]
        return render(request, self.template_name, context)
