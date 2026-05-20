"""
API Mixins para Proveedores - Inyección de servicios en ViewSets.

WARNING: SINTEL v3.5: Arquitectura Service Layer Modular.
- Este archivo contiene mixins específicos para cada modelo.
- Inyectan acceso estandarizado a Selectors, CRUDService y BusinessService.
- Usan get_empresa_id() de SintelDSVMixin para Zero Trust.
"""
from apps.tenant.proveedores.services.selectors import (
    ProveedorSelector,
    LIST_FIELDS,
    DETAIL_FIELDS,
)
from apps.tenant.proveedores.services.business_service import (
    ProveedorBusinessService,
)
from apps.tenant.proveedores.services.crud_service import (
    ProveedorCRUDService,
)


class ProveedorServiceMixin:
    """
    Service mixin para Proveedor ViewSet.
    Inyecta acceso a Selectors y BusinessService.
    Requiere que el ViewSet herede de SintelDSVMixin (para get_empresa_id).
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


    def get_qs_list(self):
        """Retorna queryset de lista usando selector."""
        empresa_id = self.get_empresa_id()
        search = self.request.query_params.get('search') if hasattr(self, 'request') else None
        return self.selector_class.get_list(empresa_id, search=search)

    def get_qs_detail(self):
        """Retorna queryset de detalle usando selector."""
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

    def _get_empresa(self):
        """Helper para obtener empresa actual."""
        from apps.tenant.empresa.models import Empresa
        empresa_id = self.get_empresa_id()
        return Empresa.objects.filter(id=empresa_id).first()
