"""Core API v1 - Inventario facade.

⚠️ POLÍTICA:
- No copiar lógica de negocio.
- La app Core solo orquesta y expone los mismos ViewSets (acciones incluidas).
- Las acciones @action se arrastran por herencia (NO redefinir).
"""

from rest_framework.authentication import SessionAuthentication

from apps.tenant.inventario.api.viewsets import (
    ActivoFijoViewSet,
    CategoriaItemViewSet,
    MovimientoInventarioViewSet,
    ProductoViewSet,
    ServicioViewSet,
)

from . import serializers as ws_serializers


class CategoriaItemCoreViewSet(CategoriaItemViewSet):
    authentication_classes = [SessionAuthentication]

    def get_serializer_class(self):
        if self.action == "list":
            return ws_serializers.CategoriaItemWorkspaceListSerializer
        return ws_serializers.CategoriaItemWorkspaceDetailSerializer


class ProductoCoreViewSet(ProductoViewSet):
    authentication_classes = [SessionAuthentication]

    def get_serializer_class(self):
        if self.action == "list":
            return ws_serializers.ProductoWorkspaceListSerializer
        return ws_serializers.ProductoWorkspaceDetailSerializer


class MovimientoInventarioCoreViewSet(MovimientoInventarioViewSet):
    authentication_classes = [SessionAuthentication]

    def get_serializer_class(self):
        if self.action == "list":
            return ws_serializers.MovimientoInventarioWorkspaceListSerializer
        return ws_serializers.MovimientoInventarioWorkspaceDetailSerializer


class ServicioCoreViewSet(ServicioViewSet):
    authentication_classes = [SessionAuthentication]

    def get_serializer_class(self):
        if self.action == "list":
            return ws_serializers.ServicioWorkspaceListSerializer
        return ws_serializers.ServicioWorkspaceDetailSerializer


class ActivoFijoCoreViewSet(ActivoFijoViewSet):
    authentication_classes = [SessionAuthentication]

    def get_serializer_class(self):
        if self.action == "list":
            return ws_serializers.ActivoFijoWorkspaceListSerializer
        return ws_serializers.ActivoFijoWorkspaceDetailSerializer
