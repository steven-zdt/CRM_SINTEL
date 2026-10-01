from apps.tenant.api.mixins import BaseServiceMixin
from apps.tenant.compras.requisiciones.services.business_service import (
    RequisicionCompraBusinessService,
)
from apps.tenant.compras.requisiciones.services.crud_service import RequisicionCompraCRUDService
from apps.tenant.compras.requisiciones.services.selectors import RequisicionCompraSelector


class RequisicionCompraServiceMixin(BaseServiceMixin):
    """Mixin para inyectar logica de negocio y acceso a datos de
    RequisicionCompra en el ViewSet (mismo patron que
    OrdenCompraServiceMixin en apps.tenant.compras.services.api_mixins)."""

    selector_class = RequisicionCompraSelector
    crud_service_class = RequisicionCompraCRUDService
    business_service_class = RequisicionCompraBusinessService

    def get_qs_list(self):
        from apps.tenant.core.services.organizational_scope import (
            OrganizationalScope,
            OrganizationalScopeError,
        )

        empresa_id = self._get_empresa_id_seguro()
        search = self.request.query_params.get("search") if hasattr(self, "request") else None
        estado = self.request.query_params.get("estado") if hasattr(self, "request") else None

        try:
            scope = OrganizationalScope.resolve(self.request)
            sede_ids, area_ids = scope.sede_ids, scope.area_ids
        except OrganizationalScopeError:
            sede_ids, area_ids = None, None

        return self.selector_class.get_list(
            empresa_id,
            search=search,
            estado=estado,
            sede_ids=sede_ids,
            area_ids=area_ids,
        )

    def get_qs_detail(self, requisicion_uuid: str):
        empresa_id = self._get_empresa_id_seguro()
        return self.selector_class.get_detail(empresa_id, requisicion_uuid)

    def service_crear_requisicion(self, data: dict, items_data: list, empresa):
        sede = self._get_sede()
        solicitante = getattr(self.request.user, "tenant_profile", None)
        return self.business_service_class.crear_requisicion(
            data, items_data, empresa, sede, solicitante
        )

    def service_actualizar_requisicion(
        self, requisicion_uuid: str, data: dict, items_data: list = None
    ):
        empresa_id = self._get_empresa_id_seguro()
        return self.business_service_class.actualizar_requisicion(
            requisicion_uuid, data, items_data, empresa_id
        )

    def service_eliminar_requisicion(self, requisicion_uuid: str):
        empresa_id = self._get_empresa_id_seguro()
        return self.business_service_class.eliminar_requisicion(requisicion_uuid, empresa_id)

    def service_enviar_a_aprobacion(self, requisicion_uuid: str):
        empresa_id = self._get_empresa_id_seguro()
        usuario = getattr(self.request.user, "tenant_profile", None)
        return self.business_service_class.enviar_a_aprobacion(
            requisicion_uuid, empresa_id, usuario
        )

    def service_aprobar_requisicion(self, requisicion_uuid: str, comentario: str = ""):
        empresa_id = self._get_empresa_id_seguro()
        usuario = getattr(self.request.user, "tenant_profile", None)
        return self.business_service_class.aprobar_requisicion(
            requisicion_uuid, empresa_id, usuario, comentario
        )

    def service_rechazar_requisicion(self, requisicion_uuid: str, motivo: str):
        empresa_id = self._get_empresa_id_seguro()
        usuario = getattr(self.request.user, "tenant_profile", None)
        return self.business_service_class.rechazar_requisicion(
            requisicion_uuid, empresa_id, motivo, usuario
        )

    def service_cancelar_requisicion(self, requisicion_uuid: str, motivo: str = ""):
        empresa_id = self._get_empresa_id_seguro()
        usuario = getattr(self.request.user, "tenant_profile", None)
        return self.business_service_class.cancelar_requisicion(
            requisicion_uuid, empresa_id, motivo, usuario
        )

    def service_vincular_cotizacion(self, requisicion_uuid: str, cotizacion_uuid: str, **kwargs):
        empresa_id = self._get_empresa_id_seguro()
        return self.business_service_class.vincular_cotizacion(
            requisicion_uuid, cotizacion_uuid, empresa_id, **kwargs
        )

    def service_vincular_factura(self, requisicion_uuid: str, factura_uuid: str, **kwargs):
        empresa_id = self._get_empresa_id_seguro()
        return self.business_service_class.vincular_factura(
            requisicion_uuid, factura_uuid, empresa_id, **kwargs
        )

    def service_crear_orden_desde_requisicion(
        self, requisicion_uuid: str, oc_data: dict, items_ordenados: list, empresa
    ):
        empresa_id = self._get_empresa_id_seguro()
        sede = self._get_sede()
        return self.business_service_class.crear_orden_desde_requisicion(
            requisicion_uuid,
            oc_data,
            items_ordenados,
            empresa,
            sede,
            empresa_id,
        )

    def service_adjuntar_documento(self, requisicion_uuid: str, data: dict):
        empresa_id = self._get_empresa_id_seguro()
        return self.business_service_class.adjuntar_documento(requisicion_uuid, empresa_id, data)

    def service_sincronizar_trazabilidad_proyecto(self, requisicion_uuid: str):
        empresa_id = self._get_empresa_id_seguro()
        return self.business_service_class.sincronizar_trazabilidad_proyecto(
            requisicion_uuid, empresa_id
        )

    def service_get_siguiente_consecutivo(self) -> int:
        empresa_id = self._get_empresa_id_seguro()
        return self.selector_class.get_siguiente_consecutivo(empresa_id)

    def service_get_disponibles_para_orden(self):
        """Fase 7 del plan (#32): Requisiciones que pueden vincularse a una
        nueva/existente Orden de Compra. Mismo criterio de scope que
        get_qs_list()."""
        from apps.tenant.core.services.organizational_scope import (
            OrganizationalScope,
            OrganizationalScopeError,
        )

        empresa_id = self._get_empresa_id_seguro()
        try:
            scope = OrganizationalScope.resolve(self.request)
            sede_ids, area_ids = scope.sede_ids, scope.area_ids
        except OrganizationalScopeError:
            sede_ids, area_ids = None, None

        return self.selector_class.get_available_for_purchase(
            empresa_id, sede_ids=sede_ids, area_ids=area_ids
        )
