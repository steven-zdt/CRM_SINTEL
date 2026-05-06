"""
API Mixins para Gastos - Inyección de servicios en ViewSets.

WARNING: SINTEL v2.61.4: Arquitectura Service Layer Modular.
- Este archivo contiene mixins específicos para cada modelo.
- Inyectan acceso estandarizado a Selectors, CRUDService y BusinessService.
- Usan get_empresa_id() de SintelDSVMixin para Zero Trust.
"""
from apps.tenant.gastos.services.selectors import (
    GastoSelector,
    ResolucionSelector,
    DocumentoSelector,
)
from apps.tenant.gastos.services.business_service import (
    GastoBusinessService,
    ResolucionBusinessService,
)
from apps.tenant.gastos.services.crud_service import (
    GastoCRUDService,
    ResolucionCRUDService,
    DocumentoCRUDService,
)


class GastoServiceMixin:
    """
    Service mixin para Gasto ViewSet.
    Inyecta acceso a Selectors y BusinessService.
    Requiere que el ViewSet herede de SintelDSVMixin (para get_empresa_id).
    """

    selector_class = GastoSelector
    business_service_class = GastoBusinessService
    crud_service_class = GastoCRUDService

    def get_qs_list(self):
        """Retorna queryset de lista usando selector."""
        empresa_id = self.get_empresa_id()
        search = self.request.query_params.get('search') if hasattr(self, 'request') else None
        return self.selector_class.get_list(empresa_id, search=search)

    def get_qs_detail(self):
        """Retorna queryset de detalle usando selector."""
        empresa_id = self.get_empresa_id()
        return self.selector_class.get_detail(empresa_id, self.kwargs.get('pk'))

    def service_calcular_retenciones(self, subtotal, retefuente_pct, reteica_pct):
        """Calcula retenciones usando business service."""
        return self.business_service_class.calcular_retenciones(
            subtotal, retefuente_pct, reteica_pct
        )

    def service_procesar_gasto(self, serializer):
        """Procesa creación de gasto usando business service."""
        empresa = self._get_empresa()
        return self.business_service_class.procesar_gasto(
            empresa=empresa,
            data=serializer.validated_data
        )

    def service_anular_gasto(self, gasto):
        """Anula un gasto usando CRUD service."""
        return self.crud_service_class.anular_gasto(gasto)

    def service_desactivar_gasto(self, gasto):
        """Desactiva un gasto usando CRUD service."""
        return self.crud_service_class.desactivar_gasto(gasto)

    def service_get_summary(self):
        """Obtiene resumen de gastos usando selector."""
        empresa_id = self.get_empresa_id()
        return self.selector_class.get_summary(empresa_id)

    def _get_empresa(self):
        """Helper para obtener empresa actual."""
        from apps.tenant.empresa.models import Empresa
        empresa_id = self.get_empresa_id()
        return Empresa.objects.filter(id=empresa_id).first()


class ResolucionServiceMixin:
    """
    Service mixin para ResolucionDIAN ViewSet.
    Inyecta acceso a Selectors y CRUDService.
    """

    selector_class = ResolucionSelector
    crud_service_class = ResolucionCRUDService
    business_service_class = ResolucionBusinessService

    def get_qs_list(self):
        """Retorna queryset de lista usando selector."""
        empresa_id = self.get_empresa_id()
        search = self.request.query_params.get('search') if hasattr(self, 'request') else None
        solo_vigentes = self.request.query_params.get('vigentes') == 'true' if hasattr(self, 'request') else False
        return self.selector_class.get_list(empresa_id, search=search, solo_vigentes=solo_vigentes)

    def get_qs_detail(self):
        """Retorna queryset de detalle usando selector."""
        empresa_id = self.get_empresa_id()
        return self.selector_class.get_detail(empresa_id, self.kwargs.get('pk'))

    def service_crear_resolucion(self, serializer):
        """Crea resolución usando CRUD service."""
        empresa = self._get_empresa()
        return self.crud_service_class.crear_resolucion(
            data=serializer.validated_data,
            empresa=empresa
        )

    def service_desactivar_resolucion(self, resolucion):
        """Desactiva resolución usando CRUD service."""
        return self.crud_service_class.desactivar_resolucion(resolucion)

    def service_puede_eliminar(self, resolucion):
        """Verifica si se puede eliminar la resolución."""
        return self.crud_service_class.puede_eliminar(resolucion)

    def service_eliminar_resolucion(self, resolucion):
        """Elimina resolución usando CRUD service."""
        return self.crud_service_class.eliminar_resolucion(resolucion)

    def service_obtener_vigente(self):
        """Obtiene resolución vigente usando business service."""
        empresa_id = self.get_empresa_id()
        return self.business_service_class.obtener_vigente(empresa_id)

    def _get_empresa(self):
        """Helper para obtener empresa actual."""
        from apps.tenant.empresa.models import Empresa
        empresa_id = self.get_empresa_id()
        return Empresa.objects.filter(id=empresa_id).first()


class DocumentoServiceMixin:
    """
    Service mixin para DocumentoSoporte (uso interno).
    """

    selector_class = DocumentoSelector
    crud_service_class = DocumentoCRUDService

    def get_qs_list(self):
        """Retorna queryset de lista usando selector."""
        empresa_id = self.get_empresa_id()
        resolucion_id = self.request.query_params.get('resolucion') if hasattr(self, 'request') else None
        search = self.request.query_params.get('search') if hasattr(self, 'request') else None
        return self.selector_class.get_list(empresa_id, resolucion_id=resolucion_id, search=search)

    def get_qs_detail(self):
        """Retorna queryset de detalle usando selector."""
        empresa_id = self.get_empresa_id()
        return self.selector_class.get_detail(empresa_id, self.kwargs.get('pk'))
