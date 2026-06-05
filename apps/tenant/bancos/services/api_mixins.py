from apps.tenant.api.mixins import BaseServiceMixin
from apps.tenant.bancos.services.selectors import (
    CuentaBancariaSelector,
    ExtractoBancarioSelector,
    TransaccionBancariaSelector,
)
from apps.tenant.bancos.services.crud_service import (
    CuentaBancariaCRUDService,
    ExtractoBancarioCRUDService,
    TransaccionBancariaCRUDService,
)
from apps.tenant.bancos.services.business_service import (
    ExtractoBancarioBusinessService,
)

class CuentaBancariaServiceMixin(BaseServiceMixin):
    """Bridge service methods for CuentaBancaria ViewSet."""
    selector_class = CuentaBancariaSelector
    crud_service_class = CuentaBancariaCRUDService

    def get_qs_list(self):
        empresa_id = self._get_empresa_id_seguro()
        search = self.request.query_params.get("search") if hasattr(self, "request") else None
        return self.selector_class.get_list(empresa_id, search=search)

    def get_qs_detail(self):
        empresa_id = self._get_empresa_id_seguro()
        return self.selector_class.get_detail(empresa_id)

    def service_crear_cuenta(self, data):
        empresa = self._get_empresa()
        return self.crud_service_class.crear_cuenta(data, empresa)

    def service_editar_cuenta(self, cuenta, data):
        return self.crud_service_class.editar_cuenta(cuenta, data)

    def service_eliminar_cuenta(self, cuenta):
        return self.crud_service_class.eliminar_cuenta(cuenta)

class ExtractoBancarioServiceMixin(BaseServiceMixin):
    """Bridge service methods for ExtractoBancario ViewSet."""
    selector_class = ExtractoBancarioSelector
    crud_service_class = ExtractoBancarioCRUDService
    business_service_class = ExtractoBancarioBusinessService

    def get_qs_list(self):
        empresa_id = self._get_empresa_id_seguro()
        cuenta_uuid = self.request.query_params.get("cuenta_uuid") if hasattr(self, "request") else None
        search = self.request.query_params.get("search") if hasattr(self, "request") else None
        return self.selector_class.get_list(empresa_id, cuenta_uuid=cuenta_uuid, search=search)

    def get_qs_detail(self):
        empresa_id = self._get_empresa_id_seguro()
        return self.selector_class.get_detail(empresa_id)

    def service_crear_extracto(self, data):
        empresa = self._get_empresa()
        return self.crud_service_class.crear_extracto(data, empresa)

    def service_editar_extracto(self, extracto, data):
        return self.crud_service_class.editar_extracto(extracto, data)

    def service_eliminar_extracto(self, extracto):
        return self.crud_service_class.eliminar_extracto(extracto)

    def service_procesar_extracto(self, extracto):
        return self.business_service_class.procesar_archivo_extracto(extracto)

class TransaccionBancariaServiceMixin(BaseServiceMixin):
    """Bridge service methods for TransaccionBancaria ViewSet."""
    selector_class = TransaccionBancariaSelector
    crud_service_class = TransaccionBancariaCRUDService

    def get_qs_list(self):
        empresa_id = self._get_empresa_id_seguro()
        extracto_uuid = self.request.query_params.get("extracto_uuid") if hasattr(self, "request") else None
        search = self.request.query_params.get("search") if hasattr(self, "request") else None
        tipo_movimiento = self.request.query_params.get("tipo_movimiento") if hasattr(self, "request") else None
        conciliado = self.request.query_params.get("conciliado") if hasattr(self, "request") else None
        return self.selector_class.get_list(
            empresa_id,
            extracto_uuid=extracto_uuid,
            search=search,
            tipo_movimiento=tipo_movimiento,
            conciliado=conciliado,
        )

    def get_qs_detail(self):
        empresa_id = self._get_empresa_id_seguro()
        return self.selector_class.get_detail(empresa_id)

    def service_conciliar_transaccion(self, transaccion, data: dict):
        return self.crud_service_class.conciliar_transaccion(transaccion, data)
