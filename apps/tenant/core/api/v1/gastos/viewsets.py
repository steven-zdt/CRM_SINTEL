"""Core API v1 - Gastos facade.

⚠️ POLÍTICA:
- No copiar lógica de negocio.
- La app Core solo orquesta y expone los mismos ViewSets (acciones incluidas).
- Las acciones @action se arrastran por herencia (NO redefinir).
"""

from rest_framework.authentication import SessionAuthentication

from apps.tenant.gastos.api.viewsets import GastoViewSet, ResolucionDIANViewSet

from . import serializers as ws_serializers


class GastoCoreViewSet(GastoViewSet):
    authentication_classes = [SessionAuthentication]

    def get_serializer_class(self):
        if self.action == "list":
            return ws_serializers.GastoWorkspaceListSerializer
        return ws_serializers.GastoWorkspaceDetailSerializer


class ResolucionDIANCoreViewSet(ResolucionDIANViewSet):
    authentication_classes = [SessionAuthentication]
