"""
ViewSets CRUD para catálogos de impuestos (privados, autenticados).

Estos ViewSets permiten crear/editar/eliminar catálogos desde la consola.
Los ViewSets públicos (ReadOnly) permanecen en viewsets.py para acceso público.

Referencia: https://www.django-rest-framework.org/api-guide/viewsets/
"""

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, viewsets
from rest_framework.filters import OrderingFilter, SearchFilter

from apps.config.api.pagination import StandardResultsSetPagination
from apps.public.impuestos.api.serializers import (
    ActividadEconomicaSerializer,
    CodigoTributarioSerializer,
    ConceptoRetencionSerializer,
    NormaTributariaSerializer,
    TarifaIVASerializer,
    TipoImpuestoSerializer,
)
from apps.public.impuestos.models import (
    ActividadEconomica,
    CodigoTributario,
    ConceptoRetencion,
    NormaTributaria,
    TarifaIVA,
    TipoImpuesto,
)


class BaseCRUD(viewsets.ModelViewSet):
    """Base ViewSet CRUD para catálogos (autenticados)."""

    permission_classes = [permissions.IsAuthenticated]  # Requiere autenticación
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    ordering_fields = "__all__"
    ordering = ["id"]

    def perform_create(self, serializer):
        """Invalidar caché después de crear."""
        instance = serializer.save()
        self._clear_cache()
        return instance

    def perform_update(self, serializer):
        """Invalidar caché después de actualizar."""
        instance = serializer.save()
        self._clear_cache()
        return instance

    def perform_destroy(self, instance):
        """Invalidar caché después de eliminar."""
        instance.delete()
        self._clear_cache()

    def _clear_cache(self):
        """Invalidar caché del provider si es necesario."""
        try:
            from apps.public.impuestos.services.provider import clear_impuestos_cache

            clear_impuestos_cache()
        except ImportError:
            # Si el provider no está disponible, continuar sin error
            pass


class TipoImpuestoCRUDViewSet(BaseCRUD):
    """ViewSet CRUD para TipoImpuesto."""

    queryset = TipoImpuesto.objects.all()
    serializer_class = TipoImpuestoSerializer
    filterset_fields = ["activo", "fecha_vigencia"]
    search_fields = ["codigo", "nombre", "descripcion"]
    ordering = ["codigo"]


class TarifaIVACRUDViewSet(BaseCRUD):
    """ViewSet CRUD para TarifaIVA."""

    queryset = TarifaIVA.objects.all()
    serializer_class = TarifaIVASerializer
    filterset_fields = ["activo", "tipo_tarifa", "fecha_vigencia"]
    search_fields = ["codigo", "nombre", "descripcion"]
    ordering = ["-fecha_vigencia"]


class ConceptoRetencionCRUDViewSet(BaseCRUD):
    """ViewSet CRUD para ConceptoRetencion."""

    queryset = ConceptoRetencion.objects.all()
    serializer_class = ConceptoRetencionSerializer
    filterset_fields = ["activo", "tipo_retencion", "fecha_vigencia"]
    search_fields = ["codigo", "nombre", "descripcion"]
    ordering = ["codigo"]


class CodigoTributarioCRUDViewSet(BaseCRUD):
    """ViewSet CRUD para CodigoTributario."""

    queryset = CodigoTributario.objects.all()
    serializer_class = CodigoTributarioSerializer
    filterset_fields = ["activo", "tipo", "fecha_vigencia"]
    search_fields = ["codigo", "nombre", "descripcion", "tipo"]
    ordering = ["codigo"]


class ActividadEconomicaCRUDViewSet(BaseCRUD):
    """ViewSet CRUD para ActividadEconomica."""

    queryset = ActividadEconomica.objects.all()
    serializer_class = ActividadEconomicaSerializer
    filterset_fields = ["activo"]
    search_fields = ["codigo", "nombre", "descripcion"]
    ordering = ["codigo"]


class NormaTributariaCRUDViewSet(BaseCRUD):
    """ViewSet CRUD para NormaTributaria."""

    queryset = NormaTributaria.objects.all()
    serializer_class = NormaTributariaSerializer
    filterset_fields = ["articulo", "impuesto", "tema", "vigencia_desde", "vigencia_hasta"]
    search_fields = ["articulo", "tema", "impuesto", "texto_plano"]
    ordering = ["vigencia_desde", "articulo"]
