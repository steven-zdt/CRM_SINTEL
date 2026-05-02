"""
ViewSets para la app impuestos (catálogo DIAN).

WARNING: IMPORTANTE: Todos los ViewSets son ReadOnlyModelViewSet porque
este es un catálogo de solo lectura disponible para todos los tenants.

Referencia: https://www.django-rest-framework.org/api-guide/viewsets/
"""

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, status, viewsets
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.config.api.pagination import StandardResultsSetPagination
from apps.public.impuestos.api.serializers import (
    ActividadEconomicaSerializer,
    CodigoTributarioSerializer,
    ConceptoRetencionSerializer,
    ContribuyenteTipoSerializer,
    NormaTributariaSerializer,
    PerfilTributarioSerializer,
    RegimenRentaSerializer,
    ResponsabilidadRUTSerializer,
    TarifaIVASerializer,
    TipoImpuestoSerializer,
)
from apps.public.impuestos.models import (
    ActividadEconomica,
    CodigoTributario,
    ConceptoRetencion,
    ContribuyenteTipo,
    NormaTributaria,
    PerfilTributario,
    RegimenRenta,
    ResponsabilidadRUT,
    TarifaIVA,
    TipoImpuesto,
)


class BaseReadOnly(viewsets.ReadOnlyModelViewSet):
    """Base ViewSet para catálogos públicos (ReadOnly, AllowAny)."""

    permission_classes = [permissions.AllowAny]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    ordering_fields = "__all__"
    ordering = ["id"]


class BaseReadWrite(viewsets.ModelViewSet):
    """
    Base ViewSet para catálogos con permisos según método HTTP.

    WARNING: POLÍTICA SSoT: GET abierto (AllowAny), POST/PUT/PATCH/DELETE solo staff.
    """

    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    ordering_fields = "__all__"
    ordering = ["id"]

    def get_permissions(self):
        """
        Permisos dinámicos: GET abierto, escritura solo staff.
        """
        if self.action in ["list", "retrieve"]:
            # Lectura: abierto a todos
            return [permissions.AllowAny()]
        else:
            # Escritura: solo staff/admin
            return [permissions.IsAdminUser()]

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


class TipoImpuestoViewSet(BaseReadOnly):
    """ViewSet de solo lectura para TipoImpuesto."""

    queryset = TipoImpuesto.objects.all()
    serializer_class = TipoImpuestoSerializer
    filterset_fields = ["activo", "fecha_vigencia"]
    search_fields = ["codigo", "nombre", "descripcion"]
    ordering = ["codigo"]


class TarifaIVAViewSet(BaseReadOnly):
    """ViewSet de solo lectura para TarifaIVA."""

    queryset = TarifaIVA.objects.all()
    serializer_class = TarifaIVASerializer
    filterset_fields = ["activo", "tipo_tarifa", "fecha_vigencia"]
    search_fields = ["codigo", "nombre", "descripcion"]
    ordering = ["-fecha_vigencia"]


class ConceptoRetencionViewSet(BaseReadOnly):
    """ViewSet de solo lectura para ConceptoRetencion."""

    queryset = ConceptoRetencion.objects.all()
    serializer_class = ConceptoRetencionSerializer
    filterset_fields = ["activo", "tipo_retencion", "fecha_vigencia"]
    search_fields = ["codigo", "nombre", "descripcion"]
    ordering = ["codigo"]


class CodigoTributarioViewSet(BaseReadOnly):
    """ViewSet de solo lectura para CodigoTributario."""

    queryset = CodigoTributario.objects.all()
    serializer_class = CodigoTributarioSerializer
    filterset_fields = ["activo", "tipo", "fecha_vigencia"]
    search_fields = ["codigo", "nombre", "descripcion", "tipo"]
    ordering = ["codigo"]


class ActividadEconomicaViewSet(BaseReadOnly):
    """ViewSet de solo lectura para ActividadEconomica."""

    queryset = ActividadEconomica.objects.all()
    serializer_class = ActividadEconomicaSerializer
    filterset_fields = ["activo"]
    search_fields = ["codigo", "nombre", "descripcion"]
    ordering = ["codigo"]


class NormaTributariaViewSet(BaseReadOnly):
    """ViewSet de solo lectura para NormaTributaria."""

    queryset = NormaTributaria.objects.all()
    serializer_class = NormaTributariaSerializer
    filterset_fields = ["articulo", "impuesto", "tema", "vigencia_desde", "vigencia_hasta"]
    search_fields = ["articulo", "tema", "impuesto", "texto_plano"]
    ordering = ["vigencia_desde", "articulo"]


