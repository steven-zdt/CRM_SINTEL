"""
API Mixins para Empleados - Inyección de servicios en ViewSets.

WARNING: SINTEL v2.61.4: Arquitectura Service Layer Modular.
- Este archivo contiene mixins específicos para cada modelo.
- Inyectan acceso estandarizado a Selectors, CRUDService y BusinessService.
- Usan get_empresa_id() de SintelDSVMixin para Zero Trust.
"""
from apps.tenant.empleados.services.selectors import (
    ContratoSelector,
    DevengoSelector,
    EmpleadoSelector,
    NominaSummarySelector,
)
from apps.tenant.empleados.services.business_service import (
    ContratoBusinessService,
    DevengoBusinessService,
    EmpleadoBusinessService,
    NominaCalculationService,
)


class EmpleadoServiceMixin:
    """
    Service mixin para Empleado ViewSet.
    Inyecta acceso a Selectors y BusinessService.
    Requiere que el ViewSet herede de SintelDSVMixin (para get_empresa_id).
    """

    # Instancias de servicios (pueden ser sobrescritas en subclasses)
    selector_class = EmpleadoSelector
    business_service_class = EmpleadoBusinessService
    summary_selector_class = NominaSummarySelector

    def get_qs_list(self):
        """Retorna queryset de lista usando selector."""
        empresa_id = self.get_empresa_id()
        search = self.request.query_params.get('search') if hasattr(self, 'request') else None
        return self.selector_class.get_list(empresa_id, search=search)

    def get_qs_detail(self):
        """Retorna queryset de detalle usando selector."""
        empresa_id = self.get_empresa_id()
        lookup_kwarg = getattr(self, 'lookup_url_kwarg', 'pk')
        return self.selector_class.get_detail(empresa_id, self.kwargs.get(lookup_kwarg))

    def service_crear_empleado(self, serializer):
        """Crea empleado usando business service."""
        empresa = self._get_empresa()
        return self.business_service_class.crear_empleado(serializer.validated_data, empresa)

    def service_actualizar_empleado(self, serializer):
        """Actualiza empleado usando business service."""
        return self.business_service_class.actualizar_empleado(
            serializer.instance,
            serializer.validated_data
        )

    def service_eliminar_empleado_retirado(self, empleado):
        """Elimina empleado retirado usando business service."""
        return self.business_service_class.eliminar_empleado_retirado(empleado)

    def service_get_nomina_summary(self, request):
        """Obtiene resumen de nómina usando selector."""
        empresa_id = self.get_empresa_id()
        if not empresa_id:
            return None
        return self.summary_selector_class.get_summary(empresa_id)

    def _get_empresa(self):
        """Helper para obtener empresa actual de forma segura."""
        from apps.tenant.api.utils import resolve_tenant_empresa
        return resolve_tenant_empresa(self.request, self)


class ContratoServiceMixin:
    """
    Service mixin para Contrato ViewSet.
    Inyecta acceso a Selectors y BusinessService.
    """

    selector_class = ContratoSelector
    business_service_class = ContratoBusinessService

    def get_qs_list(self):
        """Retorna queryset de lista usando selector."""
        empresa_id = self.get_empresa_id()
        search = self.request.query_params.get('search') if hasattr(self, 'request') else None
        empleado_id = self.request.query_params.get('empleado') if hasattr(self, 'request') else None
        if empleado_id:
            try:
                empleado_id = int(empleado_id)
            except (TypeError, ValueError):
                empleado_id = None
        return self.selector_class.get_list(empresa_id, search=search, empleado_id=empleado_id)

    def get_qs_detail(self):
        """Retorna queryset de detalle usando selector."""
        empresa_id = self.get_empresa_id()
        lookup_kwarg = getattr(self, 'lookup_url_kwarg', 'pk')
        return self.selector_class.get_detail(empresa_id, self.kwargs.get(lookup_kwarg))

    def service_gestionar_contrato(self, empleado, data, contrato_existente=None):
        """Gestiona creación/actualización de contrato."""
        return self.business_service_class.gestionar_contrato(empleado, data, contrato_existente)

    def service_preparar_datos_contrato(self, data):
        """Prepara y normaliza datos de contrato."""
        return self.business_service_class.preparar_datos_contrato(data)


