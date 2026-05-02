"""Core API v1 - Proyectos facade.

# WARNING: POLÍTICA:
- No copiar lógica de negocio.
- La app Core solo orquesta y expone los mismos ViewSets (acciones incluidas).
"""

from apps.tenant.proyectos.api.viewsets import ProyectoViewSet

from . import serializers as ws_serializers


class ProyectoCoreViewSet(ProyectoViewSet):
    def get_serializer_class(self):
        if self.action == 'list':
            return ws_serializers.ProyectoWorkspaceListSerializer
        return ws_serializers.ProyectoWorkspaceDetailSerializer
