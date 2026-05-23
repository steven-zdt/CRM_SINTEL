"""
API Mixins para Cotizaciones - Inyeccion de servicios en ViewSets.
"""
from .business_service import CotizacionService
from .selectors import CotizacionSelector
from .crud_service import CotizacionCRUDService

# Re-exports desde servicios modulares
from .producto_service import ProductoServiceMixin
from .servicio_service import ServicioServiceMixin
from .item_service import CotizacionItemServiceMixin
# Configuracion se importa directamente en __init__.py desde el modulo configuracion

class CotizacionServiceMixin:
    selector_class = CotizacionSelector
    business_service_class = CotizacionService
    crud_service_class = CotizacionCRUDService

    def get_qs_list(self):
        empresa_id = self.get_empresa_id()
        search = self.request.query_params.get('search') if hasattr(self, 'request') else None
        estado = self.request.query_params.get('estado') if hasattr(self, 'request') else None
        cliente = self.request.query_params.get('cliente') if hasattr(self, 'request') else None
        return self.selector_class.get_list(empresa_id, search=search, estado=estado, cliente=cliente)

    def get_qs_detail(self):
        empresa_id = self.get_empresa_id()
        return self.selector_class.get_detail(None, empresa_id)

    def service_crear_cotizacion(self, serializer):
        from apps.tenant.empresa.models import Empresa
        empresa = Empresa.objects.filter(id=self.get_empresa_id()).only('id').first()
        return self.business_service_class.crear_preforma(
            empresa=empresa,
            datos=serializer.validated_data,
        )

    def service_actualizar_cotizacion(self, instance, serializer):
        return self.business_service_class.actualizar_cotizacion(
            instance=instance,
            datos=serializer.validated_data,
        )
