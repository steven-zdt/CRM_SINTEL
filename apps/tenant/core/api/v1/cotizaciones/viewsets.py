"""Core API v1 - Cotizaciones facade.

⚠️ POLÍTICA:
- No copiar lógica de negocio.
- La app Core solo orquesta y expone los mismos ViewSets (acciones incluidas).
- Las acciones @action se arrastran por herencia (NO redefinir).
"""

from rest_framework.authentication import SessionAuthentication

from apps.tenant.cotizaciones.api.viewsets import CotizacionViewSet, CotizacionItemViewSet
from apps.tenant.cotizaciones.configuracion.viewsets import ConfiguracionCotizacionViewSet

from . import serializers as ws_serializers


class CotizacionCoreViewSet(CotizacionViewSet):
    authentication_classes = [SessionAuthentication]
    serializer_class = ws_serializers.CotizacionWorkspaceSerializer


class CotizacionItemCoreViewSet(CotizacionItemViewSet):
    authentication_classes = [SessionAuthentication]
    serializer_class = ws_serializers.CotizacionItemWorkspaceSerializer


class ConfiguracionCotizacionCoreViewSet(ConfiguracionCotizacionViewSet):
    authentication_classes = [SessionAuthentication]

    def get_serializer_class(self):
        if self.action == 'list':
            return ws_serializers.ConfiguracionCotizacionWorkspaceListSerializer
        return ws_serializers.ConfiguracionCotizacionWorkspaceDetailSerializer
