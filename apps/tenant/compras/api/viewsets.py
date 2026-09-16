import logging

from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from rest_framework.response import Response

from apps.config.api.pagination import StandardResultsSetPagination
from apps.tenant.api.base import BaseTenantViewSet
from apps.tenant.api.mixins import SintelDSVMixin
from apps.tenant.api.permissions import (
    HasOrganizationalScope,
    IsTenantAdminOrReadOnly,
    IsTenantMember,
)
from apps.tenant.compras.models import OrdenCompra, PlantillaOrdenCompra, RecepcionCompra
from apps.tenant.compras.services import (
    OrdenCompraBusinessService,
    OrdenCompraServiceMixin,
    PlantillaOrdenCompraServiceMixin,
    RecepcionCompraBusinessService,
    RecepcionCompraServiceMixin,
)
from apps.tenant.core.services.organizational_context import OrganizationalContextMixin

from .serializers import (
    OrdenCompraCreateUpdateSerializer,
    OrdenCompraDetailSerializer,
    OrdenCompraListSerializer,
    PlantillaOrdenCompraSerializer,
    RecepcionCompraCreateSerializer,
    RecepcionCompraDetailSerializer,
    RecepcionCompraListSerializer,
)

logger = logging.getLogger(__name__)


class OrdenCompraViewSet(OrganizationalContextMixin, OrdenCompraServiceMixin, SintelDSVMixin, BaseTenantViewSet):
    """
    ViewSet para la gestion de Ordenes de Compra.

    Fase 9 (OCF): OrganizationalContextMixin adoptado de forma aditiva. A
    diferencia de las apps anteriores de esta fase, aqui SI hereda
    SintelDSVMixin (piloto ADR-003) - get_empresa_id()/get_sede_id() son la
    misma SSoT que OrganizationalContext.resolve() duplica (Fase 2), sin la
    divergencia de las demas apps. Aun asi get_queryset() no se migro a
    context.filter(): get_qs_list() (Fase F5, OSF) ya aplica un filtro
    scope-aware mas especifico (alcance SEDE/AREA => conjunto COMPLETO de
    sedes/areas permitidas, via OrganizationalScope) que el generico de
    context.filter() (que solo resuelve la sede ACTIVA, una sola), y con
    .only()/select_related propios del selector - migrar seria un cambio de
    comportamiento real, no solo de mecanismo.
    """
    queryset = OrdenCompra.objects.none()
    serializer_class = OrdenCompraDetailSerializer
    service_class = OrdenCompraBusinessService
    http_method_names = ['get', 'post', 'put', 'patch', 'delete', 'head', 'options']

    pagination_class = StandardResultsSetPagination
    parser_classes = [JSONParser, FormParser, MultiPartParser]
    renderer_classes = [JSONRenderer]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["estado", "proveedor__numero_documento"]
    search_fields = ["consecutivo", "proveedor__razon_social", "observaciones"]
    ordering_fields = ["fecha", "total", "created_at"]
    ordering = ["-fecha", "-consecutivo"]

    def get_permissions(self):
        # [ADR-003] HasOrganizationalScope: prueba de concepto de permisos
        # con alcance organizacional (Fase 6). Solo aplicado aqui (no en
        # PlantillaOrdenCompraViewSet ni en las otras 16 apps) porque
        # Plantilla no es SedeAwareModel.
        return [IsTenantMember(), IsTenantAdminOrReadOnly(), HasOrganizationalScope()]

    def get_queryset(self):
        """Usa el selector para obtener QuerySet optimizado."""
        if not hasattr(self, 'action') or self.action is None:
            return OrdenCompra.objects.none()

        if self.action == "list":
            return self.get_qs_list()

        return self.get_qs_detail()

    def get_serializer_class(self):
        if self.action == "list":
            return OrdenCompraListSerializer
        if self.action in ["create", "update", "partial_update"]:
            return OrdenCompraCreateUpdateSerializer
        return OrdenCompraDetailSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        try:
            context['empresa_id'] = self.get_empresa_id()
        except Exception:
            context['empresa_id'] = None
        return context

    def create(self, request, *args, **kwargs):
        """Crea una Orden de Compra usando Service Layer."""
        try:
            empresa = self._get_empresa()
            if not empresa:
                return Response(
                    {"error": "empresa_no_configurada", "message": "No se pudo determinar la empresa activa."},
                    status=status.HTTP_403_FORBIDDEN
                )

            # WARNING: [SEC-M6] Solo nombres de campo, no valores (datos de proveedor/monto).
            _campos = list(request.data.keys()) if hasattr(request.data, 'keys') else type(request.data).__name__
            logger.info(f"[OrdenCompraViewSet:create] Campos recibidos: {_campos}")

            serializer = OrdenCompraCreateUpdateSerializer(
                data=request.data, context={'empresa_id': empresa.id}
            )
            serializer.is_valid(raise_exception=True)

            validated_data = serializer.validated_data
            items_data = validated_data.pop('items')

            success, result, status_code = self.service_crear_orden_compra(
                validated_data, items_data, empresa
            )
            if not success:
                logger.warning(f"[OrdenCompraViewSet:create] Fallo creacion: {result}")
                return Response(result, status=status_code)

            out_serializer = OrdenCompraDetailSerializer(result)
            return Response(out_serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            # Hallazgo UI/UX (piloto Compras): serializer.is_valid(raise_exception=True)
            # caia en el except generico de abajo y devolvia 500 "error_interno" con el
            # traceback de Python expuesto, en vez de 400 con los errores de campo reales
            # (items vacios, fecha_entrega invalida). Viola CLAUDE.md ("no mostrar
            # ValidationError/Traceback al usuario final").
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error en OrdenCompraViewSet.create: {e}", exc_info=True)
            return Response(
                {"error": "error_interno", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def update(self, request, *args, **kwargs):
        """Actualiza una Orden de Compra usando Service Layer."""
        try:
            instance = self.get_object()
            empresa_id = self.get_empresa_id()

            serializer = OrdenCompraCreateUpdateSerializer(
                data=request.data, context={'empresa_id': empresa_id}, partial=True
            )
            serializer.is_valid(raise_exception=True)

            validated_data = serializer.validated_data
            items_data = validated_data.pop('items', None)

            success, result, status_code = self.service_actualizar_orden_compra(
                instance.uuid, validated_data, items_data
            )
            if not success:
                logger.warning(f"[OrdenCompraViewSet:update] Fallo actualizacion: {result}")
                return Response(result, status=status_code)

            out_serializer = OrdenCompraDetailSerializer(result)
            return Response(out_serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return self.handle_service_error(e)

    def destroy(self, request, *args, **kwargs):
        """Elimina fisicamente una Orden de Compra en estado Borrador."""
        try:
            instance = self.get_object()
            success, result, status_code = self.service_eliminar_orden_compra(instance.uuid)
            if not success:
                return Response(result, status=status_code)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return self.handle_service_error(e)

    @action(detail=True, methods=["post"], url_path="cambiar-estado")
    def cambiar_estado(self, request, uuid=None):
        """Cambia el estado de una Orden de Compra."""
        try:
            nuevo_estado = request.data.get('estado')
            if not nuevo_estado:
                return Response(
                    {"detail": "Debe especificar el nuevo estado."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            success, result, status_code = self.service_cambiar_estado(uuid, nuevo_estado)
            if not success:
                return Response(result, status=status_code)

            out_serializer = OrdenCompraDetailSerializer(result)
            return Response(out_serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return self.handle_service_error(e)

    @action(detail=False, methods=["get"], url_path="siguiente-consecutivo")
    def siguiente_consecutivo(self, request):
        """Obtiene el siguiente consecutivo de la empresa."""
        try:
            consecutivo = self.service_get_siguiente_consecutivo()
            return Response({"siguiente_consecutivo": consecutivo}, status=status.HTTP_200_OK)
        except Exception as e:
            return self.handle_service_error(e)

    # --- Acciones de Renderizado (UI/HTMX) ---

    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='render-offcanvas/crear')
    def render_offcanvas_crear(self, request):
        """Renderiza offcanvas para crear."""
        import datetime

        from apps.tenant.compras.services.selectors import PlantillaOrdenCompraSelector
        empresa = self._get_empresa()
        fecha_default = datetime.date.today().isoformat()
        
        # Consultamos las plantillas vigentes del tenant
        plantillas = PlantillaOrdenCompraSelector.get_list(empresa_id=empresa.id, vigente_only=True)

        context = {
            'offcanvas_id': 'offcanvas-compra-crear',
            'mode': 'create',
            'plantillas': plantillas,
            'fecha_default': fecha_default,
        }
        return Response(context, template_name='tenant/compras/offcanvas_crear_compras.html')

    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='render-offcanvas/editar')
    def render_offcanvas_editar(self, request):
        """Renderiza offcanvas para editar."""
        uuid_val = request.query_params.get('uuid') or request.query_params.get('id')
        empresa_id = self.get_empresa_id()
        if not uuid_val:
            return Response({"error": "ID requerido"}, status=status.HTTP_400_BAD_REQUEST)

        instance = get_object_or_404(OrdenCompra, uuid=uuid_val, empresa_id=empresa_id)
        # [FASE 7, consolidacion OCF/OSF] get_object_or_404() no dispara
        # check_object_permissions() como self.get_object() -- HasOrganizationalScope
        # nunca se evaluaba para esta accion. Se invoca explicitamente aqui
        # (mismo efecto que self.get_object(), sin depender de self.kwargs
        # porque esta es una accion detail=False con uuid en query_params).
        self.check_object_permissions(request, instance)

        context = {
            'instance': instance,
            'offcanvas_id': 'offcanvas-compra-editar',
            'mode': 'edit',
        }
        return Response(context, template_name='tenant/compras/offcanvas_editar_compras.html')

    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='render-offcanvas/detalle')
    def render_offcanvas_detalle(self, request):
        """Renderiza offcanvas de detalle."""
        uuid_val = request.query_params.get('uuid') or request.query_params.get('id')
        empresa_id = self.get_empresa_id()
        if not uuid_val:
            return Response({"error": "ID requerido"}, status=status.HTTP_400_BAD_REQUEST)

        instance = get_object_or_404(OrdenCompra, uuid=uuid_val, empresa_id=empresa_id)
        # [FASE 7, consolidacion OCF/OSF] ver nota identica en render_offcanvas_editar().
        self.check_object_permissions(request, instance)
        return Response({'instance': instance, 'offcanvas_id': 'offcanvas-compra-detalle'}, template_name='tenant/compras/offcanvas_detalle_compras.html')


class PlantillaOrdenCompraViewSet(OrganizationalContextMixin, PlantillaOrdenCompraServiceMixin, SintelDSVMixin, BaseTenantViewSet):
    """
    ViewSet para la gestion de Plantillas de Orden de Compra.
    """
    queryset = PlantillaOrdenCompra.objects.none()
    serializer_class = PlantillaOrdenCompraSerializer
    lookup_field = "uuid"
    lookup_url_kwarg = "uuid"
    pagination_class = StandardResultsSetPagination
    parser_classes = [JSONParser, FormParser, MultiPartParser]
    renderer_classes = [JSONRenderer]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["nombre", "vigente", "created_at"]
    ordering = ["-vigente", "-created_at"]

    def get_permissions(self):
        return [IsTenantMember(), IsTenantAdminOrReadOnly()]

    def get_queryset(self):
        if not hasattr(self, 'action') or self.action is None:
            return PlantillaOrdenCompra.objects.none()

        vigente_only = self.request.query_params.get('vigente') == 'true'
        if self.action == "list":
            return self.get_qs_list(vigente_only=vigente_only)

        uuid_val = self.kwargs.get(self.lookup_url_kwarg)
        return self.get_qs_detail(uuid_val)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        try:
            context['empresa_id'] = self.get_empresa_id()
        except Exception:
            context['empresa_id'] = None
        return context

    def get_object(self):
        uuid_val = self.kwargs.get(self.lookup_url_kwarg)
        empresa_id = self.get_empresa_id()
        obj = PlantillaOrdenCompra.objects.filter(uuid=uuid_val, empresa_id=empresa_id).first()
        if not obj:
            from rest_framework.exceptions import NotFound
            raise NotFound("Plantilla no encontrada en su organizacion.")
        self.check_object_permissions(self.request, obj)
        return obj

    def create(self, request, *args, **kwargs):
        empresa = self._get_empresa()
        if not empresa:
            return Response(
                {"detail": "No se pudo determinar la empresa activa."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        plantilla = self.service_crear_plantilla(empresa, serializer.validated_data)
        out = self.get_serializer(plantilla)
        return Response(out.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        uuid_val = self.kwargs.get(self.lookup_url_kwarg)
        serializer = self.get_serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        plantilla = self.service_actualizar_plantilla(uuid_val, serializer.validated_data)
        out = self.get_serializer(plantilla)
        return Response(out.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='render-offcanvas/crear')
    def render_offcanvas_crear(self, request):
        return Response(
            {'offcanvas_id': 'offcanvas-plantilla-crear'},
            template_name='tenant/compras/offcanvas_crear_plantilla.html'
        )


class RecepcionCompraViewSet(OrganizationalContextMixin, RecepcionCompraServiceMixin, SintelDSVMixin, BaseTenantViewSet):
    """
    ViewSet para Recepcion de Compras (F21): OrdenCompra -> RecepcionCompra ->
    MovimientoInventario. Solo API (sin renderizado de offcanvas HTMX -
    reduccion de alcance documentada en documentacion/F21_RECEPCION_INVENTARIO.md,
    consistente con la decision de no construir frontend nuevo en esta fase).
    """
    queryset = RecepcionCompra.objects.none()
    serializer_class = RecepcionCompraDetailSerializer
    service_class = RecepcionCompraBusinessService
    http_method_names = ['get', 'post', 'head', 'options']

    pagination_class = StandardResultsSetPagination
    parser_classes = [JSONParser, FormParser, MultiPartParser]
    renderer_classes = [JSONRenderer]

    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["estado"]
    ordering_fields = ["fecha", "created_at"]
    ordering = ["-fecha", "-id"]

    def get_permissions(self):
        # Mismo piloto de alcance organizacional que OrdenCompraViewSet:
        # RecepcionCompra hereda SedeAwareModel igual que su orden padre.
        return [IsTenantMember(), IsTenantAdminOrReadOnly(), HasOrganizationalScope()]

    def get_queryset(self):
        if not hasattr(self, 'action') or self.action is None:
            return RecepcionCompra.objects.none()
        if self.action == "list":
            orden_uuid = self.request.query_params.get('orden_compra')
            estado = self.request.query_params.get('estado')
            return self.get_qs_list(orden_compra_uuid=orden_uuid, estado=estado)
        uuid_val = self.kwargs.get(self.lookup_url_kwarg or self.lookup_field)
        return self.get_qs_detail(uuid_val)

    def get_serializer_class(self):
        if self.action == "list":
            return RecepcionCompraListSerializer
        if self.action == "create":
            return RecepcionCompraCreateSerializer
        return RecepcionCompraDetailSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        try:
            context['empresa_id'] = self.get_empresa_id()
        except Exception:
            context['empresa_id'] = None
        return context

    def create(self, request, *args, **kwargs):
        """Crea una RecepcionCompra en BORRADOR (sin efecto en stock todavia)."""
        try:
            empresa = self._get_empresa()
            if not empresa:
                return Response(
                    {"error": "empresa_no_configurada", "message": "No se pudo determinar la empresa activa."},
                    status=status.HTTP_403_FORBIDDEN
                )

            serializer = RecepcionCompraCreateSerializer(
                data=request.data, context={'empresa_id': empresa.id}
            )
            serializer.is_valid(raise_exception=True)

            validated_data = serializer.validated_data
            items_data = validated_data.pop('items')

            success, result, status_code = self.service_crear_recepcion(
                validated_data, items_data, empresa
            )
            if not success:
                logger.warning(f"[RecepcionCompraViewSet:create] Fallo creacion: {result}")
                return Response(result, status=status_code)

            out_serializer = RecepcionCompraDetailSerializer(result)
            return Response(out_serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return self.handle_service_error(e)

    @action(detail=True, methods=["post"], url_path="confirmar")
    def confirmar(self, request, uuid=None):
        """Confirma la recepcion: genera MovimientoInventario y actualiza la orden."""
        try:
            success, result, status_code = self.service_confirmar_recepcion(uuid)
            if not success:
                return Response(result, status=status_code)
            out_serializer = RecepcionCompraDetailSerializer(result)
            return Response(out_serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return self.handle_service_error(e)

    @action(detail=True, methods=["post"], url_path="anular")
    def anular(self, request, uuid=None):
        """Anula una recepcion en Borrador (sin efecto en stock aun)."""
        try:
            success, result, status_code = self.service_anular_recepcion(uuid)
            if not success:
                return Response(result, status=status_code)
            out_serializer = RecepcionCompraDetailSerializer(result)
            return Response(out_serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return self.handle_service_error(e)
