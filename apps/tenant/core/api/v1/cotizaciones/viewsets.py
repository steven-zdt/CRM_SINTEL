"""Core API v1 - Cotizaciones facade.

# WARNING: POLÍTICA:
- No copiar lógica de negocio.
- La app Core solo orquesta y expone los mismos ViewSets (acciones incluidas).
- Las acciones @action se arrastran por herencia (NO redefinir).
"""

from apps.tenant.cotizaciones.api.viewsets import CotizacionItemViewSet, CotizacionViewSet
from apps.tenant.cotizaciones.configuracion.viewsets import ConfiguracionCotizacionViewSet

from . import serializers as ws_serializers


class CotizacionCoreViewSet(CotizacionViewSet):
    serializer_class = ws_serializers.CotizacionWorkspaceSerializer


class CotizacionItemCoreViewSet(CotizacionItemViewSet):
    serializer_class = ws_serializers.CotizacionItemWorkspaceSerializer


class ConfiguracionCotizacionCoreViewSet(ConfiguracionCotizacionViewSet):
    def get_serializer_class(self):
        if self.action == 'list':
            return ws_serializers.ConfiguracionCotizacionWorkspaceListSerializer
        return ws_serializers.ConfiguracionCotizacionWorkspaceDetailSerializer
