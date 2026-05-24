"""
API Mixins para Contabilidad - Inyección de servicios en ViewSets (v3.10.1).

SINTEL v3.10.1: Arquitectura Service Layer Modular.
- Hereda de BaseServiceMixin (canonical, consolidado)
- Mantiene solo métodos service_* específicos de Contabilidad
"""
from apps.tenant.api.mixins import BaseServiceMixin
from apps.tenant.contabilidad.services.selectors import (
    CuentaSelector,
    AsientoSelector,
    PeriodoSelector,
    MovimientoSelector,
)
from apps.tenant.contabilidad.services.business_service import (
    ContabilidadBusinessService,
)
from apps.tenant.contabilidad.services.crud_service import (
    ContabilidadCRUDService,
)


class CuentaServiceMixin(BaseServiceMixin):
    """
    Service mixin para CuentaContable ViewSet.
    Hereda de BaseServiceMixin para get_qs_list(), get_qs_detail(), etc.
    """

    selector_class = CuentaSelector
    business_service_class = ContabilidadBusinessService
    crud_service_class = ContabilidadCRUDService

    def get_qs_list(self):
        """Sobrescribe para agregar parámetro tipo."""
        empresa_id = self.get_empresa_id()
        search = self.request.query_params.get('search') if hasattr(self, 'request') else None
        tipo = self.request.query_params.get('tipo') if hasattr(self, 'request') else None
        return self.selector_class.get_list(empresa_id, search=search, tipo=tipo)


class AsientoServiceMixin(BaseServiceMixin):
    """
    Service mixin para AsientoContable ViewSet.
    Hereda de BaseServiceMixin para get_qs_list(), get_qs_detail(), etc.
    """

    selector_class = AsientoSelector
    business_service_class = ContabilidadBusinessService
    crud_service_class = ContabilidadCRUDService

    def get_qs_list(self):
        """Sobrescribe para agregar parámetro estado."""
        empresa_id = self.get_empresa_id()
        search = self.request.query_params.get('search') if hasattr(self, 'request') else None
        estado = self.request.query_params.get('estado') if hasattr(self, 'request') else None
        return self.selector_class.get_list(empresa_id, search=search, estado=estado)

    def service_crear_asiento(self, serializer):
        """Crea asiento usando business service."""
        empresa_id = self.get_empresa_id()
        return self.business_service_class.crear_asiento(
            empresa_id=empresa_id,
            data=serializer.validated_data
        )


class PeriodoServiceMixin(BaseServiceMixin):
    """
    Service mixin para PeriodoContable ViewSet.
    Hereda de BaseServiceMixin para get_qs_list(), get_qs_detail(), etc.
    """

    selector_class = PeriodoSelector
    business_service_class = ContabilidadBusinessService
    crud_service_class = ContabilidadCRUDService


class MovimientoServiceMixin(BaseServiceMixin):
    """
    Service mixin para MovimientoContable ViewSet.
    Hereda de BaseServiceMixin para get_qs_list(), get_qs_detail(), etc.
    """

    selector_class = MovimientoSelector
    crud_service_class = ContabilidadCRUDService

    def get_qs_list(self):
        """Sobrescribe para agregar parámetro asiento."""
        empresa_id = self.get_empresa_id()
        asiento_id = self.request.query_params.get('asiento') if hasattr(self, 'request') else None
        return self.selector_class.get_list(empresa_id, asiento_id=asiento_id)
