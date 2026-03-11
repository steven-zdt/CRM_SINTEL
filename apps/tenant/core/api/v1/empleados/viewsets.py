"""Core API v1 - Empleados facade.

⚠️ POLÍTICA:
- No copiar lógica de negocio.
- La app Core solo orquesta y expone los mismos ViewSets (acciones incluidas).
- Las acciones @action se arrastran por herencia (NO redefinir).
"""

from rest_framework.authentication import SessionAuthentication

from apps.tenant.empleados.api.viewsets import EmpleadoViewSet, ContratoViewSet, DevengoViewSet

from . import serializers as ws_serializers


class EmpleadoCoreViewSet(EmpleadoViewSet):
    authentication_classes = [SessionAuthentication]

    def get_serializer_class(self):
        return (
            ws_serializers.EmpleadoWorkspaceListSerializer
            if self.action == 'list'
            else ws_serializers.EmpleadoWorkspaceDetailSerializer
        )


class ContratoCoreViewSet(ContratoViewSet):
    authentication_classes = [SessionAuthentication]
    serializer_class = ws_serializers.ContratoWorkspaceSerializer


class DevengoCoreViewSet(DevengoViewSet):
    authentication_classes = [SessionAuthentication]
    serializer_class = ws_serializers.DevengoWorkspaceSerializer
