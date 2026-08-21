"""
Vistas HTML server-rendered (django-tables2 + HTMX) para los listados de
Empleados. Expansion Fase 5-BIS (ver PLAN_UNICO_CORRECCIONES.md).

No reemplazan la API DRF (apps/tenant/empleados/api/viewsets.py), que sigue
viva para crear/editar/cancelar/eliminar y para consumidores API-first.
"""
import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django_tables2 import SingleTableView
from rest_framework.exceptions import ValidationError as DRFValidationError

from apps.tenant.api.mixins import SintelDSVMixin
from apps.tenant.empleados.models import Contrato, Devengo, Empleado, LiquidacionPrestacion, PeriodoNomina, ResolucionDIAN
from apps.tenant.empleados.services.selectors import ContratoSelector, DevengoSelector, EmpleadoSelector, PeriodoNominaSelector
from apps.tenant.empleados.tables import (
    ContratoTable,
    DevengoDetailTable,
    EmpleadoTable,
    LiquidacionDetailTable,
    LiquidacionEmpleadoMasterTable,
    NominaEmpleadoMasterTable,
    PeriodoNominaTable,
    ResolucionDIANTable,
)

logger = logging.getLogger(__name__)


class _EmpleadosTableViewBase(LoginRequiredMixin, SintelDSVMixin, SingleTableView):
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


class EmpleadoTableView(_EmpleadosTableViewBase):
    table_class = EmpleadoTable
    template_name = "tenant/empleados/partials/tabla_empleados.html"

    def get_queryset(self):
        empresa_id = self._resolver_empresa_id()
        if not empresa_id:
            return Empleado.objects.none()
        search = (self.request.GET.get("q") or "").strip() or None

        # [OSF Fase F13] Antes de esta fase, la grilla HTML no aplicaba
        # ningun filtro de alcance organizacional, a diferencia del endpoint
        # DRF equivalente (F7) - mismo patron de bug recurrente (compras F5,
        # facturas F11, gastos/proyectos F13). NULL-safe.
        from apps.tenant.core.services.organizational_scope import (
            OrganizationalScope,
            OrganizationalScopeError,
        )
        try:
            scope = OrganizationalScope.resolve(self.request)
            sede_ids, area_ids = scope.sede_ids, scope.area_ids
        except OrganizationalScopeError:
            sede_ids, area_ids = None, None

        return EmpleadoSelector.get_list(
            empresa_id=empresa_id, search=search, sede_ids=sede_ids, area_ids=area_ids,
        )


class ContratoTableView(_EmpleadosTableViewBase):
    table_class = ContratoTable
    template_name = "tenant/empleados/partials/tabla_contratos.html"

    def get_queryset(self):
        empresa_id = self._resolver_empresa_id()
        if not empresa_id:
            return Contrato.objects.none()
        search = (self.request.GET.get("q") or "").strip() or None
        return ContratoSelector.get_list(empresa_id=empresa_id, search=search)


class ResolucionDIANTableView(_EmpleadosTableViewBase):
    table_class = ResolucionDIANTable
    template_name = "tenant/empleados/partials/tabla_resoluciones.html"

    def get_queryset(self):
        empresa_id = self._resolver_empresa_id()
        if not empresa_id:
            return ResolucionDIAN.objects.none()
        search = (self.request.GET.get("q") or "").strip()
        qs = ResolucionDIAN.objects.filter(empresa_id=empresa_id).order_by("-vigente", "-fecha_resolucion")
        if search:
            qs = qs.filter(numero_resolucion__icontains=search)
        return qs


class PeriodoNominaTableView(_EmpleadosTableViewBase):
    table_class = PeriodoNominaTable
    template_name = "tenant/empleados/partials/tabla_periodos.html"

    def get_queryset(self):
        empresa_id = self._resolver_empresa_id()
        if not empresa_id:
            return PeriodoNomina.objects.none()
        estado = (self.request.GET.get("estado") or "").strip() or None
        return PeriodoNominaSelector.get_list(empresa_id, estado=estado)


# ============================================================================
# MASTER-DETAIL: Nominas
# ============================================================================

