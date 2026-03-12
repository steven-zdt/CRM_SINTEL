"""Core API v1 - Facturas serializers facade.

⚠️ POLÍTICA:
- No copiar lógica de negocio.
- Composición vía herencia de serializers existentes de la app facturas.
- ⚠️ v2.61.1: Alineado con patrón de cotizaciones
"""

from apps.tenant.facturas.api.serializers import (
    FacturaListSerializer,
    FacturaDetailSerializer,
    FacturaWriteSerializer,
    ItemFacturaSerializer,
    NotaCreditoListSerializer,
    NotaCreditoDetailSerializer,
)


class FacturaWorkspaceListSerializer(FacturaListSerializer):
    """
    ⚠️ v2.61.1: Serializer facade para listado de facturas en Core API.
    """
    class Meta(FacturaListSerializer.Meta):
        pass


class FacturaWorkspaceDetailSerializer(FacturaDetailSerializer):
    """
    ⚠️ v2.61.1: Serializer facade para detalle de factura en Core API.
    """
    class Meta(FacturaDetailSerializer.Meta):
        pass


class FacturaWorkspaceSerializer(FacturaWriteSerializer):
    """
    ⚠️ v2.61.1: Serializer facade para escritura de factura en Core API.
    """
    class Meta(FacturaWriteSerializer.Meta):
        pass


class ItemFacturaWorkspaceSerializer(ItemFacturaSerializer):
    """
    ⚠️ v2.61.1: Serializer facade para items de factura en Core API.
    """
    class Meta(ItemFacturaSerializer.Meta):
        pass


class NotaCreditoWorkspaceListSerializer(NotaCreditoListSerializer):
    """
    ⚠️ v2.61.1: Serializer facade para listado de notas crédito en Core API.
    """
    class Meta(NotaCreditoListSerializer.Meta):
        pass


class NotaCreditoWorkspaceDetailSerializer(NotaCreditoDetailSerializer):
    """
    ⚠️ v2.61.1: Serializer facade para detalle de nota crédito en Core API.
    """
    class Meta(NotaCreditoDetailSerializer.Meta):
        pass
