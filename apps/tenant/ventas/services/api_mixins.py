from apps.tenant.api.mixins import BaseServiceMixin
from apps.tenant.ventas.services.selectors import (
    ResolucionFacturacionSelector,
    VentaSelector,
)
from apps.tenant.ventas.services.business_service import (
    ResolucionFacturacionBusinessService,
    VentaBusinessService,
)
from apps.tenant.ventas.services.crud_service import (
    ResolucionFacturacionCRUDService,
    VentaCRUDService,
)


class VentaServiceMixin(BaseServiceMixin):
    selector_class = VentaSelector
    business_service_class = VentaBusinessService
    crud_service_class = VentaCRUDService

    def service_crear_borrador(self, empresa, payload: dict):
        return self.business_service_class.crear_venta_borrador(empresa=empresa, payload=payload)

    def service_procesar_y_facturar(self, empresa, payload: dict):
        return self.business_service_class.procesar_y_facturar_venta(empresa=empresa, payload=payload)

    def service_anular_venta(self, venta_uuid: str, empresa_id: int):
        return self.business_service_class.anular_venta(venta_uuid=venta_uuid, empresa_id=empresa_id)

    def get_qs_list(self):
        empresa_id = self._get_empresa_id_seguro()
        search = self.request.query_params.get("search") if hasattr(self, "request") else None
        estado = self.request.query_params.get("estado") if hasattr(self, "request") else None
        return self.selector_class.get_list(empresa_id, search=search, estado=estado)

    def get_qs_detail(self):
        empresa_id = self._get_empresa_id_seguro()
        venta_uuid = self.kwargs.get(self.lookup_field or "uuid")
        return self.selector_class.get_detail(empresa_id, venta_uuid)


class ResolucionFacturacionServiceMixin(BaseServiceMixin):
    selector_class = ResolucionFacturacionSelector
    business_service_class = ResolucionFacturacionBusinessService
    crud_service_class = ResolucionFacturacionCRUDService

    def service_crear_resolucion(self, empresa, payload: dict):
        return self.business_service_class.crear_resolucion(empresa=empresa, payload=payload)

    def service_actualizar_resolucion(self, resolucion_uuid: str, empresa_id: int, payload: dict):
        return self.business_service_class.actualizar_resolucion(
            resolucion_uuid=resolucion_uuid,
            empresa_id=empresa_id,
            payload=payload,
        )

    def service_eliminar_resolucion(self, resolucion_uuid: str, empresa_id: int):
        return self.business_service_class.eliminar_resolucion(
            resolucion_uuid=resolucion_uuid,
            empresa_id=empresa_id,
        )

    def get_qs_list(self):
        empresa_id = self._get_empresa_id_seguro()
        vigente_only = self.request.query_params.get("vigente") == "true" if hasattr(self, "request") else False
        return self.selector_class.get_list(empresa_id, vigente_only=vigente_only)

    def get_qs_detail(self):
        empresa_id = self._get_empresa_id_seguro()
        resolucion_uuid = self.kwargs.get(self.lookup_field or "uuid")
        return self.selector_class.get_detail(empresa_id, resolucion_uuid)
