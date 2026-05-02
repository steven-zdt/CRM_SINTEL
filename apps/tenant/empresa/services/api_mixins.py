"""
API Mixins para Empresa - Inyección de servicios en ViewSets.

WARNING: SINTEL v3.5: Arquitectura Service Layer Modular.
"""
from apps.tenant.empresa.services.selectors import (
    EmpresaSelector,
    LIST_FIELDS,
    DETAIL_FIELDS,
)
from apps.tenant.empresa.services.business_service import (
    EmpresaService,
)
from apps.tenant.empresa.services.crud_service import (
    crear_empresa_db,
    actualizar_empresa_db,
)


class EmpresaServiceMixin:
    """
    Service mixin para Empresa ViewSet.
    """

    selector_class = EmpresaSelector
    business_service_class = EmpresaService

    def get_qs_list(self):
        """Retorna queryset de lista usando selector."""
        search = self.request.query_params.get('search') if hasattr(self, 'request') else None
        return self.selector_class.get_list(search=search)

    def get_qs_detail(self):
        """Retorna queryset de detalle usando selector."""
        return self.selector_class.get_detail()

    def service_get_or_create(self, serializer):
        """Obtiene o crea empresa usando business service."""
        return self.business_service_class.get_or_create_empresa(
            data=serializer.validated_data
        )

    def service_update(self, serializer):
        """Actualiza empresa usando business service."""
        return self.business_service_class.update_empresa(
            data=serializer.validated_data
        )

    def service_has_active_profiles(self, empresa):
        """Verifica si hay perfiles activos."""
        return self.business_service_class.has_active_profiles(empresa)
