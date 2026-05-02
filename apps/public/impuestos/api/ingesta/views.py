"""
Vistas DRF para la API de Ingesta.

Referencia: https://www.django-rest-framework.org/api-guide/viewsets/
"""

from rest_framework import mixins, status, viewsets
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.public.impuestos.api.ingesta.serializers import (
    DocumentoFuenteCreateSerializer,
    DocumentoFuenteDetailSerializer,
)
from apps.public.impuestos.api.ingesta.throttling import IngestaScopedThrottle
from apps.public.impuestos.models import DocumentoFuente


class IngestaViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    ViewSet para ingesta de documentos tributarios.

    Endpoints:
    - POST /api/public/v1/impuestos/ingesta/ : Crear documento (archivo o URL)
    - GET /api/public/v1/impuestos/ingesta/ : Listar documentos
    - GET /api/public/v1/impuestos/ingesta/{id}/ : Detalle con logs
    """

    queryset = DocumentoFuente.objects.all().order_by("-created_at")
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, JSONParser, FormParser]  # multipart + json + form-urlencoded
    throttle_classes = [IngestaScopedThrottle]
    throttle_scope = "impuestos_ingesta"

    def get_serializer_class(self):
        """Usar CreateSerializer para create, DetailSerializer para el resto."""
        if self.action == "create":
            return DocumentoFuenteCreateSerializer
        return DocumentoFuenteDetailSerializer

    def create(self, request, *args, **kwargs):
        """
        Crear DocumentoFuente y disparar tarea Celery.

        - Si url_origen: encola descargar_fuente
        - Si archivo: encola procesar_fuente
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Crear documento con estado RECIBIDO
        doc: DocumentoFuente = serializer.save(estado="RECIBIDO")

        # Disparar tarea Celery según el caso
        try:
            from apps.public.impuestos.tasks import descargar_fuente, procesar_fuente

            if doc.url_origen and not doc.archivo:
                # Encolar descarga desde URL
                descargar_fuente.delay(doc.id)
            else:
                # Archivo ya presente; encolar procesamiento
                procesar_fuente.delay(doc.id)
        except ImportError:
            # Si Celery no está configurado, solo registrar
            pass

        # Devolver detalle con 202 Accepted
        detail_serializer = DocumentoFuenteDetailSerializer(doc)
        return Response(detail_serializer.data, status=status.HTTP_202_ACCEPTED)
