"""
API Mixins para Empleados - Inyeccion de servicios en ViewSets (v3.10.1).

SINTEL v3.10.1: Arquitectura Service Layer Modular.
- Hereda de BaseServiceMixin (canonical, consolidado)
- Mantiene solo métodos service_* específicos de Empleados
"""
from apps.tenant.api.mixins import BaseServiceMixin
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


class EmpleadoServiceMixin(BaseServiceMixin):
    """
    Service mixin para Empleado ViewSet.
    Hereda de BaseServiceMixin para get_qs_list(), get_qs_detail(), etc.
    """

    # Instancias de servicios (pueden ser sobrescritas en subclasses)
    selector_class = EmpleadoSelector
    contrato_selector = ContratoSelector
    devengo_selector = DevengoSelector
    business_service_class = EmpleadoBusinessService
    summary_selector_class = NominaSummarySelector

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
        """Elimina empleado retirado usando business service. Pasa empresa_id para DSV."""
        empresa_id = self.get_empresa_id()
        return self.business_service_class.eliminar_empleado_retirado(empleado, empresa_id=empresa_id)

    def service_get_nomina_summary(self, request):
        """Obtiene resumen de nomina usando selector."""
        empresa_id = self.get_empresa_id()
        if not empresa_id:
            return None
        return self.summary_selector_class.get_summary(empresa_id)


class ContratoServiceMixin(BaseServiceMixin):
    """
    Service mixin para Contrato ViewSet.
    Hereda de BaseServiceMixin para get_empresa_id(), etc.
    """

    selector_class = ContratoSelector
    business_service_class = ContratoBusinessService

    def get_qs_list(self):
        """Sobrescribe para agregar parámetro empleado."""
        empresa_id = self.get_empresa_id()
        search = self.request.query_params.get('search') if hasattr(self, 'request') else None
        empleado_id = self.request.query_params.get('empleado') if hasattr(self, 'request') else None
        if empleado_id:
            try:
                empleado_id = int(empleado_id)
            except (TypeError, ValueError):
                empleado_id = None
        return self.selector_class.get_list(empresa_id, search=search, empleado_id=empleado_id)

    def get_empleado_by_id(self, empleado_id):
        """Obtiene empleado por PK recibido en payload validando tenant."""
        return EmpleadoSelector.get_by_id(self.get_empresa_id(), empleado_id)

    def get_contrato_activo_for_empleado(self, empleado_id):
        """Obtiene contrato activo por empleado validando tenant."""
        return self.selector_class.get_activo_for_empleado(self.get_empresa_id(), empleado_id)

    def service_gestionar_contrato(self, empleado, data, contrato_existente=None):
        """Gestiona creacion/actualizacion de contrato."""
        return self.business_service_class.gestionar_contrato(empleado, data, contrato_existente)

    def service_preparar_datos_contrato(self, data):
        """Prepara y normaliza datos de contrato."""
        return self.business_service_class.preparar_datos_contrato(data)


class DevengoServiceMixin(BaseServiceMixin):
    """
    Service mixin para Devengo ViewSet.
    Hereda de BaseServiceMixin para get_empresa_id(), etc.
    """

    selector_class = DevengoSelector
    business_service_class = DevengoBusinessService
    calculation_service_class = NominaCalculationService

    def get_qs_list(self):
        """Sobrescribe para agregar parámetros empleado y periodo_mes."""
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

    def get_historial_qs(self, empleado_id: int):
        """Retorna queryset de historial de nominas de un empleado."""
        empresa_id = self.get_empresa_id()
        search = self.request.query_params.get('search') if hasattr(self, 'request') else None
        return self.selector_class.get_historial(empleado_id, empresa_id, search=search)

    def service_procesar_devengo(self, serializer, instance=None):
        """Procesa creacion/actualizacion de devengo con validaciones y calculos."""
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
        """Valida limite de dias en un mes. Soporta payload o argumentos directos."""
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
        """Calcula nomina usando servicio de calculo."""
        return self.calculation_service_class.calcular_liquidacion(
            contrato=contrato,
            dias_laborados=dias_laborados,
            **kwargs
        )

    def get_contrato_by_id(self, contrato_id):
        """Obtiene contrato por PK recibido en payload validando tenant."""
        return ContratoSelector.get_by_id(self.get_empresa_id(), contrato_id)

    def get_ultima_nomina_for_empleado(self, empleado_id):
        """Obtiene la ultima nomina de un empleado validando tenant."""
        return self.selector_class.get_ultima_for_empleado(self.get_empresa_id(), empleado_id)

    def exists_devengo_for_periodo(self, empleado_id, periodo_mes):
        """Valida existencia de nomina vigente en un periodo."""
        return self.selector_class.exists_for_periodo(
            self.get_empresa_id(),
            empleado_id,
            periodo_mes,
        )
