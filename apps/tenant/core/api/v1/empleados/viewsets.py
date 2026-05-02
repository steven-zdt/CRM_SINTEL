"""Core API v1 - Empleados facade.

# WARNING: POLÍTICA:
- No copiar lógica de negocio.
- La app Core solo orquesta y expone los mismos ViewSets (acciones incluidas).
- Las acciones @action se arrastran por herencia (NO redefinir).
"""

from apps.tenant.empleados.api.viewsets import ContratoViewSet, DevengoViewSet, EmpleadoViewSet

from . import serializers as ws_serializers


class EmpleadoCoreViewSet(EmpleadoViewSet):
    def get_serializer_class(self):
        return (
            ws_serializers.EmpleadoWorkspaceListSerializer
            if self.action == 'list'
            else ws_serializers.EmpleadoWorkspaceDetailSerializer
        )


class ContratoCoreViewSet(ContratoViewSet):
    serializer_class = ws_serializers.ContratoWorkspaceSerializer


class DevengoCoreViewSet(DevengoViewSet):
    serializer_class = ws_serializers.DevengoWorkspaceSerializer
