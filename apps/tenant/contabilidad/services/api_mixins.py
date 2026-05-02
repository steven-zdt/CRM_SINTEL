"""
API Mixins para Contabilidad - Inyección de servicios en ViewSets.

WARNING: SINTEL v3.5: Arquitectura Service Layer Modular.
- Este archivo contiene mixins específicos para cada modelo.
- Inyectan acceso estandarizado a Selectors, CRUDService y BusinessService.
- Usan get_empresa_id() de SintelDSVMixin para Zero Trust.
"""
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


class CuentaServiceMixin:
    """
    Service mixin para CuentaContable ViewSet.
    Inyecta acceso a Selectors y BusinessService.
    Requiere que el ViewSet herede de SintelDSVMixin (para get_empresa_id).
    """

    selector_class = CuentaSelector
    business_service_class = ContabilidadBusinessService
    crud_service_class = ContabilidadCRUDService

    def get_qs_list(self):
        """Retorna queryset de lista usando selector."""
        empresa_id = self.get_empresa_id()
        search = self.request.query_params.get('search') if hasattr(self, 'request') else None
        tipo = self.request.query_params.get('tipo') if hasattr(self, 'request') else None
        return self.selector_class.get_list(empresa_id, search=search, tipo=tipo)

    def get_qs_detail(self):
        """Retorna queryset de detalle usando selector."""
        empresa_id = self.get_empresa_id()
        return self.selector_class.get_detail(empresa_id, self.kwargs.get('pk'))


class AsientoServiceMixin:
    """
    Service mixin para AsientoContable ViewSet.
    """

    selector_class = AsientoSelector
    business_service_class = ContabilidadBusinessService
    crud_service_class = ContabilidadCRUDService

    def get_qs_list(self):
        """Retorna queryset de lista usando selector."""
        empresa_id = self.get_empresa_id()
        search = self.request.query_params.get('search') if hasattr(self, 'request') else None
        estado = self.request.query_params.get('estado') if hasattr(self, 'request') else None
        return self.selector_class.get_list(empresa_id, search=search, estado=estado)

    def get_qs_detail(self):
        """Retorna queryset de detalle usando selector."""
        empresa_id = self.get_empresa_id()
        return self.selector_class.get_detail(empresa_id, self.kwargs.get('pk'))

    def service_crear_asiento(self, serializer):
        """Crea asiento usando business service."""
        empresa_id = self.get_empresa_id()
        return self.business_service_class.crear_asiento(
            empresa_id=empresa_id,
            data=serializer.validated_data
        )


class PeriodoServiceMixin:
    """
    Service mixin para PeriodoContable ViewSet.
    """

    selector_class = PeriodoSelector
    business_service_class = ContabilidadBusinessService
    crud_service_class = ContabilidadCRUDService

    def get_qs_list(self):
        """Retorna queryset de lista usando selector."""
        empresa_id = self.get_empresa_id()
        return self.selector_class.get_list(empresa_id)

    def get_qs_detail(self):
        """Retorna queryset de detalle usando selector."""
        empresa_id = self.get_empresa_id()
        return self.selector_class.get_detail(empresa_id, self.kwargs.get('pk'))


class MovimientoServiceMixin:
    """
    Service mixin para MovimientoContable ViewSet.
    """

    selector_class = MovimientoSelector
    crud_service_class = ContabilidadCRUDService

    def get_qs_list(self):
        """Retorna queryset de lista usando selector."""
        empresa_id = self.get_empresa_id()
        asiento_id = self.request.query_params.get('asiento') if hasattr(self, 'request') else None
        return self.selector_class.get_list(empresa_id, asiento_id=asiento_id)

    def get_qs_detail(self):
        """Retorna queryset de detalle usando selector."""
        empresa_id = self.get_empresa_id()
        return self.selector_class.get_detail(empresa_id, self.kwargs.get('pk'))
