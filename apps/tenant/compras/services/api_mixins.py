from rest_framework.exceptions import ValidationError

from apps.tenant.api.mixins import BaseServiceMixin
from apps.tenant.compras.services.business_service import (
    OrdenCompraBusinessService,
    RecepcionCompraBusinessService,
)
from apps.tenant.compras.services.crud_service import (
    OrdenCompraCRUDService,
    PlantillaOrdenCompraCRUDService,
    RecepcionCompraCRUDService,
)
from apps.tenant.compras.services.selectors import (
    OrdenCompraSelector,
    PlantillaOrdenCompraSelector,
    RecepcionCompraSelector,
)


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

    def get_qs_list(self):
        """
        [OSF Fase F5] Filtra por el conjunto COMPLETO de sedes/areas
        permitidas (OrganizationalScope), no por una sola "sede activa": un
        perfil con alcance SEDE/AREA asignado a varias sedes/areas debe ver
        las ordenes de TODAS las suyas, no solo de la activa. Hallazgo real
        de F4/F5: la version anterior de este metodo (una sola sede activa,
        via `_get_sede_id_seguro()`) ocultaba ordenes de las demas sedes
        asignadas, y nunca filtraba por area en absoluto para alcance=AREA.
        Un perfil con alcance EMPRESA (o sin tenant_profile, ej. fallback
        DEBUG) sigue viendo todas las sedes/areas de la empresa, igual que
        antes. Reemplaza BaseServiceMixin.get_qs_list() solo para este
        ViewSet - no cambia el comportamiento por defecto de las otras 16
        apps.

        `OrganizationalScope.resolve()` es MAS estricto que
        `_get_empresa_id_seguro()` (que ya usamos arriba): sin
        tenant_profile y fuera de DEBUG, `_get_empresa_id_seguro()` cae al
        singleton de empresa sin condicion, mientras que
        OrganizationalScope.resolve() exige DEBUG para ese mismo fallback y
        lanza OrganizationalScopeError si no. Se captura explicitamente para
        no convertir un request que hoy funciona (sin perfil, produccion,
        via singleton) en un 500 - se degrada a "sin restriccion", el mismo
        comportamiento que el `perfil is None` de la version anterior.
        """
        from apps.tenant.core.services.organizational_scope import (
            OrganizationalScope,
            OrganizationalScopeError,
        )

        empresa_id = self._get_empresa_id_seguro()
        search = self.request.query_params.get('search') if hasattr(self, 'request') else None

        try:
            scope = OrganizationalScope.resolve(self.request)
            sede_ids, area_ids = scope.sede_ids, scope.area_ids
        except OrganizationalScopeError:
            sede_ids, area_ids = None, None

        return self.selector_class.get_list(
            empresa_id, search=search, sede_ids=sede_ids, area_ids=area_ids,
        )

    def service_crear_orden_compra(self, data: dict, items_data: list, empresa):
        """
        Orquesta la creacion de la Orden de Compra desde el ViewSet.

        [ADR-003] `sede` se resuelve aqui (via _get_sede(), heredado de
        BaseServiceMixin) y se pasa explicita al business service - nunca se
        re-deriva dentro de business_service.py/crud_service.py.
        """
        sede = self._get_sede()
        return self.business_service_class.crear_orden_compra(data, items_data, empresa, sede)

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


class RecepcionCompraServiceMixin(BaseServiceMixin):
    """Mixin para inyectar logica de negocios de Recepcion de Compras (F21)."""
    selector_class = RecepcionCompraSelector
    crud_service_class = RecepcionCompraCRUDService
    business_service_class = RecepcionCompraBusinessService

    def get_qs_list(self, orden_compra_uuid: str = None, estado: str = None):
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
        return self.selector_class.get_list(
            empresa_id, orden_compra_uuid=orden_compra_uuid, estado=estado,
            sede_ids=sede_ids, area_ids=area_ids,
        )

    def get_qs_detail(self, recepcion_uuid: str):
        empresa_id = self._get_empresa_id_seguro()
        return self.selector_class.get_detail(empresa_id, recepcion_uuid)

    def service_crear_recepcion(self, data: dict, items_data: list, empresa):
        sede = self._get_sede()
        usuario = getattr(self.request.user, 'tenant_profile', None)
        return self.business_service_class.crear_recepcion(data, items_data, empresa, sede, usuario)

    def service_confirmar_recepcion(self, recepcion_uuid: str):
        empresa_id = self._get_empresa_id_seguro()
        return self.business_service_class.confirmar_recepcion(recepcion_uuid, empresa_id)

    def service_anular_recepcion(self, recepcion_uuid: str):
        empresa_id = self._get_empresa_id_seguro()
        return self.business_service_class.anular_recepcion(recepcion_uuid, empresa_id)
