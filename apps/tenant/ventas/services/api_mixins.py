"""
API Mixins para Ventas - Inyeccion de servicios en ViewSets (v3.10.5).

Hereda de BaseServiceMixin (canonical).
Mantiene solo metodos service_* especificos de Ventas.
"""
from apps.tenant.api.mixins import BaseServiceMixin
from apps.tenant.ventas.services.selectors import OrdenVentaSelector
from apps.tenant.ventas.services.business_service import OrdenVentaBusinessService
from apps.tenant.ventas.services.crud_service import OrdenVentaCRUDService


class OrdenVentaServiceMixin(BaseServiceMixin):
    """
    Service mixin para OrdenVentaViewSet.
    Hereda de BaseServiceMixin para get_qs_list(), get_qs_detail(), etc.
    """

    selector_class = OrdenVentaSelector
    business_service_class = OrdenVentaBusinessService
    crud_service_class = OrdenVentaCRUDService

    def service_crear_orden(self, data: dict, empresa):
        """Bridge para creacion de orden desde ViewSet."""
        return self.business_service_class.crear_orden(empresa=empresa, data=data)

    def service_actualizar_orden(self, orden, data: dict, empresa):
        """Bridge para actualizacion de orden desde ViewSet."""
        return self.business_service_class.actualizar_orden(
            empresa=empresa,
            orden=orden,
            data=data,
        )

    def service_confirmar_orden(self, orden):
        """Confirma la orden (BORRADOR -> CONFIRMADA)."""
        empresa_id = self.get_empresa_id()
        return self.business_service_class.confirmar_orden(orden, empresa_id)

    def service_generar_factura(self, orden):
        """Genera factura electronica a partir de la orden."""
        empresa_id = self.get_empresa_id()
        return self.business_service_class.generar_factura(orden, empresa_id)

    def service_anular_orden(self, orden, motivo: str):
        """Anula la orden con motivo."""
        empresa_id = self.get_empresa_id()
        return self.business_service_class.anular_orden(orden, empresa_id, motivo)

    def get_qs_list(self):
        """Retorna queryset de lista con soporte de busqueda."""
        empresa_id = self._get_empresa_id_seguro()
        search = self.request.query_params.get("search") if hasattr(self, "request") else None
        return self.selector_class.get_list(empresa_id, search=search)

    def get_qs_detail(self):
        """Retorna queryset de detalle filtrado por uuid."""
        empresa_id = self._get_empresa_id_seguro()
        orden_uuid = self.kwargs.get(self.lookup_field or "uuid")
        return self.selector_class.get_detail(empresa_id, orden_uuid)
