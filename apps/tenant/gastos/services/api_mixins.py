"""
API Mixins para Gastos - Inyeccion de servicios en ViewSets (v3.10.1).

SINTEL v3.10.1: Arquitectura Service Layer Modular.
- Hereda de BaseServiceMixin (canonical, consolidado)
- _get_empresa_id_seguro(), get_qs_list(), get_qs_detail(), _get_empresa() → BaseServiceMixin
- Mantiene solo métodos service_* específicos de Gastos
"""
from apps.tenant.api.mixins import BaseServiceMixin
from apps.tenant.gastos.services.selectors import (
    ResolucionSelector,
    DocumentoSelector,
)
from apps.tenant.gastos.services.business_service import (
    GastoBusinessService,
    ResolucionBusinessService,
)
from apps.tenant.gastos.services.crud_service import (
    ResolucionCRUDService,
    DocumentoCRUDService,
)


class GastoServiceMixin(BaseServiceMixin):
    """
    Service mixin para Gasto ViewSet.
    Hereda de BaseServiceMixin para get_qs_list(), get_qs_detail(), etc.
    """

    selector_class = DocumentoSelector
    business_service_class = GastoBusinessService
    crud_service_class = DocumentoCRUDService

    def service_crear_gasto(self, data, empresa):
        """Bridge para creacion de gasto desde ViewSet."""
        return self.business_service_class.procesar_gasto(empresa, data)

    def service_anular_gasto(self, gasto, motivo, usuario):
        """Anula un gasto usando business service."""
        empresa_id = self.get_empresa_id()
        return self.business_service_class.anular_gasto(gasto.id, motivo, usuario, empresa_id)

    def service_get_summary(self):
        """Obtiene resumen de gastos usando selector."""
        empresa_id = self._get_empresa_id_seguro()
        return self.selector_class.get_summary(empresa_id)


class ResolucionServiceMixin(BaseServiceMixin):
    """
    Service mixin para ResolucionDIAN ViewSet.
    Hereda de BaseServiceMixin para get_qs_list(), get_qs_detail(), etc.
    """

    selector_class = ResolucionSelector
    crud_service_class = ResolucionCRUDService
    business_service_class = ResolucionBusinessService

    def get_qs_list(self):
        """Sobrescribe para agregar parámetro vigentes."""
        empresa_id = self._get_empresa_id_seguro()
        search = self.request.query_params.get('search') if hasattr(self, 'request') else None
        solo_vigentes = self.request.query_params.get('vigentes') == 'true' if hasattr(self, 'request') else False
        return self.selector_class.get_list(empresa_id, search=search, solo_vigentes=solo_vigentes)

    def service_crear_resolucion(self, serializer):
        """Crea resolucion usando business service."""
        empresa = self._get_empresa()
        return self.business_service_class.crear_resolucion(
            data=serializer.validated_data,
            empresa=empresa
        )

    def service_desactivar_resolucion(self, resolucion):
        """Desactiva resolucion usando business service."""
        empresa_id = self.get_empresa_id()
        return self.business_service_class.desactivar_resolucion(empresa_id, resolucion.id)

    def service_obtener_vigente(self):
        """Obtiene resolucion vigente usando business service."""
        empresa_id = self._get_empresa_id_seguro()
        return self.selector_class.get_vigente(empresa_id)

    def service_obtener_siguiente_numero_soporte(self, empresa):
        """Obtiene el siguiente consecutivo para la resolucion vigente."""
        resolucion = self.service_obtener_vigente()
        if not resolucion:
            return None
        return DocumentoCRUDService._obtener_siguiente_consecutivo(resolucion)


