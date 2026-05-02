"""Mixin de inyeccion de servicios para Perfil ViewSet."""
from apps.tenant.perfil.services.business_service import PerfilBusinessService
from apps.tenant.perfil.services.crud_service import PerfilCRUDService
from apps.tenant.perfil.services.selectors import PerfilSelector


class PerfilServiceMixin:
    """Inyecta acceso estandarizado a Selector, CRUDService y BusinessService."""

    selector_class = PerfilSelector
    business_service_class = PerfilBusinessService
    crud_service_class = PerfilCRUDService

    @property
    def perfil_service(self):
        return PerfilBusinessService()

    def get_qs_list(self):
        """Retorna queryset de lista usando selector."""
        empresa_id = self._resolve_empresa_id()
        search = self.request.query_params.get('search') if hasattr(self, 'request') else None
        return self.selector_class.get_list(empresa_id, search=search)

    def get_qs_detail(self):
        """Retorna queryset de detalle usando selector."""
        empresa_id = self._resolve_empresa_id()
        pk = self.kwargs.get('pk')
        return self.selector_class.get_detail(pk, empresa_id)

    def _resolve_empresa_id(self):
        """Resuelve empresa_id del tenant activo."""
        from apps.tenant.empresa.models import Empresa
        empresa = Empresa.objects.only('id').first()
        return empresa.id if empresa else None
