"""
ViewSet del Reporting Hub -- FASE 27 (mision Reporting Hub).

No hereda BaseTenantViewSet (ModelViewSet con lookup UUID) porque no expone
CRUD de un modelo Django -- expone un catalogo declarativo + ejecucion de
consultas, el mismo patron ya aceptado en esta app para
LibroDiarioViewSet (apps/tenant/contabilidad/api/viewsets.py). Reutiliza
autenticacion/permisos existentes en vez de inventar nuevos.
"""
import logging

from django.http import HttpResponse
from rest_framework import status, viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.services.reporting.api.serializers import (
    ReportExportRequestSerializer,
    ReportQueryRequestSerializer,
)
from apps.services.reporting.contracts import ReportRequest
from apps.services.reporting.exporters import export
from apps.services.reporting.query_engine import ReportQueryEngine, ReportValidationError
from apps.services.reporting.registry import registry
from apps.services.reporting.scope import ScopeViolationError
from apps.tenant.api.base import RelaxedJWTAuthentication
from apps.tenant.api.permissions import IsTenantMember

logger = logging.getLogger("apps.services.reporting.api")

_CONTENT_TYPES = {
    "csv": "text/csv",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


def _parse_export_query_params(query_params) -> dict:
    """Traduce ?filters[fecha_inicio]=X&group_by=a,b&export_format=csv (GET,
    para que un <a href> normal dispare la descarga sin JS) al mismo shape
    que ReportExportRequestSerializer espera desde JSON (POST).

    WARNING: el parametro se llama `export_format`, NO `format` -- ver nota
    en ReportExportRequestSerializer (colision con URL_FORMAT_OVERRIDE de DRF)."""
    filters = {}
    prefix = "filters["
    for key in query_params:
        if key.startswith(prefix) and key.endswith("]"):
            filters[key[len(prefix):-1]] = query_params[key]

    data = {"filters": filters}
    if query_params.get("dataset_id"):
        data["dataset_id"] = query_params["dataset_id"]
    if query_params.get("group_by"):
        data["group_by"] = [v for v in query_params["group_by"].split(",") if v]
    if query_params.get("measures"):
        data["measures"] = [v for v in query_params["measures"].split(",") if v]
    if query_params.get("order_by"):
        data["order_by"] = query_params["order_by"]
    if query_params.get("page"):
        data["page"] = query_params["page"]
    if query_params.get("page_size"):
        data["page_size"] = query_params["page_size"]
    if query_params.get("export_format"):
        data["export_format"] = query_params["export_format"]
    return data


def _dataset_to_dict(dataset) -> dict:
    return {
        "dataset_id": dataset.dataset_id,
        "owner_app": dataset.owner_app,
        "name": dataset.name,
        "description": dataset.description,
        "dimensions": [
            {"name": d.name, "label": d.label, "type": d.field_type.value, "description": d.description}
            for d in dataset.dimensions
        ],
        "measures": [
            {
                "name": m.name, "label": m.label, "type": m.field_type.value,
                "aggregation": m.aggregation.value, "description": m.description,
            }
            for m in dataset.measures
        ],
        "filters": [
            {
                "name": f.name, "label": f.label, "type": f.field_type.value,
                "description": f.description, "required": f.required,
            }
            for f in dataset.filters
        ],
        "default_ordering": dataset.default_ordering,
        "export_formats": list(dataset.export_formats),
    }


class ReportingViewSet(viewsets.ViewSet):
    """
    GET  /api/v1/reporting/                    -> catalogo completo
    GET  /api/v1/reporting/{dataset_id}/       -> contrato de un dataset
    POST /api/v1/reporting/query/              -> ejecuta un ReportRequest, JSON
    POST /api/v1/reporting/export/             -> ejecuta y exporta (csv/xlsx)

    No usa SintelDSVMixin/get_empresa_id() -- el empresa_id efectivo se
    resuelve dentro de ReportQueryEngine.execute() via el Scope Engine
    (apps/services/reporting/scope.py -> OrganizationalScope.resolve()),
    no en la capa HTTP.
    """
    authentication_classes = [RelaxedJWTAuthentication, SessionAuthentication]
    permission_classes = [IsTenantMember]
    # WARNING: BUGFIX: el regex por defecto de DRF para `pk` ([^/.]+) excluye
    # el punto -- dataset_id usa notacion "app.dataset" (ej. "ventas.resumen"),
    # por lo que GET /reporting/<dataset_id>/ nunca resolvia. Confirmado en
    # vivo: retornaba 404 "No encontrado" para todo dataset_id con punto.
    lookup_value_regex = r"[^/]+"

    def list(self, request, *args, **kwargs):
        datasets = registry.list_datasets()
        return Response([_dataset_to_dict(d) for d in datasets])

    def retrieve(self, request, pk=None, *args, **kwargs):
        dataset = registry.get_dataset(pk)
        if dataset is None:
            return Response({"detail": f"Dataset desconocido: {pk}"}, status=status.HTTP_404_NOT_FOUND)
        return Response(_dataset_to_dict(dataset))

    @action(detail=False, methods=["post"], url_path="query")
    def query(self, request):
        serializer = ReportQueryRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        report_request = ReportRequest(
            dataset_id=data["dataset_id"],
            filters=data["filters"],
            group_by=tuple(data["group_by"]),
            measures=tuple(data["measures"]),
            order_by=data["order_by"],
            page=data["page"],
            page_size=data["page_size"],
        )
        try:
            result = ReportQueryEngine().execute(report_request, request)
        except ReportValidationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except ScopeViolationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        return Response(result.to_dict())

    @action(detail=False, methods=["get", "post"], url_path="export")
    def export_report(self, request):
        # GET: descarga directa via <a href> (sin JS, sin CSRF -- solo
        # lectura). POST: cliente JS que ya tenga el ReportRequest armado.
        payload = _parse_export_query_params(request.query_params) if request.method == "GET" else request.data
        serializer = ReportExportRequestSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        report_request = ReportRequest(
            dataset_id=data["dataset_id"],
            filters=data["filters"],
            group_by=tuple(data["group_by"]),
            measures=tuple(data["measures"]),
            order_by=data["order_by"],
            page=data["page"],
            page_size=data["page_size"],
        )
        fmt = data["export_format"]
        try:
            result = ReportQueryEngine().execute(report_request, request)
        except ReportValidationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except ScopeViolationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)

        if fmt == "json":
            return Response(export(result, fmt))

        try:
            payload = export(result, fmt)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        response = HttpResponse(payload, content_type=_CONTENT_TYPES.get(fmt, "application/octet-stream"))
        filename = f"{result.dataset_id}.{fmt}"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
