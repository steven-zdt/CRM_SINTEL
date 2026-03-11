"""Core API v1 - Cotizaciones serializers facade.

⚠️ POLÍTICA:
- No copiar lógica de negocio.
- Composición vía herencia de serializers existentes de la app cotizaciones.
"""

from apps.tenant.cotizaciones.api.serializers import (
    CotizacionSerializer,
    CotizacionItemSerializer,
)
from apps.tenant.cotizaciones.configuracion.serializers import (
    ConfiguracionCotizacionListSerializer,
    ConfiguracionCotizacionDetailSerializer,
)


class CotizacionItemWorkspaceSerializer(CotizacionItemSerializer):
    class Meta(CotizacionItemSerializer.Meta):
        pass


class CotizacionWorkspaceSerializer(CotizacionSerializer):
    class Meta(CotizacionSerializer.Meta):
        pass


class ConfiguracionCotizacionWorkspaceListSerializer(ConfiguracionCotizacionListSerializer):
    class Meta(ConfiguracionCotizacionListSerializer.Meta):
        pass


class ConfiguracionCotizacionWorkspaceDetailSerializer(ConfiguracionCotizacionDetailSerializer):
    class Meta(ConfiguracionCotizacionDetailSerializer.Meta):
        pass
