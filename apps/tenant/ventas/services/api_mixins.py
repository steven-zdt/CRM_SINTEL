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

    def service_actualizar_venta(self, venta_uuid: str, empresa_id: int, payload: dict):
        return self.business_service_class.actualizar_venta_borrador(
            venta_uuid=venta_uuid, empresa_id=empresa_id, payload=payload,
        )

    def service_procesar_y_facturar(self, empresa, payload: dict, venta_existente=None):
        """
        [OSF Fase F10] Resuelve la sede ACTIVA del usuario (OrganizationalContext,
        no OrganizationalScope - este es un caso de "defaultear un registro
        nuevo", el mismo criterio que compras usa para OrdenCompra.sede en
        F5) y la propaga al DTO Venta->Factura via un id plano, nunca una FK
        directa Ventas->Facturas (contrato inter-app, ver
        crear_factura_desde_venta()). `VentaServiceMixin` no hereda
        SintelDSVMixin (cae al singleton) - OrganizationalContext.resolve()
        duplica el algoritmo independientemente, por eso funciona igual aqui.

        [COMERCIAL-04] `venta_existente`: pasada por
        `VentaViewSet.procesar_facturar()` cuando la operacion es sobre una
        Venta ya persistida (`{uuid}` en el URL) -- promueve esa misma fila
        en vez de crear una hermana nueva, y resuelve idempotencia real por
        `Venta.uuid`. Ver `VentaBusinessService.procesar_y_facturar_venta()`.
        """
        from apps.tenant.core.services.organizational_context import (
            OrganizationalContext,
            OrganizationalContextError,
        )
        try:
            sede_id = OrganizationalContext.resolve(self.request).sede_id
        except OrganizationalContextError:
            sede_id = None
        return self.business_service_class.procesar_y_facturar_venta(
            empresa=empresa, payload=payload, sede_id=sede_id, venta_existente=venta_existente,
        )

    def service_anular_venta(self, venta_uuid: str, empresa_id: int):
        return self.business_service_class.anular_venta(venta_uuid=venta_uuid, empresa_id=empresa_id)

    def service_eliminar_venta_sincronizada(self, venta_uuid: str, empresa_id: int):
        """PLAN_SINCRONIZACION_FACTURAS_VENTAS_FASES: elimina una Venta
        creada/vinculada por sincronizacion (nunca la Factura origen)."""
        return self.business_service_class.eliminar_venta_sincronizada(
            venta_uuid=venta_uuid, empresa_id=empresa_id,
        )

    def service_vincular_factura_existente(self, venta, factura_uuid: str, empresa_id: int):
        """FACTURAS-UI-CRONO-01: vinculacion manual de una Factura ya
        persistida (naturaleza VENTA) -- nunca crea/emite una Factura."""
        return self.business_service_class.vincular_factura_existente(
            venta=venta, factura_uuid=factura_uuid, empresa_id=empresa_id,
        )

    def service_actualizar_gestion_pago(self, venta, data: dict, empresa_id: int):
        """Integracion Facturas<->Ventas: pass-through de Gestion Manual de
        Pago hacia la Factura vinculada (SSoT sigue siendo Factura)."""
        return self.business_service_class.actualizar_gestion_pago(
            venta=venta, data=data, empresa_id=empresa_id,
        )

    def service_listar_pendientes_sincronizacion(self, empresa_id: int, search: str | None = None):
        """PLAN_SINCRONIZACION_FACTURAS_VENTAS_FASES: Facturas naturaleza
        VENTA (FE) sin Venta comercial vinculada aun."""
        from apps.tenant.ventas.services.business_service import FacturaVentaSyncService
        return FacturaVentaSyncService.listar_pendientes(empresa_id, search=search)

    def service_sincronizar_facturas(self, factura_uuids: list, empresa_id: int, empresa):
        """PLAN_SINCRONIZACION_FACTURAS_VENTAS_FASES: vincula (o crea) Venta
        comercial para cada Factura pendiente, unitaria o masivamente."""
        from apps.tenant.ventas.services.business_service import FacturaVentaSyncService
        return FacturaVentaSyncService.sincronizar_masivo(factura_uuids, empresa_id, empresa)

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
