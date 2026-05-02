"""Core API v1 - Contabilidad facade.

# WARNING: POLÍTICA:
- No copiar lógica de negocio.
- La app Core solo orquesta y expone los mismos ViewSets (acciones incluidas).
- Las acciones @action se arrastran por herencia (NO redefinir).
- # WARNING: v2.61: Incluye CatalogoMaestroNIIFViewSet para el catálogo oficial NIIF Colombia.
"""

from apps.tenant.contabilidad.api.viewsets import (
    AsientoContableViewSet,
    CatalogoMaestroNIIFViewSet,
    CuentaContableViewSet,
    MovimientoContableViewSet,
    PeriodoContableViewSet,  # # WARNING: v2.61
)

from . import serializers as ws_serializers


class CuentaContableCoreViewSet(CuentaContableViewSet):
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ws_serializers.CuentaContableWorkspaceDetailSerializer
        return ws_serializers.CuentaContableWorkspaceListSerializer


class AsientoContableCoreViewSet(AsientoContableViewSet):
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ws_serializers.AsientoContableWorkspaceDetailSerializer
        return ws_serializers.AsientoContableWorkspaceListSerializer


class MovimientoContableCoreViewSet(MovimientoContableViewSet):
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ws_serializers.MovimientoContableWorkspaceDetailSerializer
        return ws_serializers.MovimientoContableWorkspaceListSerializer


class CatalogoMaestroNIIFCoreViewSet(CatalogoMaestroNIIFViewSet):
    """
    Facade para CatalogoMaestroNIIF (Catálogo oficial NIIF Colombia).
    
    # WARNING: v2.61: Expone el catálogo maestro NIIF a través de Core API.
    """
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ws_serializers.CatalogoMaestroNIIFWorkspaceDetailSerializer
        return ws_serializers.CatalogoMaestroNIIFWorkspaceListSerializer


class PeriodoContableCoreViewSet(PeriodoContableViewSet):
    """
    Facade para PeriodoContable (Periodos Contables).
    
    # WARNING: v2.61: Expone los periodos contables a través de Core API.
    """
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ws_serializers.PeriodoContableWorkspaceDetailSerializer
        return ws_serializers.PeriodoContableWorkspaceListSerializer
