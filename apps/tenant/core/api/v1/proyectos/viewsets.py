"""Core API v1 - Proyectos facade.

⚠️ POLÍTICA:
- No copiar lógica de negocio.
- La app Core solo orquesta y expone los mismos ViewSets (acciones incluidas).
"""

from rest_framework.authentication import SessionAuthentication

from apps.tenant.proyectos.api.viewsets import ProyectoViewSet

from . import serializers as ws_serializers


class ProyectoCoreViewSet(ProyectoViewSet):
    authentication_classes = [SessionAuthentication]

    def get_serializer_class(self):
        if self.action == 'list':
            return ws_serializers.ProyectoWorkspaceListSerializer
        return ws_serializers.ProyectoWorkspaceDetailSerializer
