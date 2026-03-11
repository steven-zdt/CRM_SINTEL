"""Core API v1 - Inventario serializers facade.

⚠️ POLÍTICA:
- No copiar lógica de negocio.
- Heredar serializers existentes de la app inventario.
- Exponer URLs absolutas de imágenes para el Workspace.
"""

from rest_framework import serializers

from apps.tenant.inventario.api.serializers import (
    CategoriaItemDetailSerializer,
    CategoriaItemListSerializer,
    MovimientoInventarioDetailSerializer,
    MovimientoInventarioListSerializer,
    ProductoDetailSerializer,
    ProductoListSerializer,
)


class _ImagenUrlMixin(serializers.Serializer):
    imagen_url = serializers.SerializerMethodField()

    def get_imagen_url(self, obj):
        request = self.context.get("request") if hasattr(self, "context") else None
        if not getattr(obj, "imagen", None):
            return None
        try:
            url = obj.imagen.url
        except Exception:
            return None
        return request.build_absolute_uri(url) if request else url


class CategoriaItemWorkspaceListSerializer(_ImagenUrlMixin, CategoriaItemListSerializer):
    class Meta(CategoriaItemListSerializer.Meta):
        fields = tuple(CategoriaItemListSerializer.Meta.fields) + ("imagen_url",)


class CategoriaItemWorkspaceDetailSerializer(_ImagenUrlMixin, CategoriaItemDetailSerializer):
    class Meta(CategoriaItemDetailSerializer.Meta):
        fields = tuple(CategoriaItemDetailSerializer.Meta.fields) + ("imagen_url",)


class ProductoWorkspaceListSerializer(_ImagenUrlMixin, ProductoListSerializer):
    class Meta(ProductoListSerializer.Meta):
        fields = tuple(ProductoListSerializer.Meta.fields) + ("imagen_url",)


class ProductoWorkspaceDetailSerializer(_ImagenUrlMixin, ProductoDetailSerializer):
    class Meta(ProductoDetailSerializer.Meta):
        fields = tuple(ProductoDetailSerializer.Meta.fields) + ("imagen_url",)


class MovimientoInventarioWorkspaceListSerializer(MovimientoInventarioListSerializer):
    class Meta(MovimientoInventarioListSerializer.Meta):
        pass


class MovimientoInventarioWorkspaceDetailSerializer(MovimientoInventarioDetailSerializer):
    class Meta(MovimientoInventarioDetailSerializer.Meta):
        pass
