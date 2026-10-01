"""
Vistas HTML server-rendered (django-tables2 + HTMX) para los paneles Detail
de los split-pane Master-Detail de Empleados (historial de nominas/
liquidaciones del empleado seleccionado en el Master).

El directorio de Empleados, Contratos, Resoluciones DIAN, Periodos de Nomina,
y los paneles Master de Nominas/Liquidaciones migraron a DataTables -- POST
/api/v1/empleados/{dt,contratos/dt,resoluciones-dian/dt,periodos-nomina/dt,
con-nominas/dt,con-liquidaciones/dt}/ + DataTables JS, ver
docs/remediation/DATATABLES_PILOT_VENTAS_STATUS.md (EmpleadoTable/
ContratoTable/ResolucionDIANTable/PeriodoNominaTable/
NominaEmpleadoMasterTable/LiquidacionEmpleadoMasterTable, django-tables2,
retirados junto con sus TableView). Los paneles Detail siguen aqui porque no
son listados planos independientes -- dependen de la seleccion hecha en el
Master (?empleado_uuid=), no de paginacion/busqueda propia.

No reemplazan la API DRF (apps/tenant/empleados/api/viewsets.py), que sigue
viva para crear/editar/cancelar/eliminar y para consumidores API-first.
"""

import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django_tables2 import SingleTableView
from rest_framework.exceptions import ValidationError as DRFValidationError

from apps.tenant.api.mixins import SintelDSVMixin
from apps.tenant.empleados.models import Devengo, Empleado, LiquidacionPrestacion
from apps.tenant.empleados.services.selectors import DevengoSelector
from apps.tenant.empleados.tables import DevengoDetailTable, LiquidacionDetailTable

logger = logging.getLogger(__name__)


class _EmpleadosTableViewBase(LoginRequiredMixin, SintelDSVMixin, SingleTableView):
    table_pagination = {"per_page": 20}

    def _resolver_empresa_id(self):
        try:
            return self.get_empresa_id()
        except DRFValidationError:
            logger.warning(
                "[%s] Sin empresa resuelta para user=%s",
                self.__class__.__name__,
                self.request.user.pk,
            )
            return None


# ============================================================================
# MASTER-DETAIL: Nominas
# ============================================================================


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

        self._empleado = (
            Empleado.objects.filter(empresa_id=empresa_id, uuid=empleado_uuid)
            .only("id", "uuid", "primer_nombre", "primer_apellido", "numero_documento")
            .first()
        )
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

        self._empleado = (
            Empleado.objects.filter(empresa_id=empresa_id, uuid=empleado_uuid)
            .only("id", "uuid", "primer_nombre", "primer_apellido", "numero_documento")
            .first()
        )
        if not self._empleado:
            return LiquidacionPrestacion.objects.none()

        qs = LiquidacionPrestacion.objects.filter(
            empresa_id=empresa_id, empleado_id=self._empleado.id
        ).only(
            "id",
            "uuid",
            "tipo_liquidacion",
            "fecha_corte",
            "base_salarial",
            "valor_total",
            "estado",
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
