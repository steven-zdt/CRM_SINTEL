"""
API Mixins para Gastos - Inyeccion de servicios en ViewSets.

WARNING: SINTEL v2.61.4: Arquitectura Service Layer Modular.
- Este archivo contiene mixins especificos para cada modelo.
- Inyectan acceso estandarizado a Selectors, CRUDService y BusinessService.
- Usan get_empresa_id() de SintelDSVMixin para Zero Trust.
"""
from apps.tenant.gastos.services.selectors import (
    ResolucionSelector,
    DocumentoSelector,
)
from apps.tenant.gastos.services.business_service import (
    GastoBusinessService,
    ResolucionBusinessService,
)
from apps.tenant.gastos.services.crud_service import (
    ResolucionCRUDService,
    DocumentoCRUDService,
)


class GastoServiceMixin:
    """
    Service mixin para Gasto ViewSet.
    Inyecta acceso a Selectors y BusinessService.
    Requiere que el ViewSet herede de SintelDSVMixin (para get_empresa_id).
    """

    selector_class = DocumentoSelector
    business_service_class = GastoBusinessService
    crud_service_class = DocumentoCRUDService

    def _get_empresa_id_seguro(self):
        """Obtiene empresa_id con fallback al singleton del esquema tenant."""
        try:
            return self.get_empresa_id()
        except Exception:
            empresa = self._get_empresa()
            return empresa.id if empresa else None

    def get_qs_list(self):
        """Retorna queryset de lista usando selector."""
        empresa_id = self._get_empresa_id_seguro()
        search = self.request.query_params.get('search') if hasattr(self, 'request') else None
        return self.selector_class.get_list(empresa_id, search=search)

    def get_qs_detail(self):
        """Retorna queryset de detalle usando selector."""
        empresa_id = self._get_empresa_id_seguro()
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field or 'pk'
        return self.selector_class.get_detail(empresa_id, self.kwargs.get(lookup_url_kwarg))

    def service_calcular_retenciones(self, subtotal, retefuente_pct, reteica_pct):
        """Calcula retenciones usando business service."""
        return self.business_service_class.calcular_retenciones(
            subtotal, retefuente_pct, reteica_pct
        )

    def service_crear_gasto(self, data, empresa):
        """Bridge para creacion de gasto desde ViewSet."""
        return self.business_service_class.procesar_gasto(empresa, data)

    def service_anular_gasto(self, gasto, motivo, usuario):
        """Anula un gasto usando business service."""
        empresa_id = self.get_empresa_id()
        return self.business_service_class.anular_gasto(gasto.id, motivo, usuario, empresa_id)


    def service_get_summary(self):
        """Obtiene resumen de gastos usando selector."""
        empresa_id = self._get_empresa_id_seguro()
        return self.selector_class.get_summary(empresa_id)

    def _get_empresa(self):
        """Helper para obtener empresa actual."""
        from apps.tenant.empresa.models import Empresa
        try:
            empresa_id = self.get_empresa_id()
            return Empresa.objects.filter(id=empresa_id).first()
        except Exception:
            return Empresa.objects.only('id').first()


class ResolucionServiceMixin:
    """
    Service mixin para ResolucionDIAN ViewSet.
    Inyecta acceso a Selectors y CRUDService.
    """

    selector_class = ResolucionSelector
    crud_service_class = ResolucionCRUDService
    business_service_class = ResolucionBusinessService

    def _get_empresa_id_seguro(self):
        """Obtiene empresa_id con fallback al singleton del esquema tenant."""
        try:
            return self.get_empresa_id()
        except Exception:
            empresa = self._get_empresa()
            return empresa.id if empresa else None

    def get_qs_list(self):
        """Retorna queryset de lista usando selector."""
        empresa_id = self._get_empresa_id_seguro()
        search = self.request.query_params.get('search') if hasattr(self, 'request') else None
        solo_vigentes = self.request.query_params.get('vigentes') == 'true' if hasattr(self, 'request') else False
        return self.selector_class.get_list(empresa_id, search=search, solo_vigentes=solo_vigentes)

    def get_qs_detail(self):
        """Retorna queryset de detalle usando selector."""
        empresa_id = self._get_empresa_id_seguro()
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field or 'pk'
        return self.selector_class.get_detail(empresa_id, self.kwargs.get(lookup_url_kwarg))

    def service_crear_resolucion(self, serializer):
        """Crea resolucion usando business service."""
        empresa = self._get_empresa()
        return self.business_service_class.crear_resolucion(
            data=serializer.validated_data,
            empresa=empresa
        )

    def service_desactivar_resolucion(self, resolucion):
        """Desactiva resolucion usando business service."""
        empresa_id = self.get_empresa_id()
        return self.business_service_class.desactivar_resolucion(empresa_id, resolucion.id)


    def service_obtener_vigente(self):
        """Obtiene resolucion vigente usando business service."""
        empresa_id = self._get_empresa_id_seguro()
        return self.selector_class.get_vigente(empresa_id)

    def service_obtener_siguiente_numero_soporte(self, empresa):
        """Obtiene el siguiente consecutivo para la resolucion vigente."""
        resolucion = self.service_obtener_vigente()
        if not resolucion:
            return None
        return DocumentoCRUDService._obtener_siguiente_consecutivo(resolucion)

    def _get_empresa(self):
        """Helper para obtener empresa actual."""
        from apps.tenant.empresa.models import Empresa
        try:
            empresa_id = self.get_empresa_id()
            return Empresa.objects.filter(id=empresa_id).first()
        except Exception:
            return Empresa.objects.only('id').first()


