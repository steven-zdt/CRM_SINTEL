"""
API Mixins para Empleados - Inyeccion de servicios en ViewSets (v3.10.1).

SINTEL v3.10.1: Arquitectura Service Layer Modular.
- Hereda de BaseServiceMixin (canonical, consolidado)
- Mantiene solo métodos service_* específicos de Empleados
"""
from apps.tenant.api.mixins import BaseServiceMixin
from apps.tenant.empleados.models import Empleado
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

    def get_qs_list(self):
        """[OSF Fase F7] Sobrescribe BaseServiceMixin.get_qs_list() (que no
        pasa sede_ids/area_ids) para filtrar scope-aware, mismo criterio de
        degradacion que facturas/cotizaciones/gastos/inventario/proyectos."""
        from apps.tenant.core.services.organizational_scope import (
            OrganizationalScope,
            OrganizationalScopeError,
        )

        empresa_id = self._get_empresa_id_seguro()
        search = self.request.query_params.get('search') if hasattr(self, 'request') else None
        try:
            scope = OrganizationalScope.resolve(self.request)
            sede_ids, area_ids = scope.sede_ids, scope.area_ids
        except OrganizationalScopeError:
            sede_ids, area_ids = None, None
        return self.selector_class.get_list(
            empresa_id, search=search, sede_ids=sede_ids, area_ids=area_ids,
        )

    def get_qs_detail(self):
        """[OSF Fase F13] Sobrescribe BaseServiceMixin.get_qs_detail() (que no
        pasa sede_ids/area_ids) para que retrieve/update/partial_update/
        destroy respeten el mismo alcance organizacional que get_qs_list()
        (F7) - mismo gap que F11/F13(gastos/cotizaciones/inventario/proyectos)
        encontraron y corrigieron."""
        from apps.tenant.core.services.organizational_scope import (
            OrganizationalScope,
            OrganizationalScopeError,
        )

        empresa_id = self._get_empresa_id_seguro()
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field or 'pk'
        lookup_value = self.kwargs.get(lookup_url_kwarg)
        try:
            scope = OrganizationalScope.resolve(self.request)
            sede_ids, area_ids = scope.sede_ids, scope.area_ids
        except OrganizationalScopeError:
            sede_ids, area_ids = None, None
        return self.selector_class.get_detail(empresa_id, lookup_value, sede_ids=sede_ids, area_ids=area_ids)

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
        """
        Valida que no exista devengo duplicado.

        WARNING [mision auditoria nomina "sincronizacion backend<->frontend",
        2026-09-10]: bug real encontrado al auditar el contrato JSON con un
        POST real -- este pre-check (corre ANTES de que el serializer
        resuelva el FK) asumia que 'empleado' siempre venia como PK entero,
        y crasheaba con un ValueError interno filtrado al usuario
        ("Field 'id' expected a number but got '<uuid>'") si se enviaba UUID
        -- la forma correcta segun AGENTS.md Sec.14 y lo que
        UUIDOrPKRelatedField acepta explicitamente. Se resuelve aqui el
        mismo UUID-o-PK que el serializer resolveria, ANTES de filtrar.
        """
        empresa_id = self.get_empresa_id()
        empleado_id = self._resolver_empleado_id(payload.get('empleado'), empresa_id)
        return self.business_service_class.validar_duplicado(
            empleado_id=empleado_id,
            periodo_mes=payload.get('periodo_mes'),
            fecha_pago=payload.get('fecha_pago'),
            empresa_id=empresa_id
        )

    @staticmethod
    def _resolver_empleado_id(valor, empresa_id):
        """UUID-o-PK -> PK entero (o None si no resuelve), mismo criterio de
        deteccion que UUIDOrPKRelatedField.to_internal_value() (serializers.py):
        '-' presente y no son puros digitos => es UUID."""
        if valor is None or valor == '':
            return None
        valor_str = str(valor).strip()
        if '-' in valor_str and not valor_str.isdigit():
            return Empleado.objects.filter(
                empresa_id=empresa_id, uuid=valor_str
            ).values_list('id', flat=True).first()
        try:
            return int(valor_str)
        except (TypeError, ValueError):
            return None

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
