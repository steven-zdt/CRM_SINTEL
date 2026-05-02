"""
API Mixins para Cotizaciones - Inyección de servicios en ViewSets.

WARNING: SINTEL v3.5: Arquitectura Service Layer Modular.
"""
from apps.tenant.cotizaciones.services.selectors import (
    CotizacionSelector,
    CotizacionItemSelector,
)
from apps.tenant.cotizaciones.services.business_service import CotizacionService
from apps.tenant.cotizaciones.services.crud_service import CotizacionCRUDService


class CotizacionServiceMixin:
    """
    Service mixin para Cotizacion ViewSet.
    """

    selector_class = CotizacionSelector
    business_service_class = CotizacionService
    crud_service_class = CotizacionCRUDService

    def get_qs_list(self):
        """Retorna queryset de lista usando selector."""
        empresa_id = self.get_empresa_id()
        search = self.request.query_params.get('search') if hasattr(self, 'request') else None
        estado = self.request.query_params.get('estado') if hasattr(self, 'request') else None
        cliente = self.request.query_params.get('cliente') if hasattr(self, 'request') else None
        return self.selector_class.get_list(empresa_id, search=search, estado=estado, cliente=cliente)

    def get_qs_detail(self):
        """Retorna queryset de detalle usando selector."""
        empresa_id = self.get_empresa_id()
        return self.selector_class.get_detail(None, empresa_id)

    def service_crear_cotizacion(self, serializer):
        """Crea cotizacion usando business service."""
        from apps.tenant.empresa.models import Empresa
        empresa = Empresa.objects.filter(id=self.get_empresa_id()).only('id').first()
        return self.business_service_class.crear_preforma(
            empresa=empresa,
            datos=serializer.validated_data,
        )


class CotizacionItemServiceMixin:
    """
    Service mixin para CotizacionItem ViewSet.
    """

    selector_class = CotizacionItemSelector
    crud_service_class = CotizacionCRUDService

    def get_qs_list(self):
        """Retorna queryset de lista usando selector."""
        empresa_id = self.get_empresa_id()
        cotizacion_id = self.request.query_params.get('cotizacion') if hasattr(self, 'request') else None
        return self.selector_class.get_list(cotizacion_id, empresa_id)

    def get_qs_detail(self):
        """Retorna queryset de detalle usando selector."""
        empresa_id = self.get_empresa_id()
        pk = self.kwargs.get('pk')
        return self.selector_class.get_detail(pk, empresa_id)
