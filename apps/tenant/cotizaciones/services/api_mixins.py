"""
API Mixins para Cotizaciones - Inyeccion de servicios en ViewSets (v3.10.1).

SINTEL v3.10.1: Arquitectura Service Layer Modular.
- Hereda de BaseServiceMixin (canonical, consolidado)
- Mantiene solo métodos service_* específicos de Cotizaciones
"""
from apps.tenant.api.mixins import BaseServiceMixin
from .business_service import CotizacionService
from .selectors import CotizacionSelector
from .crud_service import CotizacionCRUDService

# Re-exports desde servicios modulares
from .producto_service import ProductoServiceMixin
from .servicio_service import ServicioServiceMixin
from .item_service import CotizacionItemServiceMixin
# Configuracion se importa directamente en __init__.py desde el modulo configuracion

class CotizacionServiceMixin(BaseServiceMixin):
    selector_class = CotizacionSelector
    business_service_class = CotizacionService
    crud_service_class = CotizacionCRUDService

    def get_qs_list(self):
        empresa_id = self.get_empresa_id()
        search = self.request.query_params.get('search') if hasattr(self, 'request') else None
        estado = self.request.query_params.get('estado') if hasattr(self, 'request') else None
        cliente = self.request.query_params.get('cliente') if hasattr(self, 'request') else None

        # [OSF Fase F7] mismo criterio de degradacion que facturas/compras:
        # si no se puede resolver un scope, no restringir (comportamiento
        # identico al de antes de esta fase).
        from apps.tenant.core.services.organizational_scope import (
            OrganizationalScope,
            OrganizationalScopeError,
        )
        try:
            sede_ids = OrganizationalScope.resolve(self.request).sede_ids
        except OrganizationalScopeError:
            sede_ids = None

        return self.selector_class.get_list(
            empresa_id, search=search, estado=estado, cliente=cliente, sede_ids=sede_ids,
        )

    def get_qs_detail(self):
        """[OSF Fase F13] Antes de esta fase no pasaba sede_ids - retrieve/
        update/exportar-pdf/render-offcanvas-*/recalcular en CotizacionViewSet
        (todos via get_object()) solo filtraban por empresa_id, mismo gap que
        F11/F13(gastos) encontraron y corrigieron."""
        from apps.tenant.core.services.organizational_scope import (
            OrganizationalScope,
            OrganizationalScopeError,
        )
        empresa_id = self.get_empresa_id()
        try:
            sede_ids = OrganizationalScope.resolve(self.request).sede_ids
        except OrganizationalScopeError:
            sede_ids = None
        return self.selector_class.get_detail(None, empresa_id, sede_ids=sede_ids)

    def service_crear_cotizacion(self, serializer):
        empresa = self._get_empresa()
        return self.business_service_class.crear_preforma(
            empresa=empresa,
            datos=serializer.validated_data,
        )

    def service_actualizar_cotizacion(self, instance, serializer):
        return self.business_service_class.actualizar_cotizacion(
            instance=instance,
            datos=serializer.validated_data,
        )