class NominaMasterTableView(_EmpleadosTableViewBase):
    """Master: empleados con al menos 1 nomina registrada."""

    table_class = NominaEmpleadoMasterTable
    template_name = "tenant/empleados/partials/tabla_nomina_master.html"
    table_pagination = {"per_page": 30}

    def get_queryset(self):
        empresa_id = self._resolver_empresa_id()
        if not empresa_id:
            return Empleado.objects.none()

        qs = (
            Empleado.objects.filter(empresa_id=empresa_id)
            .annotate(total_nominas=Count("nominas", distinct=True))
            .filter(total_nominas__gt=0)
            .only("id", "uuid", "primer_nombre", "primer_apellido", "numero_documento")
            .order_by("-total_nominas", "primer_apellido", "primer_nombre")
        )
        search = (self.request.GET.get("q") or "").strip()
        if search:
            qs = qs.filter(
                Q(primer_nombre__icontains=search)
                | Q(primer_apellido__icontains=search)
                | Q(numero_documento__icontains=search)
            )
        return qs


class NominaDetailTableView(_EmpleadosTableViewBase):
    """
    Detail: historico de nominas (Devengo) del empleado indicado en
    ?empleado_uuid=. Retorna el panel completo (header + tabla), no solo la
    tabla, porque el nombre/contador/boton "Nueva Nomina" del header dependen
    del empleado seleccionado en el master.
    """

    table_class = DevengoDetailTable
    template_name = "tenant/empleados/partials/tabla_nomina_detalle.html"

    def get_queryset(self):
        empresa_id = self._resolver_empresa_id()
        empleado_uuid = self.request.GET.get("empleado_uuid")
        if not empresa_id or not empleado_uuid:
            self._empleado = None
            return Devengo.objects.none()

        self._empleado = Empleado.objects.filter(empresa_id=empresa_id, uuid=empleado_uuid).only(
            "id", "uuid", "primer_nombre", "primer_apellido", "numero_documento"
        ).first()
        if not self._empleado:
            return Devengo.objects.none()

        return DevengoSelector.get_historial(empleado_id=self._empleado.id, empresa_id=empresa_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["empleado"] = getattr(self, "_empleado", None)
        return context


# ============================================================================
# MASTER-DETAIL: Liquidaciones
# ============================================================================

class LiquidacionMasterTableView(_EmpleadosTableViewBase):
    """Master: TODOS los empleados del tenant, ordenados por total de liquidaciones DESC."""

    table_class = LiquidacionEmpleadoMasterTable
    template_name = "tenant/empleados/partials/tabla_liquidacion_master.html"
    table_pagination = {"per_page": 30}

    def get_queryset(self):
        empresa_id = self._resolver_empresa_id()
        if not empresa_id:
            return Empleado.objects.none()

        qs = (
            Empleado.objects.filter(empresa_id=empresa_id)
            .annotate(total_liquidaciones=Count("liquidaciones", distinct=True))
            .only("id", "uuid", "primer_nombre", "primer_apellido", "numero_documento")
            .order_by("-total_liquidaciones", "primer_apellido", "primer_nombre")
        )
        search = (self.request.GET.get("q") or "").strip()
        if search:
            qs = qs.filter(
                Q(primer_nombre__icontains=search)
                | Q(primer_apellido__icontains=search)
                | Q(numero_documento__icontains=search)
            )
        return qs


class LiquidacionDetailTableView(_EmpleadosTableViewBase):
    """
    Detail: historico de liquidaciones del empleado indicado en
    ?empleado_uuid= (y opcionalmente ?tipo_liquidacion=). Retorna el panel
    completo (header + filtros + tabla), mismo motivo que NominaDetailTableView.
    """

    table_class = LiquidacionDetailTable
    template_name = "tenant/empleados/partials/tabla_liquidacion_detalle.html"

    def get_queryset(self):
        empresa_id = self._resolver_empresa_id()
        empleado_uuid = self.request.GET.get("empleado_uuid")
        if not empresa_id or not empleado_uuid:
            self._empleado = None
            return LiquidacionPrestacion.objects.none()

        self._empleado = Empleado.objects.filter(empresa_id=empresa_id, uuid=empleado_uuid).only(
            "id", "uuid", "primer_nombre", "primer_apellido", "numero_documento"
        ).first()
        if not self._empleado:
            return LiquidacionPrestacion.objects.none()

        qs = LiquidacionPrestacion.objects.filter(
            empresa_id=empresa_id, empleado_id=self._empleado.id
        ).only(
            "id", "uuid", "tipo_liquidacion", "fecha_corte", "base_salarial", "valor_total", "estado",
        )
        tipo = self.request.GET.get("tipo_liquidacion") or None
        if tipo:
            qs = qs.filter(tipo_liquidacion=tipo)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["empleado"] = getattr(self, "_empleado", None)
        context["tipo_activo"] = self.request.GET.get("tipo_liquidacion") or ""
        return context
