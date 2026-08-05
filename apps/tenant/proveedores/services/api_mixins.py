"""
API Mixins para Proveedores - Inyección de servicios en ViewSets (v3.10.1).

SINTEL v3.10.1: Arquitectura Service Layer Modular.
- Hereda de BaseServiceMixin (canonical, consolidado)
- Mantiene properties y service_* methods específicos de Proveedores
"""
from apps.tenant.api.mixins import BaseServiceMixin
from apps.tenant.proveedores.services.selectors import (
    ProveedorSelector,
    CuentasPagarSelector,
    RepresentanteSelector,
    LIST_FIELDS,
    DETAIL_FIELDS,
    LIST_FIELDS_REPRESENTANTE,
    DETAIL_FIELDS_REPRESENTANTE,
)
from apps.tenant.proveedores.services.business_service import (
    ProveedorBusinessService,
    CuentasPagarBusinessService,
    RepresentanteBusinessService,
)
from apps.tenant.proveedores.services.crud_service import (
    ProveedorCRUDService,
    RepresentanteCRUDService,
)


class ProveedorServiceMixin(BaseServiceMixin):
    """
    Service mixin para Proveedor ViewSet.
    Hereda de BaseServiceMixin para get_qs_list(), get_qs_detail(), etc.
    """

    selector_class = ProveedorSelector
    business_service_class = ProveedorBusinessService
    crud_service_class = ProveedorCRUDService

    @property
    def proveedor_selector(self):
        return self.selector_class()

    @property
    def proveedor_service(self):
        return self.business_service_class()

    @property
    def proveedor_crud(self):
        return self.crud_service_class()

    def get_qs_detail(self):
        """Sobrescribe para usar get_by_id en lugar de get_detail."""
        empresa_id = self.get_empresa_id()
        pk = self.kwargs.get('pk')
        return self.selector_class.get_by_id(empresa_id, pk)

    def service_crear_proveedor(self, serializer):
        """Crea proveedor usando business service."""
        return self.business_service_class.create_proveedor(
            data=serializer.validated_data
        )

    def service_actualizar_proveedor(self, serializer):
        """Actualiza proveedor usando business service."""
        return self.business_service_class.update_proveedor(
            instance=serializer.instance,
            data=serializer.validated_data
        )

    def service_obtener_snapshot(self, proveedor_uuid, tipo_documento):
        """Obtiene snapshot de proveedor."""
        empresa = self._get_empresa()
        return self.business_service_class.obtener_snapshot_proveedor(
            empresa=empresa,
            proveedor_uuid=proveedor_uuid,
            tipo_documento=tipo_documento
        )


class CuentasPagarServiceMixin:
    """
    Mixin que inyecta cuentas_pagar_selector y cuentas_pagar_service en CuentasPagarViewSet.
    Proporciona acceso al selector Zero-Waste y al business service de Cuentas por Pagar.
    """

    @property
    def cuentas_pagar_selector(self) -> CuentasPagarSelector:
        return CuentasPagarSelector()

    @property
    def cuentas_pagar_service(self):
        return CuentasPagarBusinessService()


class RepresentanteServiceMixin(BaseServiceMixin):
    """
    Service mixin para Representante ViewSet (v3.17.0).
    Inyecta selector, business service y CRUD service.
    """

    selector_class = RepresentanteSelector
    business_service_class = RepresentanteBusinessService
    crud_service_class = RepresentanteCRUDService

    @property
    def representante_selector(self):
        return self.selector_class()

    @property
    def representante_service(self):
        return self.business_service_class()

    @property
    def representante_crud(self):
        return self.crud_service_class()
