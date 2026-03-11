"""Core API v1 - Proyectos serializers facade.

⚠️ POLÍTICA:
- No copiar lógica de negocio.
- Composición vía herencia de serializers existentes de la app proyectos.
"""

from apps.tenant.proyectos.api.serializers import ProyectoDetailSerializer, ProyectoListSerializer


class ProyectoWorkspaceListSerializer(ProyectoListSerializer):
    class Meta(ProyectoListSerializer.Meta):
        pass


class ProyectoWorkspaceDetailSerializer(ProyectoDetailSerializer):
    class Meta(ProyectoDetailSerializer.Meta):
        pass