class SearchView(APIView):
    """
    Vista de búsqueda con OpenSearch.

    Endpoint: GET /api/public/v1/impuestos/search/
    Parámetros:
        - q: Query de búsqueda
        - fields: Campos a buscar (default: "titulo^3,articulo^2,tema,impuesto,texto")
        - size: Tamaño de página (default: 20)
        - from: Offset (default: 0)
    """

    permission_classes = [permissions.AllowAny]
    throttle_scope = "impuestos_search"
    throttle_classes = [ScopedRateThrottle]

    def get(self, request):
        """Búsqueda multi_match contra el alias impuestos-docs."""
        from apps.public.impuestos.search.client import get_search_client
        from apps.public.impuestos.search.schema import INDEX_ALIAS

        client = get_search_client()

        # Parámetros de query
        q = request.GET.get("q") or ""
        size = int(request.GET.get("size", 20))
        offset = int(request.GET.get("from", 0))
        fields_str = request.GET.get("fields", "titulo^3,articulo^2,tema,impuesto,texto")
        fields = [f.strip() for f in fields_str.split(",")]

        # Construir query
        body = {
            "size": size,
            "from": offset,
            "query": {
                "multi_match": {
                    "query": q,
                    "fields": fields,
                }
            },
            "highlight": {
                "fields": {
                    "texto": {},
                }
            },
        }

        # Ejecutar búsqueda contra el alias
        try:
            resp = client.search(index=INDEX_ALIAS, body=body)
            return Response(resp)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================================================
# VIEWSETS PARA NORMATIVA DIAN - CATÁLOGOS TRIBUTARIOS (v2.30+)
# ============================================================================


class ContribuyenteTipoViewSet(BaseReadWrite):
    """
    ViewSet para ContribuyenteTipo.

    WARNING: POLÍTICA SSoT: GET abierto, POST/PUT/PATCH/DELETE solo staff.
    """

    queryset = ContribuyenteTipo.objects.all()
    serializer_class = ContribuyenteTipoSerializer
    filterset_fields = ["activo", "clase", "segmento_dian", "vigente_desde", "vigente_hasta"]
    search_fields = ["nombre", "base_legal"]
    ordering = ["clase", "segmento_dian", "nombre"]


class RegimenRentaViewSet(BaseReadWrite):
    """
    ViewSet para RegimenRenta.

    WARNING: POLÍTICA SSoT: GET abierto, POST/PUT/PATCH/DELETE solo staff.
    """

    queryset = RegimenRenta.objects.all()
    serializer_class = RegimenRentaSerializer
    filterset_fields = ["activo", "codigo", "vigente_desde", "vigente_hasta"]
    search_fields = ["nombre", "descripcion", "base_legal"]
    ordering = ["codigo"]


class ResponsabilidadRUTViewSet(BaseReadWrite):
    """
    ViewSet para ResponsabilidadRUT.

    WARNING: POLÍTICA SSoT: GET abierto, POST/PUT/PATCH/DELETE solo staff.
    """

    queryset = ResponsabilidadRUT.objects.all()
    serializer_class = ResponsabilidadRUTSerializer
    filterset_fields = [
        "activo",
        "codigo",
        "es_responsable_iva",
        "es_no_responsable_iva",
        "es_simple",
        "es_facturador_electronico",
        "es_gran_contribuyente",
        "vigente_desde",
        "vigente_hasta",
    ]
    search_fields = ["codigo", "nombre", "descripcion", "base_legal"]
    ordering = ["codigo"]


class PerfilTributarioViewSet(BaseReadWrite):
    """
    ViewSet para PerfilTributario.

    WARNING: POLÍTICA SSoT: GET abierto, POST/PUT/PATCH/DELETE solo staff.
    """

    queryset = (
        PerfilTributario.objects.prefetch_related("responsabilidades")
        .select_related("tipo_contribuyente", "regimen_renta")
        .all()
    )
    serializer_class = PerfilTributarioSerializer
    filterset_fields = [
        "activo",
        "tipo_contribuyente",
        "regimen_renta",
        "recomendado_desde",
        "recomendado_hasta",
    ]
    search_fields = ["nombre"]
    ordering = ["nombre"]


# Lista de ViewSets para registro automático en el router
VIEWSETS = [
    (r"impuestos/tipos", TipoImpuestoViewSet, "tipo-impuesto"),
    (r"impuestos/tarifas-iva", TarifaIVAViewSet, "tarifa-iva"),
    (r"impuestos/conceptos-retencion", ConceptoRetencionViewSet, "concepto-retencion"),
    (r"impuestos/codigos-tributarios", CodigoTributarioViewSet, "codigo-tributario"),
    (r"impuestos/actividades-economicas", ActividadEconomicaViewSet, "actividad-economica"),
    (r"impuestos/normas", NormaTributariaViewSet, "norma-tributaria"),
    # Nuevos catálogos tributarios (v2.30+)
    (r"impuestos/contribuyentes-tipos", ContribuyenteTipoViewSet, "contribuyente-tipo"),
    (r"impuestos/regimenes-renta", RegimenRentaViewSet, "regimen-renta"),
    (r"impuestos/responsabilidades-rut", ResponsabilidadRUTViewSet, "responsabilidad-rut"),
    (r"impuestos/perfiles-tributarios", PerfilTributarioViewSet, "perfil-tributario"),
]
