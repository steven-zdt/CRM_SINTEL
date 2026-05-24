"""
API Mixins for ConfiguracionCotizacion (v3.10.1).

SINTEL v3.10.1: Arquitectura Service Layer Modular.
- Hereda de BaseServiceMixin (canonical, consolidado)
- Mantiene solo métodos service_* específicos de ConfiguracionCotizacion
"""
from apps.tenant.api.mixins import BaseServiceMixin
from .selectors import ConfiguracionSelector
from .business_service import ConfiguracionBusinessService

class ConfiguracionServiceMixin(BaseServiceMixin):
    selector_class = ConfiguracionSelector
    business_service_class = ConfiguracionBusinessService

    def get_qs_list(self):
        empresa_id = self.get_empresa_id()
        return self.selector_class.get_list(empresa_id)

    def get_qs_detail(self):
        empresa_id = self.get_empresa_id()
        return self.selector_class.get_list(empresa_id)

    def service_crear_configuracion(self, serializer):
        """Crea configuracion usando business service."""
        empresa = self._get_empresa()
        return self.business_service_class.crear_configuracion(
            empresa=empresa,
            datos=serializer.validated_data,
        )

    def service_actualizar_configuracion(self, instance, serializer):
        """Actualiza configuracion usando business service."""
        return self.business_service_class.actualizar_configuracion(
            instance,
            serializer.validated_data,
        )