class DevengoServiceMixin:
    """
    Service mixin para Devengo ViewSet.
    Inyecta acceso a Selectors, BusinessService y cálculos de nómina.
    """

    selector_class = DevengoSelector
    business_service_class = DevengoBusinessService
    calculation_service_class = NominaCalculationService

    def get_qs_list(self):
        """Retorna queryset de lista usando selector."""
        empresa_id = self.get_empresa_id()
        search = self.request.query_params.get('search') if hasattr(self, 'request') else None
        empleado_id = self.request.query_params.get('empleado') if hasattr(self, 'request') else None
        periodo_mes = self.request.query_params.get('periodo_mes') if hasattr(self, 'request') else None

        if empleado_id:
            try:
                empleado_id = int(empleado_id)
            except (TypeError, ValueError):
                empleado_id = None

        return self.selector_class.get_list(
            empresa_id,
            search=search,
            empleado_id=empleado_id,
            periodo_mes=periodo_mes
        )

    def get_qs_detail(self):
        """Retorna queryset de detalle usando selector."""
        empresa_id = self.get_empresa_id()
        lookup_kwarg = getattr(self, 'lookup_url_kwarg', 'pk')
        return self.selector_class.get_detail(empresa_id, self.kwargs.get(lookup_kwarg))

    def get_historial_qs(self, empleado_id: int):
        """Retorna queryset de historial de nóminas de un empleado."""
        empresa_id = self.get_empresa_id()
        search = self.request.query_params.get('search') if hasattr(self, 'request') else None
        return self.selector_class.get_historial(empleado_id, empresa_id, search=search)

    def service_procesar_devengo(self, serializer, instance=None):
        """Procesa creación/actualización de devengo con validaciones y cálculos."""
        from apps.tenant.empleados.models import Empleado

        empresa_id = self.get_empresa_id()
        validated_data = serializer.validated_data

        empleado = validated_data.get('empleado', instance.empleado if instance else None)
        contrato = validated_data.get('contrato', instance.contrato if instance else None)

        return self.business_service_class.procesar_devengo(
            empleado=empleado,
            contrato=contrato,
            data=validated_data,
            empresa_id=empresa_id,
            instance=instance
        )

    def service_anular_devengo(self, devengo):
        """Anula un devengo."""
        empresa_id = self.get_empresa_id()
        return self.business_service_class.anular_devengo(devengo, empresa_id)

    def service_eliminar_devengo(self, devengo, *args, **kwargs):
        """Elimina un devengo."""
        empresa_id = self.get_empresa_id()
        return self.business_service_class.eliminar_devengo(devengo, empresa_id)

    def service_validar_limite_dias(self, payload=None, *args, **kwargs):
        """Valida límite de días en un mes. Soporta payload o argumentos directos."""
        empresa_id = self.get_empresa_id()
        
        if payload:
            empleado_id = payload.get('empleado')
            periodo_mes = payload.get('periodo_mes')
            dias_laborados = payload.get('dias_laborados')
            devengo_id_excluir = payload.get('id')
        else:
            empleado_id = kwargs.get('empleado_id')
            periodo_mes = kwargs.get('periodo_mes')
            dias_laborados = kwargs.get('dias_laborados')
            devengo_id_excluir = kwargs.get('devengo_id_excluir')

        return self.business_service_class.validar_limite_dias_mes(
            empleado_id=empleado_id,
            periodo_mes=periodo_mes,
            nuevos_dias=dias_laborados,
            empresa_id=empresa_id,
            devengo_id_excluir=devengo_id_excluir
        )

    def service_validar_duplicado(self, payload):
        """Valida que no exista devengo duplicado."""
        empresa_id = self.get_empresa_id()
        return self.business_service_class.validar_duplicado(
            empleado_id=payload.get('empleado'),
            periodo_mes=payload.get('periodo_mes'),
            fecha_pago=payload.get('fecha_pago'),
            empresa_id=empresa_id
        )

    def service_calcular_nomina(self, contrato, dias_laborados, **kwargs):
        """Calcula nómina usando servicio de cálculo."""
        return self.calculation_service_class.calcular_liquidacion(
            contrato=contrato,
            dias_laborados=dias_laborados,
            **kwargs
        )
