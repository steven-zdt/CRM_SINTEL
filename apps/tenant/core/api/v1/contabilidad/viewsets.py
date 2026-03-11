"""Core API v1 - Contabilidad facade.

⚠️ POLÍTICA:
- No copiar lógica de negocio.
- La app Core solo orquesta y expone los mismos ViewSets (acciones incluidas).
- Las acciones @action se arrastran por herencia (NO redefinir).
- ⚠️ v2.61: Incluye CatalogoMaestroNIIFViewSet para el catálogo oficial NIIF Colombia.
"""

from rest_framework.authentication import SessionAuthentication

from apps.tenant.contabilidad.api.viewsets import (
    CuentaContableViewSet,
    AsientoContableViewSet,
    MovimientoContableViewSet,
    CatalogoMaestroNIIFViewSet,
)

from . import serializers as ws_serializers


class CuentaContableCoreViewSet(CuentaContableViewSet):
    authentication_classes = [SessionAuthentication]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ws_serializers.CuentaContableWorkspaceDetailSerializer
        return ws_serializers.CuentaContableWorkspaceListSerializer


class AsientoContableCoreViewSet(AsientoContableViewSet):
    authentication_classes = [SessionAuthentication]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ws_serializers.AsientoContableWorkspaceDetailSerializer
        return ws_serializers.AsientoContableWorkspaceListSerializer


class MovimientoContableCoreViewSet(MovimientoContableViewSet):
    authentication_classes = [SessionAuthentication]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ws_serializers.MovimientoContableWorkspaceDetailSerializer
        return ws_serializers.MovimientoContableWorkspaceListSerializer


class CatalogoMaestroNIIFCoreViewSet(CatalogoMaestroNIIFViewSet):
    """
    Facade para CatalogoMaestroNIIF (Catálogo oficial NIIF Colombia).
    
    ⚠️ v2.61: Expone el catálogo maestro NIIF a través de Core API.
    """
    authentication_classes = [SessionAuthentication]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ws_serializers.CatalogoMaestroNIIFWorkspaceDetailSerializer
        return ws_serializers.CatalogoMaestroNIIFWorkspaceListSerializer
