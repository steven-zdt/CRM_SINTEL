"""
Vistas HTML server-rendered (django-tables2 + HTMX) para los listados de
Contabilidad. Expansion Fase 5-BIS (ver PLAN_UNICO_CORRECCIONES.md).

No reemplazan la API DRF (apps/tenant/contabilidad/api/viewsets.py), que
sigue viva para crear/editar/aprobar/cerrar y para consumidores API-first.
"""
import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, F, Q
from django_tables2 import SingleTableView
from rest_framework.exceptions import ValidationError as DRFValidationError

from apps.tenant.api.mixins import SintelDSVMixin
from apps.tenant.contabilidad.models import AsientoContable, PeriodoContable, Retencion
from apps.tenant.contabilidad.services.selectors import (
    ASIENTO_LIST_FIELDS,
    AsientoContableSelector,
    CuentaContableSelector,
    PeriodoContableSelector,
    PlantillaContableSelector,
)
from apps.tenant.contabilidad.tables import (
    AsientoContableTable,
    CuentaContableTable,
    PeriodoContableTable,
    PlantillaContableTable,
    RetencionTable,
)

logger = logging.getLogger(__name__)


class _ContabilidadTableViewBase(LoginRequiredMixin, SintelDSVMixin, SingleTableView):
    """Resuelve empresa_id una sola vez; retorna queryset vacio si no hay tenant."""

    table_pagination = {"per_page": 20}

    def _resolver_empresa_id(self):
        try:
            return self.get_empresa_id()
        except DRFValidationError:
            logger.warning(
                "[%s] Sin empresa resuelta para user=%s",
                self.__class__.__name__, self.request.user.pk,
            )
            return None


class CuentaContableTableView(_ContabilidadTableViewBase):
    table_class = CuentaContableTable
    template_name = "tenant/contabilidad/partials/tabla_cuentas.html"

    def get_queryset(self):
        empresa_id = self._resolver_empresa_id()
        if not empresa_id:
            from apps.tenant.contabilidad.models import CuentaContable
            return CuentaContable.objects.none()

        qs = CuentaContableSelector.get_qs_list(empresa_id=empresa_id)
        search = (self.request.GET.get("q") or "").strip()
        if search:
            qs = qs.filter(Q(codigo__icontains=search) | Q(nombre__icontains=search))
        return qs


class PeriodoContableTableView(_ContabilidadTableViewBase):
    table_class = PeriodoContableTable
    template_name = "tenant/contabilidad/partials/tabla_periodos.html"

    def get_queryset(self):
        empresa_id = self._resolver_empresa_id()
        if not empresa_id:
            return PeriodoContable.objects.none()

        qs = PeriodoContableSelector.get_qs_list(empresa_id=empresa_id)
        search = (self.request.GET.get("q") or "").strip()
        if search:
            qs = qs.filter(periodo__icontains=search)
        estado = self.request.GET.get("estado") or None
        if estado:
            qs = qs.filter(estado=estado)
        return qs


class AsientoContableTableView(_ContabilidadTableViewBase):
    table_class = AsientoContableTable
    template_name = "tenant/contabilidad/partials/tabla_asientos.html"

    def get_queryset(self):
        empresa_id = self._resolver_empresa_id()
        if not empresa_id:
            return AsientoContable.objects.none()

        qs = (
            AsientoContable.objects.filter(empresa_id=empresa_id)
            .only(*ASIENTO_LIST_FIELDS)
            .annotate(movimientos_count=Count("movimientos", distinct=True))
        )
        search = (self.request.GET.get("q") or "").strip()
        if search:
            qs = qs.filter(Q(numero__icontains=search) | Q(descripcion__icontains=search))
        estado = self.request.GET.get("estado") or None
        if estado:
            qs = qs.filter(estado=estado)
        cuadratura = self.request.GET.get("cuadratura") or None
        if cuadratura == "cuadrado":
            qs = qs.filter(total_debe=F("total_haber"))
        elif cuadratura == "no_cuadrado":
            qs = qs.exclude(total_debe=F("total_haber"))
        return qs


class RetencionTableView(_ContabilidadTableViewBase):
    """Solo lectura -- las retenciones se generan via Pull Model (RetencionesService)."""

    table_class = RetencionTable
    template_name = "tenant/contabilidad/partials/tabla_retenciones.html"

    def get_queryset(self):
        empresa_id = self._resolver_empresa_id()
        if not empresa_id:
            return Retencion.objects.none()

        qs = Retencion.objects.filter(empresa_id=empresa_id).select_related(
            "configuracion", "asiento_contable"
        ).only(
            "id", "uuid", "tipo", "porcentaje", "base", "monto", "naturaleza",
            "documento_origen_app", "documento_origen_modelo", "documento_origen_id",
            "reversada", "created_at",
            "configuracion__id", "configuracion__tipo_tercero",
            "asiento_contable__uuid", "asiento_contable__numero",
        )
        search = (self.request.GET.get("q") or "").strip()
        if search:
            qs = qs.filter(
                Q(documento_origen_app__icontains=search)
                | Q(documento_origen_modelo__icontains=search)
                | Q(uuid__icontains=search)
            )
        tipo = self.request.GET.get("tipo") or None
        if tipo:
            qs = qs.filter(tipo=tipo)
        naturaleza = self.request.GET.get("naturaleza") or None
        if naturaleza:
            qs = qs.filter(naturaleza=naturaleza)
        reversada = self.request.GET.get("reversada")
        if reversada in ("true", "false"):
            qs = qs.filter(reversada=(reversada == "true"))
        return qs


class PlantillaContableTableView(_ContabilidadTableViewBase):
    table_class = PlantillaContableTable
    template_name = "tenant/contabilidad/partials/tabla_plantillas.html"

    def get_queryset(self):
        empresa_id = self._resolver_empresa_id()
        if not empresa_id:
            from apps.tenant.contabilidad.models import PlantillaContable
            return PlantillaContable.objects.none()

        qs = PlantillaContableSelector.get_qs_list(empresa_id=empresa_id).annotate(
            lineas_count=Count("lineas", distinct=True)
        )
        search = (self.request.GET.get("q") or "").strip()
        if search:
            qs = qs.filter(Q(nombre__icontains=search) | Q(tipo_transaccion__icontains=search))
        tipo = self.request.GET.get("tipo_transaccion") or None
        if tipo:
            qs = qs.filter(tipo_transaccion=tipo)
        activo = self.request.GET.get("activo")
        if activo in ("true", "false"):
            qs = qs.filter(activo=(activo == "true"))
        return qs
