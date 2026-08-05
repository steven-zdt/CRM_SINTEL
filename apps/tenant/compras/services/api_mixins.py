from rest_framework.exceptions import ValidationError
from apps.tenant.api.mixins import BaseServiceMixin
from apps.tenant.compras.services.selectors import OrdenCompraSelector, PlantillaOrdenCompraSelector
from apps.tenant.compras.services.crud_service import OrdenCompraCRUDService, PlantillaOrdenCompraCRUDService
from apps.tenant.compras.services.business_service import OrdenCompraBusinessService


class PlantillaOrdenCompraServiceMixin(BaseServiceMixin):
    """
    Mixin para inyectar logica de negocios y acceso a datos de Plantillas de Orden de Compra
    en los ViewSets correspondientes.
    """
    selector_class = PlantillaOrdenCompraSelector
    crud_service_class = PlantillaOrdenCompraCRUDService

    def get_qs_list(self, vigente_only: bool = False):
        empresa_id = self._get_empresa_id_seguro()
        return self.selector_class.get_list(empresa_id, vigente_only=vigente_only)

    def get_qs_detail(self, plantilla_uuid: str):
        empresa_id = self._get_empresa_id_seguro()
        return self.selector_class.get_detail(empresa_id, plantilla_uuid)

    def service_crear_plantilla(self, empresa, data: dict):
        """
        Crea una plantilla usando el CRUD service.
        """
        return self.crud_service_class.crear_plantilla(empresa, data)

    def service_actualizar_plantilla(self, plantilla_uuid: str, data: dict):
        """
        Actualiza una plantilla existente.
        """
        empresa_id = self._get_empresa_id_seguro()
        plantilla = self.selector_class.get_detail(empresa_id, plantilla_uuid).first()
        if not plantilla:
            raise ValidationError({"plantilla": "Plantilla no encontrada o no pertenece a su empresa."})
        return self.crud_service_class.actualizar_plantilla(plantilla, data)


class OrdenCompraServiceMixin(BaseServiceMixin):
    """
    Mixin para inyectar logica de negocios y acceso a datos de Ordenes de Compra
    en los ViewSets correspondientes.
    """
    selector_class = OrdenCompraSelector
    crud_service_class = OrdenCompraCRUDService
    business_service_class = OrdenCompraBusinessService

    def service_crear_orden_compra(self, data: dict, items_data: list, empresa):
        """
        Orquesta la creacion de la Orden de Compra desde el ViewSet.
        """
        return self.business_service_class.crear_orden_compra(data, items_data, empresa)

    def service_actualizar_orden_compra(self, orden_uuid: str, data: dict, items_data: list = None):
        """
        Orquesta la actualizacion de la Orden de Compra y sus items desde el ViewSet.
        """
        empresa_id = self._get_empresa_id_seguro()
        return self.business_service_class.actualizar_orden_compra(
            orden_uuid, data, items_data, empresa_id
        )

    def service_cambiar_estado(self, orden_uuid: str, nuevo_estado: str):
        """
        Cambia el estado de una Orden de Compra.
        """
        empresa_id = self._get_empresa_id_seguro()
        return self.business_service_class.cambiar_estado_orden_compra(
            orden_uuid, nuevo_estado, empresa_id
        )

    def service_eliminar_orden_compra(self, orden_uuid: str):
        """
        Elimina fisicamente una Orden de Compra en estado Borrador.
        """
        empresa_id = self._get_empresa_id_seguro()
        return self.business_service_class.eliminar_orden_compra(orden_uuid, empresa_id)

    def service_get_siguiente_consecutivo(self) -> int:
        """
        Obtiene el consecutivo siguiente para la empresa actual.
        """
        empresa_id = self._get_empresa_id_seguro()
        return self.selector_class.get_siguiente_consecutivo(empresa_id)
