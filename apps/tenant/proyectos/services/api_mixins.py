"""
API Mixins para Proyectos v3.5 - Inyeccion de servicios en ViewSets.

WARNING: SINTEL v3.5: Arquitectura Service Layer Modular.
- Inyecta acceso estandarizado a Selectors, CRUDService y BusinessService.
- Usa get_empresa_id() de SintelDSVMixin para Zero Trust.
"""
from apps.tenant.proyectos.services.selectors import (
    LIST_FIELDS,
    DETAIL_FIELDS,
    qs_list,
    qs_detail,
)
from apps.tenant.proyectos.services.business_service import (
    orchestrate_create_proyecto,
    orchestrate_update_proyecto,
    calcular_indicadores_financieros,
)
from apps.tenant.proyectos.services.crud_service import (
    save_proyecto,
    delete_proyecto,
)


class ProyectoServiceMixin:
    """
    Service mixin para Proyecto ViewSet.
    Inyecta acceso a Selectors y BusinessService.
    Requiere que el ViewSet herede de SintelDSVMixin (para get_empresa_id).
    """

    def get_qs_list(self):
        """Retorna queryset de lista usando selector."""
        empresa_id = self.get_empresa_id()
        search = self.request.query_params.get('search') if hasattr(self, 'request') else None
        return qs_list(empresa_id, search=search)

    def get_qs_detail(self):
        """Retorna instancia de detalle usando selector."""
        empresa_id = self.get_empresa_id()
        pk = self.kwargs.get('pk')
        return qs_detail(empresa_id, pk)

    def service_crear_proyecto(self, data):
        """Crea proyecto usando business service."""
        empresa = self._get_empresa()
        return orchestrate_create_proyecto(empresa, data)

    def service_actualizar_proyecto(self, proyecto, data):
        """Actualiza proyecto usando business service."""
        return orchestrate_update_proyecto(proyecto, data)

    def _get_empresa(self):
        """Helper para obtener empresa actual."""
        from apps.tenant.empresa.models import Empresa
        empresa_id = self.get_empresa_id()
        return Empresa.objects.filter(id=empresa_id).first()
