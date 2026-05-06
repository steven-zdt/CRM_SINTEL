"""
ViewSets DRF para gastos (JSON-only).

v2.40: INMUTABILIDAD ESTRICTA y SSoT Empresa.
- Los campos de listado usan prefijos 'ds_' alineados con GastoListSerializer.
- POST solo para crear nuevos gastos (Inmutabilidad legal).
- Acción 'anular' implementada para revertir efectos financieros.
"""
import logging
from decimal import Decimal

from django.core.exceptions import ValidationError
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from rest_framework.response import Response

from apps.config.api.pagination import StandardResultsSetPagination
from apps.tenant.api.base import BaseTenantGenericViewSet, BaseTenantViewSet
from apps.tenant.api.mixins import SintelDSVMixin, SintelServiceMixin
from apps.tenant.api.permissions import IsTenantAdminOrReadOnly, IsTenantMember
from apps.tenant.api.utils import resolve_tenant_empresa
from apps.tenant.gastos.choices.niif_gastos_choices import GASTOS_NIIF_CHOICES
from apps.tenant.gastos.models import Gasto, ResolucionDIAN
from apps.tenant.gastos.services import (
    GastoServiceMixin,  # v2.61: Service Layer Pattern
    ResolucionServiceMixin,
    anular_gasto_service,
    calcular_retenciones,  # v2.40: Función para calcular retenciones
    crear_resolucion,
    desactivar_gasto_service,  # v2.40: Función para desactivar gasto
    desactivar_resolucion,
    get_gastos_summary,
    obtener_resolucion_vigente,
    puede_eliminar_resolucion,
    qs_detail,
    qs_list,
    qs_resolucion_detail,
    qs_resolucion_list,
)

from .serializers import (
    GastoDetailSerializer,
    GastoListSerializer,
    ResolucionDIANDetailSerializer,
    ResolucionDIANListSerializer,
    ResolucionDIANNestedSerializer,
)

logger = logging.getLogger(__name__)

class GastoViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    SintelDSVMixin,
    GastoServiceMixin,  # Inyección de dependencias DDD
    BaseTenantGenericViewSet
):
    """
    ViewSet para gastos (v2.40).
    Prohíbe PUT/PATCH para garantizar integridad del Documento Soporte.
    
    WARNING: CRÍTICO: El queryset debe estar definido en tiempo de clase para que DRF
    pueda registrar las rutas correctamente. Se sobrescribe en get_queryset()
    para optimización según la acción.
    """
    # WARNING: CRÍTICO: queryset requerido por DRF para registro de rutas
    # Se usa get_queryset() para optimización, .none() es suficiente para DRF
    queryset = Gasto.objects.none()
    serializer_class = GastoDetailSerializer  # WARNING: CRÍTICO: DRF necesita serializer_class para generar rutas (se sobrescribe en get_serializer_class())
    pagination_class = StandardResultsSetPagination  # WARNING: v2.40: Paginación para Tabulator
    http_method_names = ['get', 'post', 'delete', 'head', 'options'] # Bloquea PUT/PATCH
    
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
    parser_classes = [JSONParser, FormParser, MultiPartParser]
    renderer_classes = [JSONRenderer]
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["periodo", "centro_costo", "categoria_contable"]
    search_fields = ["descripcion", "documento_soporte__vendedor_nombre", "documento_soporte__prefijo"]
    ordering_fields = ["documento_soporte__fecha", "documento_soporte__total"]
    ordering = ["-documento_soporte__fecha"]

    def get_queryset(self):
        """
        Usa las funciones del service layer para optimizar el QuerySet.
        
        WARNING: CRÍTICO: Este método sobrescribe el queryset de clase para optimización.
        Si no hay acción definida (tiempo de registro), retorna queryset vacío.
        WARNING: v2.40: Soporta búsqueda con parámetro ?search=
        
        WARNING: CRÍTICO: INCLUYE TODOS LOS DOCUMENTOS (anulados y no anulados).
        - Los documentos anulados DEBEN aparecer en la lista para mantener la secuencia de consecutivos.
        - El consecutivo prevalece en la lista, incluso si el documento está anulado.
        - Solo el summary (get_gastos_summary) excluye documentos anulados del cálculo financiero.
        """
        # Si no hay acción (tiempo de registro de rutas), retornar queryset vacío
        if not hasattr(self, 'action') or self.action is None:
            return Gasto.objects.none()
        
        if self.action == "list":
            return self.get_qs_list()
        elif self.action == "retrieve":
            return self.get_qs_detail()
        else:
            # Fallback estricto por tenant para mutaciones (anular, desactivar)
            empresa_id = self.get_empresa_id()
            return Gasto.objects.filter(empresa_id=empresa_id)

    def get_serializer_class(self):
        """Alineación v2.40: ListSerializer usa campos aplanados 'ds_'."""
        if self.action == "list":
            return GastoListSerializer
        return GastoDetailSerializer
    
    def list(self, request, *args, **kwargs):
        """
        GET /api/v1/gastos/
        Lista paginada de gastos (Tabulator v2.40).
        Soporta ?search= para búsqueda y ?page= para paginación.
        """
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    def create(self, request, *args, **kwargs):
        """
        Crea un nuevo Gasto con DocumentoSoporte.
        
        WARNING: v2.61: Service Layer & Zero-Waste Lock Aplicados.
        Toda la lógica de negocio, validación matemática de retenciones y atomicidad 
        ha sido encapsulada en GastoServiceMixin.crear_gasto_service().
        """
        try:
            # SSoT: Obtener empresa del tenant
            empresa = resolve_tenant_empresa(request, self)
            if not empresa:
                return Response(
                    {
                        "error": "empresa_no_configurada",
                        "message": "No se pudo determinar la empresa activa para este tenant.",
                        "missing_fields": ["empresa"]
                    },
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # DDD: Inyección y delegación al Service Layer
            success, result, status_code = self.crear_gasto_service(request.data.copy(), empresa)
            
            if not success:
                return Response(result, status=status_code)
                
            serializer = self.get_serializer(result)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error fatal en GastoViewSet.create: {e}", exc_info=True)
            return Response(
                {"error": "error_interno", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=["post"], url_path="desactivar")
    def desactivar(self, request, pk=None):
        """
        Acción para desactivar un gasto (v2.40).
        
        WARNING: REGLA CRÍTICA: Paso previo obligatorio antes de anular.
        El documento debe estar desactivado para poder anularlo.
        """
        try:
            gasto = self.get_object()
            resultado = self.service_desactivar_gasto(gasto)
            return Response({"detail": "Gasto desactivado correctamente"}, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error desactivando gasto {pk}: {str(e)}")
            return Response({"detail": "Error interno al desactivar"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=["post"], url_path="anular")
    def anular(self, request, pk=None):
        """
        Acción para anular un gasto (v2.40).
        
        WARNING: REGLA CRÍTICA: Solo se puede anular si está desactivado (activo=False).
        Utiliza el service layer para garantizar atomicidad e inmutabilidad.
        """
        try:
            gasto = self.get_object()
            # WARNING: REGLA: No se puede editar, solo anular a través del service
            resultado = self.service_anular_gasto(gasto)
            return Response({"detail": "Gasto anulado correctamente"}, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error anulando gasto {pk}: {str(e)}")
            return Response({"detail": "Error interno al anular"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        """
        Obtiene resumen financiero neto excluyendo documentos anulados.
        
        WARNING: v2.40: REGLA CRÍTICA - Documentos con anulado=True => Valor 0.
        Solo suma documentos no anulados para mantener integridad contable.
        
        Returns:
            {
                "subtotal_neto": Decimal,
                "retenciones_neto": Decimal,  # Suma de retefuente + reteica
                "total_neto": Decimal,
                "cantidad": int
            }
        """
        try:
            # Obtener empresa del tenant (Zero-Trust)
            empresa = resolve_tenant_empresa(request, self)
            empresa_id = empresa.id if empresa else None
            
            if not empresa_id:
                return Response(
                    {"error": "empresa_no_encontrada", "message": "No se pudo determinar la empresa activa."},
                    status=status.HTTP_403_FORBIDDEN
                )

            summary_data = get_gastos_summary(empresa_id=empresa_id)
            
            # Convertir Decimal a string para JSON (si es necesario)
            def decimal_to_str(d):
                if isinstance(d, dict):
                    return {k: str(v) if isinstance(v, Decimal) else v for k, v in d.items()}
                return d
            
            summary_serialized = decimal_to_str(summary_data)
            
            return Response(summary_serialized, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error calculando resumen de gastos: {e}", exc_info=True)
            return Response(
                {"error": "error_calculando_resumen", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=["post"], url_path="validar-financieros")
    def validar_financieros(self, request):
        """
        Valida y calcula retenciones de forma server-side para el formulario de gastos.
        """
        try:
            subtotal = Decimal(str(request.data.get('subtotal') or 0))
            retefuente_porcentaje = str(request.data.get('retefuente_porcentaje') or 0)
            reteica_porcentaje = str(request.data.get('reteica_porcentaje') or 0)

            retenciones = calcular_retenciones(
                subtotal=subtotal,
                retefuente_porcentaje=retefuente_porcentaje,
                reteica_porcentaje=reteica_porcentaje,
            )

            return Response(
                {
                    "subtotal": str(subtotal),
                    "retefuente": str(retenciones['retefuente']),
                    "reteica": str(retenciones['reteica']),
                    "total": str(retenciones['total']),
                    "ok": True,
                },
                status=status.HTTP_200_OK,
            )
        except ValidationError as e:
            return Response(
                {"detail": str(e), "ok": False},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.error("[gastos:validar_financieros] error inesperado: %s", str(e), exc_info=True)
            return Response(
                {"detail": "Error interno al validar financieros.", "ok": False},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["get"], url_path="resoluciones")
    def resoluciones(self, request):
        """
        Retorna todas las resoluciones DIAN disponibles para el formulario de creación.
        
        WARNING: v2.60: Actualizado para retornar TODAS las resoluciones (no solo vigentes)
        para que el usuario pueda seleccionar entre todas las disponibles.
        """
        empresa = resolve_tenant_empresa(request, self)
        if not empresa:
            return Response(
                {"error": "empresa_no_configurada", "message": "No se pudo determinar la empresa activa."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # WARNING: v2.60: Retornar TODAS las resoluciones de la empresa (no solo vigentes)
        resoluciones = ResolucionDIAN.objects.filter(empresa=empresa).order_by('-vigente', '-fecha_resolucion')
        serializer = ResolucionDIANNestedSerializer(resoluciones, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=["get"], url_path="resolucion-activa")
    def resolucion_activa(self, request):
        """
        Retorna la resolución DIAN vigente para la empresa del tenant.
        
        WARNING: v2.40: SSoT - Solo una resolución vigente por empresa.
        Si no existe, retorna 404 para que el frontend abra el modal de configuración.
        """
        try:
            # Obtener empresa del tenant (SSoT)
            empresa = resolve_tenant_empresa(request, self)
            
            if not empresa:
                return Response(
                    {"error": "empresa_no_configurada", "message": "No se pudo determinar la empresa activa."},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            resolucion = ResolucionDIAN.objects.filter(
                empresa=empresa,
                vigente=True
            ).first()
            
            if not resolucion:
                return Response(
                    {"error": "resolucion_no_configurada", "message": "No hay resolución DIAN configurada."},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            serializer = ResolucionDIANNestedSerializer(resolucion)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error obteniendo resolución activa: {e}", exc_info=True)
            return Response(
                {"error": "error_interno", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='gestor-offcanvas')
    def gestor_offcanvas(self, request):
        """
        Endpoint HTMX para cargar offcanvas de gastos (crear o detalle).
        
        WARNING: v2.60: Feature-Sliced Architecture - Templates separados por acción
        - Modo creación: offcanvas_crear.html
        - Modo detalle: offcanvas_detalle.html
        
        Query params:
        - id: ID del gasto (opcional, si no se proporciona es modo creación)
        - mode: 'create' o 'detail' (opcional, si no se proporciona se infiere de 'id')
        
        Returns:
            Template HTML renderizado según el modo
        """
        gasto_id = request.query_params.get('id')
        mode = request.query_params.get('mode', 'create' if not gasto_id else 'detail')
        context = {}
        
        if mode == 'detail' and gasto_id:
            try:
                # Modo detalle: cargar gasto
                empresa = resolve_tenant_empresa(request, self)
                if not empresa:
                    context['error'] = "No se pudo determinar la empresa activa."
                    return Response(context, template_name='tenant/core/gastos/offcanvas_detalle.html', status=status.HTTP_403_FORBIDDEN)
                
                # Zero Waste: only() carga solo lo necesario para el visualizador
                gasto = Gasto.objects.select_related('documento_soporte', 'documento_soporte__resolucion').filter(
                    documento_soporte__empresa=empresa,
                    id=gasto_id
                ).only(
                    'id',
                    'categoria_contable',
                    'centro_costo',
                    'descripcion',
                    'periodo',
                    'documento_soporte__prefijo',
                    'documento_soporte__consecutivo',
                    'documento_soporte__fecha',
                    'documento_soporte__vendedor_nombre',
                    'documento_soporte__vendedor_nit',
                    'documento_soporte__subtotal',
                    'documento_soporte__retefuente',
                    'documento_soporte__retefuente_porcentaje',
                    'documento_soporte__reteica',
                    'documento_soporte__reteica_porcentaje',
                    'documento_soporte__total',
                    'documento_soporte__activo',
                    'documento_soporte__anulado',
                ).first()
                
                if not gasto:
                    context['error'] = "Gasto no encontrado o no pertenece a este tenant."
                    return Response(context, template_name='tenant/core/gastos/offcanvas_detalle.html')
                
                context['gasto'] = gasto
                return Response(context, template_name='tenant/core/gastos/offcanvas_detalle.html')
                
            except Gasto.DoesNotExist:
                logger.warning(f"Gasto {gasto_id} no encontrado para Offcanvas.")
                context['error'] = "Gasto no encontrado."
                return Response(context, template_name='tenant/core/gastos/offcanvas_detalle.html', status=status.HTTP_404_NOT_FOUND)
            except Exception as e:
                logger.exception(f"Error al obtener gasto para Offcanvas: {e}")
                context['error'] = "No se pudo cargar el gasto."
                return Response(context, template_name='tenant/core/gastos/offcanvas_detalle.html', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            # Modo creación
            context['gasto'] = None
            context['GASTOS_NIIF_CHOICES'] = GASTOS_NIIF_CHOICES
            return Response(context, template_name='tenant/core/gastos/offcanvas_crear.html')
    
    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='render-offcanvas/crear')
    def render_offcanvas_crear(self, request):
        """
        Endpoint HTMX RESTful para cargar offcanvas de creación de gastos.
        
        WARNING: v2.60: Feature-Sliced Architecture - Template dedicado para creación
        - GET /api/v1/gastos/render-offcanvas/crear/ → Modo creación
        
        Returns:
            Template HTML: tenant/core/gastos/offcanvas_crear.html
        """
        context = {
            'gasto': None,
            'GASTOS_NIIF_CHOICES': GASTOS_NIIF_CHOICES
        }
        return Response(context, template_name='tenant/core/gastos/offcanvas_crear.html')
    
    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='render-offcanvas/resolucion')
    def render_offcanvas_resolucion(self, request):
        """
        Endpoint HTMX RESTful para cargar offcanvas de configuración de resolución DIAN.
        
        WARNING: v2.60: Feature-Sliced Architecture - Template dedicado para configuración
        - GET /api/v1/gastos/render-offcanvas/resolucion/ → Modo configuración
        
        Returns:
            Template HTML: tenant/core/gastos/offcanvas_resolucion.html
        """
        context = {}
        return Response(context, template_name='tenant/core/gastos/offcanvas_resolucion.html')
    
    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='render-offcanvas/detalle')
    def render_offcanvas_detalle(self, request):
        """
        Endpoint HTMX RESTful para cargar offcanvas de detalle de gastos.
        
        WARNING: v2.60: Feature-Sliced Architecture - Template dedicado para detalle
        - GET /api/v1/gastos/render-offcanvas/detalle/?id=123 → Modo detalle
        
        Query params:
        - id: ID del gasto (requerido)
        
        Returns:
            Template HTML: tenant/core/gastos/offcanvas_detalle.html
        """
        gasto_id = request.query_params.get('id')
        context = {}
        
        if not gasto_id:
            context['error'] = "Se requiere el parámetro 'id' para el modo detalle."
            return Response(context, template_name='tenant/core/gastos/offcanvas_detalle.html', status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Modo detalle: cargar gasto
            empresa = resolve_tenant_empresa(request, self)
            if not empresa:
                context['error'] = "No se pudo determinar la empresa activa."
                return Response(context, template_name='tenant/core/gastos/offcanvas_detalle.html', status=status.HTTP_403_FORBIDDEN)
            
            # Zero Waste: only() carga solo lo necesario para el visualizador
            gasto = Gasto.objects.select_related('documento_soporte', 'documento_soporte__resolucion').filter(
                documento_soporte__empresa=empresa,
                id=gasto_id
            ).only(
                'id',
                'categoria_contable',
                'centro_costo',
                'descripcion',
                'periodo',
                'documento_soporte__prefijo',
                'documento_soporte__consecutivo',
                'documento_soporte__fecha',
                'documento_soporte__vendedor_nombre',
                'documento_soporte__vendedor_nit',
                'documento_soporte__subtotal',
                'documento_soporte__retefuente',
                'documento_soporte__retefuente_porcentaje',
                'documento_soporte__reteica',
                'documento_soporte__reteica_porcentaje',
                'documento_soporte__total',
                'documento_soporte__activo',
                'documento_soporte__anulado',
            ).first()
            
            if not gasto:
                context['error'] = "Gasto no encontrado o no pertenece a este tenant."
                return Response(context, template_name='tenant/core/gastos/offcanvas_detalle.html')
            
            context['gasto'] = gasto
            return Response(context, template_name='tenant/core/gastos/offcanvas_detalle.html')
            
        except Gasto.DoesNotExist:
            logger.warning(f"Gasto {gasto_id} no encontrado para Offcanvas.")
            context['error'] = "Gasto no encontrado."
            return Response(context, template_name='tenant/core/gastos/offcanvas_detalle.html', status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.exception(f"Error al obtener gasto para Offcanvas: {e}")
            context['error'] = "No se pudo cargar el gasto."
            return Response(context, template_name='tenant/core/gastos/offcanvas_detalle.html', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=["post"], url_path="configurar-resolucion")
    def configurar_resolucion(self, request):
        """
        Crea o actualiza una resolución DIAN para la empresa del tenant.
        
        WARNING: v2.60: CORRECCIÓN - Usa ResolucionDIANCreateSerializer para manejar valores de checkbox HTML.
        WARNING: v2.40: SSoT - Solo una resolución vigente por empresa.
        Si se marca como vigente, desactiva automáticamente las anteriores.
        """
        try:
            from django.db import transaction
            from .serializers import ResolucionDIANCreateSerializer

            empresa = resolve_tenant_empresa(request, self)
            
            if not empresa:
                return Response(
                    {"error": "empresa_no_configurada", "message": "No se pudo determinar la empresa activa."},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # WARNING: v2.60: Usar serializer para validación y manejo de valores HTML
            data = request.data.copy()
            data['empresa'] = empresa.id
            
            # WARNING: CORRECCIÓN: El serializer maneja el valor "on" del checkbox
            serializer = ResolucionDIANCreateSerializer(data=data)
            
            if not serializer.is_valid():
                # WARNING: v2.60: Formatear errores para Error Injector
                error_details = {}
                for field, errors in serializer.errors.items():
                    error_details[field] = errors[0] if isinstance(errors, list) else str(errors)
                
                return Response(
                    {
                        "error": "validacion_error",
                        "message": "Error de validación en los datos proporcionados.",
                        "details": error_details,
                        "missing_fields": list(error_details.keys())
                    },
                    status=status.HTTP_422_UNPROCESSABLE_ENTITY
                )
            
            validated_data = serializer.validated_data
            vigente = validated_data.get('vigente', True)
            
            # WARNING: v2.60: El serializer ya validó y parseó todos los campos
            fecha_resolucion = validated_data['fecha_resolucion']
            fecha_fin = validated_data['fecha_fin']
            
            with transaction.atomic():
                # Si se marca como vigente, desactivar las anteriores
                if vigente:
                    ResolucionDIAN.objects.filter(
                        empresa=empresa,
                        vigente=True
                    ).update(vigente=False)
                
                # WARNING: v2.60: Crear nueva resolución usando datos validados del serializer
                resolucion = ResolucionDIAN(
                    empresa=empresa,
                    numero_resolucion=validated_data['numero_resolucion'],
                    prefijo=validated_data['prefijo'],
                    rango_desde=validated_data['rango_desde'],
                    rango_hasta=validated_data['rango_hasta'],
                    fecha_resolucion=fecha_resolucion,
                    fecha_inicio=fecha_resolucion,  # WARNING: Usar fecha_resolucion como fecha_inicio
                    fecha_fin=fecha_fin,
                    clave_tecnica=validated_data.get('clave_tecnica', ''),
                    vigente=vigente
                )
                
                # WARNING: VALIDACIÓN: Llamar a full_clean() para ejecutar clean() del modelo
                resolucion.full_clean()
                resolucion.save()
                
                serializer = ResolucionDIANNestedSerializer(resolucion)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
                
        except ValidationError as e:
            return Response(
                {"error": "validacion_error", "message": str(e), "details": e.message_dict if hasattr(e, 'message_dict') else None},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error configurando resolución: {e}", exc_info=True)
            return Response(
                {"error": "error_interno", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ResolucionDIANViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    SintelDSVMixin,
    ResolucionServiceMixin,
    BaseTenantGenericViewSet
):
    """
    ViewSet para Resoluciones DIAN (v2.40).
    
    WARNING: INMUTABILIDAD: Las resoluciones son documentos legales y no deben editarse.
    - Bloquea PUT/PATCH (update/partial_update)
    - Solo permite CREATE, LIST, RETRIEVE, DESTROY
    - En DESTROY: valida que no tenga Documentos de Soporte asociados
    
    WARNING: REGLA CRÍTICA: Solo UNA resolución puede estar vigente por empresa.
    Si se crea una nueva como vigente, desactiva automáticamente las anteriores.
    
    WARNING: SNAPSHOT INALTERABLE: Al desactivar o eliminar una resolución,
    los Documentos de Soporte conservan su número y prefijo originales.
    """
    queryset = ResolucionDIAN.objects.none()  # Se sobrescribe en get_queryset()
    serializer_class = ResolucionDIANDetailSerializer
    pagination_class = StandardResultsSetPagination
    http_method_names = ['get', 'post', 'delete', 'head', 'options']  # Bloquea PUT/PATCH
    
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
    parser_classes = [JSONParser, FormParser, MultiPartParser]
    renderer_classes = [JSONRenderer]
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['numero_resolucion', 'prefijo']
    ordering_fields = ['fecha_resolucion', 'vigente', 'created_at']
    ordering = ['-vigente', '-fecha_resolucion']
    
    def get_empresa(self):
        """
        Obtiene la empresa del tenant actual (SSoT).
        
        WARNING: PERFORMANCE BIBLE: Usa .first() en lugar de .all()[0]
        Singleton pattern: Solo debe existir una empresa por tenant
        """
        empresa = resolve_tenant_empresa(self.request, self)
        if not empresa:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied(detail='No se pudo determinar la empresa activa para este tenant')
        return empresa
    
    def get_queryset(self):
        """
        QuerySet optimizado según la acción.
        
        WARNING: SSoT: Filtrado por empresa para aislamiento multi-tenant.
        """
        if not hasattr(self, 'action') or self.action is None:
            return ResolucionDIAN.objects.none()
        
        empresa = self.get_empresa()
        
        if self.action == "list":
            return self.get_qs_list()
        elif self.action == "retrieve":
            return self.get_qs_detail()
        else:
            empresa_id = self.get_empresa_id()
            return ResolucionDIAN.objects.filter(empresa_id=empresa_id)
    
    def get_serializer_class(self):
        """Alineación v2.40: ListSerializer para listado, DetailSerializer para detalle."""
        if self.action == "list":
            return ResolucionDIANListSerializer
        return ResolucionDIANDetailSerializer
    
    def list(self, request, *args, **kwargs):
        """
        GET /api/v1/resoluciones-dian/
        Lista paginada de resoluciones (Tabulator v2.40).
        """
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    def retrieve(self, request, *args, **kwargs):
        """
        GET /api/v1/resoluciones-dian/{id}/
        Obtiene detalle de una resolución.
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    def create(self, request, *args, **kwargs):
        """
        POST /api/v1/resoluciones-dian/
        Crea una nueva resolución DIAN.
        
        WARNING: REGLA CRÍTICA: Solo UNA resolución puede estar vigente por empresa.
        Si se marca como vigente, desactiva automáticamente las anteriores.
        """
        try:
            empresa = self.get_empresa()
            resultado = crear_resolucion(empresa, request.data)
            serializer = self.get_serializer(resultado)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response(
                {"error": "validacion_error", "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error creando resolución: {e}", exc_info=True)
            return Response(
                {"error": "error_interno", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def destroy(self, request, *args, **kwargs):
        """
        DELETE /api/v1/resoluciones-dian/{id}/
        Elimina una resolución DIAN.
        
        WARNING: REGLA: No se puede eliminar si tiene Documentos de Soporte asociados.
        Los documentos deben conservar su referencia a la resolución (evidencia legal).
        """
        try:
            empresa = self.get_empresa()
            resolucion_id = self.kwargs.get('pk')
            
            # Validar que se puede eliminar
            puede_eliminar, mensaje = puede_eliminar_resolucion(empresa, resolucion_id)
            
            if not puede_eliminar:
                return Response(
                    {"error": "resolucion_en_uso", "message": mensaje},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Obtener y eliminar
            resolucion = qs_resolucion_detail(empresa.id, resolucion_id)
            if not resolucion:
                return Response(
                    {"error": "resolucion_no_encontrada", "message": "Resolución no encontrada."},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            resolucion.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
            
        except Exception as e:
            logger.error(f"Error eliminando resolución: {e}", exc_info=True)
            return Response(
                {"error": "error_interno", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=["post"], url_path="desactivar")
    def desactivar(self, request, pk=None):
        """
        POST /api/v1/resoluciones-dian/{id}/desactivar/
        Desactiva una resolución DIAN (marca vigente=False).
        
        WARNING: INMUTABILIDAD: El DocumentoSoporte conserva su número y prefijo originales
        (snapshot inalterable). La desactivación no afecta documentos ya generados.
        """
        try:
            empresa = self.get_empresa()
            resultado = desactivar_resolucion(empresa, pk)
            serializer = self.get_serializer(resultado)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response(
                {"error": "validacion_error", "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error desactivando resolución {pk}: {str(e)}")
            return Response(
                {"error": "error_interno", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=["get"], url_path="activa")
    def activa(self, request):
        """
        GET /api/v1/resoluciones-dian/activa/
        Retorna la resolución DIAN vigente para la empresa del tenant.
        
        WARNING: v2.40: SSoT - Solo una resolución vigente por empresa.
        Si no existe, retorna 404 para que el frontend abra el modal de configuración.
        """
        try:
            empresa = self.get_empresa()
            resolucion = obtener_resolucion_vigente(empresa)
            
            if not resolucion:
                return Response(
                    {"error": "resolucion_no_configurada", "message": "No hay resolución DIAN configurada."},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            serializer = ResolucionDIANNestedSerializer(resolucion)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error obteniendo resolución activa: {e}", exc_info=True)
            return Response(
                {"error": "error_interno", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )