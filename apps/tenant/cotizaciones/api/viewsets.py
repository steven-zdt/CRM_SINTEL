"""
ViewSets para Cotizaciones v2.60 - Standalone & Resiliente
# WARNING: v2.60: Integración total con DNA Dinámico y Service Layer.
# WARNING: Tabulator Factory v2.40: Paginación remota y búsqueda en tiempo real.
# WARNING: Error Boundary Pattern: Todos los errores retornan JSON nativo (sin template_name).
"""
import logging
from decimal import Decimal

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Count, DecimalField, Q, Sum
from django.db.models.functions import Coalesce
from rest_framework import permissions, serializers, status
from rest_framework.decorators import action
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from rest_framework.response import Response

from apps.config.api.pagination import StandardResultsSetPagination
from apps.tenant.api.base import BaseTenantViewSet
from apps.tenant.api.permissions import IsTenantAdminOrReadOnly, IsTenantMember
from apps.tenant.empresa.models import Empresa

from ..models import Cotizacion, CotizacionItem
from ..services import CotizacionService
from ..services.api_mixins import CotizacionServiceMixin
from ..services.selectors import CotizacionSelector
from .serializers import (
    CotizacionItemSerializer,
    CotizacionListSerializer,
    CotizacionSerializer,
)

logger = logging.getLogger(__name__)

class CotizacionViewSet(CotizacionServiceMixin, BaseTenantViewSet):
    """
    ViewSet para Cotizaciones v2.60.
    
    # WARNING: Tabulator Factory v2.40:
    - Endpoint: GET /api/v1/cotizaciones/ con StandardResultsSetPagination
    - Soporte ?search= para búsqueda en tiempo real
    - Lookup por UUID para seguridad
    """
    lookup_field = 'uuid'
    queryset = Cotizacion.objects.none()
    serializer_class = CotizacionSerializer
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
    renderer_classes = [JSONRenderer]
    pagination_class = StandardResultsSetPagination

    def _resolve_empresa(self, request):
        """Resuelve empresa del tenant con fallback seguro al singleton del esquema."""
        empresa = getattr(request, 'empresa', None)
        if empresa:
            return empresa

        tenant = getattr(request, 'tenant', None)
        empresa = getattr(tenant, 'empresa', None)
        if empresa:
            return empresa

        return Empresa.objects.only('id').first()

    def get_queryset(self):
        """
        Filtrado por empresa del tenant actual via Selectors (Zero Waste).

        - list: CotizacionSelector.get_list() con .only() + select_related
        - retrieve: CotizacionSelector.get_detail() con prefetch_related('items')
        - mutations: queryset minimo filtrado por empresa
        """
        empresa = self._resolve_empresa(self.request)
        if not empresa:
            return Cotizacion.objects.none()

        if self.action == 'list':
            search = self.request.query_params.get('search', None)
            estado = self.request.query_params.get('estado', None)
            cliente = self.request.query_params.get('cliente', None)
            return CotizacionSelector.get_list(
                empresa_id=empresa.id, search=search, estado=estado, cliente=cliente
            )

        if self.action == 'retrieve':
            return CotizacionSelector.get_detail(None, empresa_id=empresa.id)

        # Mutations: queryset minimo
        return Cotizacion.objects.filter(
            empresa_id=empresa.id
        ).only('id', 'uuid', 'estado', 'empresa_id')

    def get_serializer_class(self):
        if self.action == 'list':
            return CotizacionListSerializer
        return CotizacionSerializer

    def create(self, request, *args, **kwargs):
        """
        # WARNING: v2.60: Sobrescribir create para asegurar que se devuelva el UUID correctamente.
        El serializer.create() ya maneja la creación vía Service Layer.
        
        # WARNING: Error Boundary Pattern: Todos los errores retornan JSON nativo (sin template_name).
        # WARNING: CRÍTICO: get_serializer() ya incluye el contexto del request automáticamente.
        # WARNING: FUERZA BRUTA ARQUITECTÓNICA: Inyección explícita de empresa en el contexto.
        """
        try:
            # # WARNING: FUERZA BRUTA ARQUITECTÓNICA: Obtener empresa del tenant actual
            empresa = self._resolve_empresa(request)
            
            # # WARNING: FUERZA BRUTA ARQUITECTÓNICA: Inyectar empresa y request explícitamente en el contexto
            # Esto garantiza que el serializador SIEMPRE tenga acceso a la empresa
            serializer = self.get_serializer(
                data=request.data, 
                context={
                    'request': request,
                    'empresa': empresa  # # WARNING: CRÍTICO: Empresa siempre disponible en el contexto
                }
            )
            serializer.is_valid(raise_exception=True)
            
            # # WARNING: CRÍTICO: El serializer.create() ya retorna la instancia creada
            # No llamamos a serializer.save() porque el método create() del serializer ya lo hace
            instance = serializer.save()
            
            # # WARNING: CRÍTICO: Re-serializar la instancia para obtener todos los campos (incluyendo UUID)
            # Esto asegura que se devuelvan todos los campos read_only como uuid, cliente_display, etc.
            output_serializer = self.get_serializer(instance)
            
            headers = self.get_success_headers(output_serializer.data)
            return Response(output_serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        
        except serializers.ValidationError as e:
            logger.error(f"[CotizacionViewSet] Error de validación en create: {str(e)}", exc_info=True)
            error_detail = e.detail if hasattr(e, 'detail') else str(e)
            # # WARNING: Error Boundary: Siempre devolver estructura {"error": "...", "detail": "..."}
            if isinstance(error_detail, dict):
                # Si el dict ya tiene "error" y "detail", usarlo; si no, envolverlo
                if "error" in error_detail and "detail" in error_detail:
                    return Response(error_detail, status=status.HTTP_400_BAD_REQUEST)
                # Si es un dict de errores de campo, convertirlo a formato estándar
                return Response(
                    {"error": "Error de validación", "detail": error_detail},
                    status=status.HTTP_400_BAD_REQUEST
                )
            return Response(
                {"error": "Error de validación", "detail": str(error_detail)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        except IntegrityError as e:
            logger.error(f"[CotizacionViewSet] Error de integridad en create: {str(e)}", exc_info=True)
            # Verificar si es un error de unicidad
            if 'unique' in str(e).lower() or 'duplicate' in str(e).lower():
                return Response(
                    {
                        "error": "Ya existe una cotización con estos datos. Por favor, verifique la información.",
                        "detail": str(e),
                        "code": "duplicate_cotizacion"
                    },
                    status=status.HTTP_409_CONFLICT
                )
            return Response(
                {"error": "Error de integridad de datos", "detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        except Exception as e:
            logger.error(f"[CotizacionViewSet] Error inesperado en create: {str(e)}", exc_info=True)
            return Response(
                {"error": "Ocurrió un error inesperado al crear la cotización.", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def perform_create(self, serializer):
        """
        # WARNING: v2.60: Este método ya no se usa porque sobrescribimos create().
        Se mantiene para compatibilidad pero no hace nada.
        """
        pass

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        """
        # WARNING: FASE 3: Actualización de cotización.
        
        # WARNING: Error Boundary Pattern: Todos los errores retornan JSON nativo.
        """
        try:
            instance = self.get_object()
            
            # # WARNING: FASE 3: Obtener empresa del tenant actual para inyectar en el contexto
            empresa = self._resolve_empresa(request)
            
            # # WARNING: FASE 3: Inyectar empresa y request en el contexto del serializer
            partial = kwargs.pop('partial', False)
            serializer = self.get_serializer(
                instance,
                data=request.data,
                partial=partial,
                context={
                    'request': request,
                    'empresa': empresa  # # WARNING: CRÍTICO: Empresa siempre disponible en el contexto
                }
            )
            serializer.is_valid(raise_exception=True)
            
            # # WARNING: FASE 3: El serializer.update() retorna la cabecera actualizada
            instance = serializer.save()
            
            # # WARNING: FASE 3: Re-serializar la instancia para obtener todos los campos actualizados
            output_serializer = self.get_serializer(instance)
            
            return Response(output_serializer.data, status=status.HTTP_200_OK)
        
        except serializers.ValidationError as e:
            logger.error(f"[CotizacionViewSet] Error de validación en update: {str(e)}", exc_info=True)
            error_detail = e.detail if hasattr(e, 'detail') else str(e)
            # # WARNING: Error Boundary: Siempre devolver estructura {"error": "...", "detail": "..."}
            if isinstance(error_detail, dict):
                if "error" in error_detail and "detail" in error_detail:
                    return Response(error_detail, status=status.HTTP_400_BAD_REQUEST)
                return Response(
                    {"error": "Error de validación", "detail": error_detail},
                    status=status.HTTP_400_BAD_REQUEST
                )
            return Response(
                {"error": "Error de validación", "detail": str(error_detail)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        except IntegrityError as e:
            logger.error(f"[CotizacionViewSet] Error de integridad en update: {str(e)}", exc_info=True)
            if 'unique' in str(e).lower() or 'duplicate' in str(e).lower():
                return Response(
                    {
                        "error": "Ya existe una cotización con estos datos. Por favor, verifique la información.",
                        "detail": str(e),
                        "code": "duplicate_cotizacion"
                    },
                    status=status.HTTP_409_CONFLICT
                )
            return Response(
                {"error": "Error de integridad de datos", "detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        except Exception as e:
            logger.error(f"[CotizacionViewSet] Error inesperado en update: {str(e)}", exc_info=True)
            return Response(
                {"error": "Ocurrió un error inesperado al actualizar la cotización.", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'], url_path='exportar-pdf', url_name='exportar-pdf')
    @transaction.atomic
    def exportar_pdf(self, request, uuid=None):
        """
        Genera y exporta el PDF de la cotización usando el generador modular.
        
        # WARNING: ARQUITECTURA MODULAR: Usa CotizacionPDFGenerator directamente.
        # WARNING: GENERACIÓN MÚLTIPLE: Permite generar el PDF siempre que se solicite, independientemente del estado.
        # WARNING: TRANSICIÓN DE ESTADO: Solo cambia de BORRADOR a ENVIADA la primera vez (transaction.atomic).
        
        GET /api/v1/cotizaciones/{uuid}/exportar-pdf/
        
        Returns:
            - 200 OK: PDF file
            - 404 NOT FOUND: Si la cotización no existe
            - 500 INTERNAL SERVER ERROR: Si hay error generando el PDF
        """
        from django.http import HttpResponse
        from django.template.loader import TemplateDoesNotExist

        from apps.tenant.cotizaciones.pdf_service import preparar_contexto_pdf
        from apps.tenant.cotizaciones.utils.pdf_generator import CotizacionPDFGenerator
        from apps.tenant.empresa.models import Empresa
        
        try:
            # Obtener cotización
            cotizacion = self.get_object()
            
            # Obtener empresa del tenant
            empresa = self._resolve_empresa(request)
            if not empresa:
                return Response(
                    {"error": "Empresa no encontrada"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # # WARNING: ARQUITECTURA: Preparar contexto usando preparar_contexto_pdf (Snapshot Pattern v2.60)
            # Este método prepara el contexto completo con totales, AIU, secciones agrupadas, etc.
            context = preparar_contexto_pdf(cotizacion, empresa, request)
            
            # # WARNING: ARQUITECTURA MODULAR: Invocación directa del generador
            # El generador es el único que conoce xhtml2pdf
            # # WARNING: Template: formato_profesional.html con layout de tablas clásico (compatible xhtml2pdf)
            # # WARNING: RUTA: Intentar múltiples rutas posibles para compatibilidad
            template_paths = [
                'cotizaciones/pdf/formato_profesional.html',  # Ruta estándar (apps/tenant/cotizaciones/templates/)
                'tenant/cotizaciones/pdf/formato_profesional.html',  # Ruta alternativa (apps/tenant/templates/)
            ]
            
            pdf_content = None
            used_path = None
            for template_path in template_paths:
                try:
                    pdf_content = CotizacionPDFGenerator.render_to_pdf(template_path, context)
                    if pdf_content:
                        used_path = template_path
                        logger.info(f"[CotizacionViewSet] Template encontrado en: {template_path}")
                        break
                except Exception as path_error:
                    logger.debug(f"[CotizacionViewSet] Template no encontrado en {template_path}: {str(path_error)}")
                    continue
            
            if not pdf_content:
                # Si ninguna ruta funcionó, intentar la primera y capturar el error específico
                try:
                    pdf_content = CotizacionPDFGenerator.render_to_pdf(template_paths[0], context)
                except Exception as final_error:
                    logger.error(f"[CotizacionViewSet] Error final al cargar template: {str(final_error)}")
                    raise
            
            if not pdf_content:
                # Si pdf_content es None, hubo un error en la generación o el template no existe
                logger.error(f"[CotizacionViewSet] PDF generado está vacío o template no encontrado para cotización {cotizacion.id}")
                return Response(
                    {
                        "error": "No se pudo localizar el template o generar el PDF",
                        "detail": "Verifique que el template 'tenant/cotizaciones/pdf/formato_profesional.html' existe"
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # # WARNING: TRANSICIÓN DE ESTADO: Solo ocurre si el PDF se generó exitosamente Y está en BORRADOR
            # Esto está dentro de transaction.atomic, por lo que si algo falla después,
            # el cambio de estado se revierte automáticamente
            # # WARNING: GENERACIÓN MÚLTIPLE: Permite generar PDF siempre, pero solo cambia estado la primera vez
            if cotizacion.estado == Cotizacion.Estado.BORRADOR:
                cotizacion.estado = Cotizacion.Estado.ENVIADA
                cotizacion.save(update_fields=['estado'])
                logger.info(f"[CotizacionViewSet] Cotización {cotizacion.id} actualizada de BORRADOR a ENVIADA")
            
            # Crear respuesta HTTP (Permite múltiples descargas)
            filename = f"Cotizacion_{cotizacion.codigo_unico or cotizacion.numero_cotizacion}.pdf"
            response = HttpResponse(pdf_content, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            
            logger.info(f"[CotizacionViewSet] [OK] PDF generado para cotización {cotizacion.id} (estado: {cotizacion.estado})")
            return response
            
        except TemplateDoesNotExist as e:
            logger.error(f"[CotizacionViewSet] Template no encontrado: {str(e)}")
            return Response(
                {
                    "error": "No se pudo localizar el template",
                    "detail": f"Template no encontrado: {str(e)}. Verifique que 'cotizaciones/pdf/formato_profesional.html' existe en apps/tenant/cotizaciones/templates/."
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except ImportError as e:
            logger.error(f"[CotizacionViewSet] Error de importación: {str(e)}")
            return Response(
                {
                    "error": "Error al generar el documento",
                    "detail": "xhtml2pdf no está instalado. Instale con: pip install xhtml2pdf"
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            logger.error(f"[CotizacionViewSet] Error generando PDF: {str(e)}\n{error_trace}", exc_info=True)
            # # WARNING: TRANSICIÓN DE ESTADO: Si hay error, la transacción se revierte automáticamente
            # El estado NO se cambia si el PDF no se genera exitosamente
            return Response(
                {
                    "error": "Error al generar el documento",
                    "detail": str(e),
                    "trace": error_trace if settings.DEBUG else None
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='render-offcanvas/crear')
    def render_offcanvas_crear(self, request):
        """
        Endpoint HTMX para renderizar el editor en modo creación.
        """
        from apps.tenant.clientes.models import Cliente
        from apps.tenant.cotizaciones.configuracion.models import ConfiguracionCotizacion

        empresa = self._resolve_empresa(request)

        context = {
            'cotizacion': None,
            'is_draft': True,
            'clientes': Cliente.objects.filter(empresa_id=empresa.id, activo=True).only('id', 'razon_social').order_by('razon_social') if empresa else [],
            'configuraciones': ConfiguracionCotizacion.objects.filter(empresa_id=empresa.id, es_activo=True).only('id', 'nombre_configuracion').order_by('nombre_configuracion') if empresa else [],
        }
        return Response(context, template_name='cotizaciones/offcanvas_crear_cotizacion.html')
    
    @action(detail=True, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='render-offcanvas/editar')
    def render_offcanvas_editar(self, request, **kwargs):
        """
        Endpoint HTMX para renderizar el editor en modo edición.
        """
        from apps.tenant.clientes.models import Cliente
        from apps.tenant.cotizaciones.configuracion.models import ConfiguracionCotizacion

        cotizacion = self.get_object()
        empresa = self._resolve_empresa(request)

        context = {
            'cotizacion': cotizacion,
            'is_draft': False,
            'clientes': Cliente.objects.filter(empresa_id=empresa.id, activo=True).only('id', 'razon_social').order_by('razon_social') if empresa else [],
            'configuraciones': ConfiguracionCotizacion.objects.filter(empresa_id=empresa.id, es_activo=True).only('id', 'nombre_configuracion').order_by('nombre_configuracion') if empresa else [],
        }
        return Response(context, template_name='cotizaciones/offcanvas_editar_cotizacion.html')
    
    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='render-offcanvas/detalle')
    def render_offcanvas_detalle(self, request):
        """
        Endpoint HTMX para detalle de cotización en modo solo lectura.
        """
        cotizacion_identifier = request.query_params.get('id')
        if not cotizacion_identifier:
            return Response({'detail': 'id es requerido'}, status=status.HTTP_400_BAD_REQUEST)

        cotizacion = None
        try:
            cotizacion = self.get_queryset().get(uuid=cotizacion_identifier)
        except (Cotizacion.DoesNotExist, ValueError):
            cotizacion = self.get_queryset().filter(id=cotizacion_identifier).first()

        if not cotizacion:
            return Response({'detail': 'Cotización no encontrada'}, status=status.HTTP_404_NOT_FOUND)

        context = {
            'cotizacion': cotizacion,
            'is_draft': False,
            'readonly': True,
        }
        return Response(context, template_name='cotizaciones/offcanvas_detalle_cotizacion.html')

    @action(detail=False, methods=['get'], url_path='estadisticas')
    def estadisticas(self, request):
        """
        # WARNING: v2.61: Endpoint para obtener estadísticas de cotizaciones.
        
        Retorna resumen con:
        - total_neto: Suma de total_con_impuestos de todas las cotizaciones
        - cantidad_total: Total de cotizaciones
        - cantidad_aceptadas: Cotizaciones con estado ACEPTADA
        - cantidad_enviadas: Cotizaciones con estado ENVIADA
        - cantidad_borrador: Cotizaciones con estado BORRADOR
        
        GET /api/v1/cotizaciones/estadisticas/
        
        Returns:
            {
                "total_neto": "1000000.00",
                "cantidad_total": 50,
                "cantidad_aceptadas": 10,
                "cantidad_enviadas": 20,
                "cantidad_borrador": 20
            }
        """
        try:
            base_qs = self.get_queryset()
            totales = base_qs.aggregate(
                total_neto=Coalesce(Sum('total_con_impuestos', output_field=DecimalField()), Decimal('0.00')),
                cantidad_total=Count('id'),
                cantidad_aceptadas=Count('id', filter=Q(estado=Cotizacion.Estado.ACEPTADA)),
                cantidad_enviadas=Count('id', filter=Q(estado=Cotizacion.Estado.ENVIADA)),
                cantidad_borrador=Count('id', filter=Q(estado=Cotizacion.Estado.BORRADOR)),
            )

            return Response(
                {
                    'total_neto': str(totales.get('total_neto') or Decimal('0.00')),
                    'cantidad_total': totales.get('cantidad_total') or 0,
                    'cantidad_aceptadas': totales.get('cantidad_aceptadas') or 0,
                    'cantidad_enviadas': totales.get('cantidad_enviadas') or 0,
                    'cantidad_borrador': totales.get('cantidad_borrador') or 0,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.error(f"[CotizacionViewSet] Error calculando estadísticas: {e}", exc_info=True)
            return Response(
                {'error': 'error_calculando_estadisticas', 'message': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=['post'])
    def recalcular(self, request, uuid=None):
        """
        # WARNING: v2.60: Dispara el recálculo total de la cabecera usando el servicio (SSoT).
        
        # WARNING: Error Boundary Pattern: Todos los errores retornan JSON nativo (sin template_name).
        """
        try:
            cotizacion = self.get_object()
            
            # # WARNING: v2.60: Usar calcular_totales() del servicio (SSoT)
            CotizacionService.calcular_totales(cotizacion.id)
            # Refrescar la instancia para obtener los valores actualizados
            cotizacion.refresh_from_db()
            return Response(self.get_serializer(cotizacion).data)
        
        except serializers.ValidationError as e:
            logger.error(f"[CotizacionViewSet] Error de validación en recalcular: {str(e)}", exc_info=True)
            error_detail = e.detail if hasattr(e, 'detail') else str(e)
            # # WARNING: Error Boundary: Siempre devolver estructura {"error": "...", "detail": "..."}
            if isinstance(error_detail, dict):
                # Si el dict ya tiene "error" y "detail", usarlo; si no, envolverlo
                if "error" in error_detail and "detail" in error_detail:
                    return Response(error_detail, status=status.HTTP_400_BAD_REQUEST)
                # Si es un dict de errores de campo, convertirlo a formato estándar
                return Response(
                    {"error": "Error de validación", "detail": error_detail},
                    status=status.HTTP_400_BAD_REQUEST
                )
            return Response(
                {"error": "Error de validación", "detail": str(error_detail)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        except Exception as e:
            logger.error(f"[CotizacionViewSet] Error inesperado en recalcular: {str(e)}", exc_info=True)
            return Response(
                {"error": "Ocurrió un error inesperado al recalcular la cotización.", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class CotizacionItemViewSet(BaseTenantViewSet):
    """CRUD para ítems individuales manejados por Tabulator."""
    serializer_class = CotizacionItemSerializer
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
    renderer_classes = [JSONRenderer]

    def get_queryset(self):
        """
        Filtrado por empresa del tenant actual (singleton).
        
        # WARNING: SSoT v2.60: La empresa se obtiene del tenant, no del usuario.
        """
        empresa = getattr(self.request, 'empresa', None)
        if not empresa:
            tenant = getattr(self.request, 'tenant', None)
            empresa = getattr(tenant, 'empresa', None)
        if not empresa:
            empresa = Empresa.objects.only('id').first()
        if not empresa:
            return CotizacionItem.objects.none()
        
        from ..services.selectors import ITEM_LIST_FIELDS
        return CotizacionItem.objects.filter(
            cotizacion__empresa=empresa
        ).select_related('cotizacion', 'producto', 'servicio').only(*ITEM_LIST_FIELDS)

    def perform_create(self, serializer):
        """
        # WARNING: SSoT v2.60: Validar que la cotización pertenezca a la empresa del usuario.
        
        # WARNING: Error Boundary Pattern: Errores se propagan al método create() del ViewSet.
        """
        try:
            # Validar que la cotización pertenezca a la empresa del usuario
            cotizacion_id = serializer.validated_data.get('cotizacion')
            if cotizacion_id:
                empresa = getattr(self.request, 'empresa', None)
                if not empresa:
                    tenant = getattr(self.request, 'tenant', None)
                    empresa = getattr(tenant, 'empresa', None)
                if not empresa:
                    empresa = Empresa.objects.only('id').first()
                if empresa and cotizacion_id.empresa != empresa:
                    from rest_framework.exceptions import PermissionDenied
                    raise PermissionDenied("No tiene permisos para agregar items a esta cotización.")
            
            item = serializer.save()
            # # WARNING: v2.60: Usar calcular_totales() del servicio (SSoT)
            CotizacionService.calcular_totales(item.cotizacion.id)
        
        except serializers.ValidationError as e:
            logger.error(f"[CotizacionItemViewSet] Error de validación en perform_create: {str(e)}", exc_info=True)
            raise
        
        except IntegrityError as e:
            logger.error(f"[CotizacionItemViewSet] Error de integridad en perform_create: {str(e)}", exc_info=True)
            if 'unique' in str(e).lower() or 'duplicate' in str(e).lower():
                raise serializers.ValidationError({
                    "error": "Ya existe un item con estos datos.",
                    "detail": str(e),
                    "code": "duplicate_item"
                })
            raise serializers.ValidationError({
                "error": "Error de integridad de datos",
                "detail": str(e)
            })
        
        except Exception as e:
            logger.error(f"[CotizacionItemViewSet] Error inesperado en perform_create: {str(e)}", exc_info=True)
            raise serializers.ValidationError({
                "error": "Ocurrió un error inesperado al crear el item.",
                "detail": str(e)
            })

    def perform_update(self, serializer):
        """
        # WARNING: Error Boundary Pattern: Errores se propagan al método update() del ViewSet.
        """
        try:
            item = serializer.save()
            # # WARNING: v2.60: Usar calcular_totales() del servicio (SSoT)
            CotizacionService.calcular_totales(item.cotizacion.id)
        
        except serializers.ValidationError as e:
            logger.error(f"[CotizacionItemViewSet] Error de validación en perform_update: {str(e)}", exc_info=True)
            raise
        
        except IntegrityError as e:
            logger.error(f"[CotizacionItemViewSet] Error de integridad en perform_update: {str(e)}", exc_info=True)
            if 'unique' in str(e).lower() or 'duplicate' in str(e).lower():
                raise serializers.ValidationError({
                    "error": "Ya existe un item con estos datos.",
                    "detail": str(e),
                    "code": "duplicate_item"
                })
            raise serializers.ValidationError({
                "error": "Error de integridad de datos",
                "detail": str(e)
            })
        
        except Exception as e:
            logger.error(f"[CotizacionItemViewSet] Error inesperado en perform_update: {str(e)}", exc_info=True)
            raise serializers.ValidationError({
                "error": "Ocurrió un error inesperado al actualizar el item.",
                "detail": str(e)
            })

    def perform_destroy(self, instance):
        """
        # WARNING: Error Boundary Pattern: Errores se propagan al método destroy() del ViewSet.
        """
        try:
            cotizacion = instance.cotizacion
            cotizacion_id = cotizacion.id
            instance.delete()
            # # WARNING: v2.60: Usar calcular_totales() del servicio (SSoT)
            CotizacionService.calcular_totales(cotizacion_id)
        
        except Exception as e:
            logger.error(f"[CotizacionItemViewSet] Error inesperado en perform_destroy: {str(e)}", exc_info=True)
            raise serializers.ValidationError({
                "error": "Ocurrió un error inesperado al eliminar el item.",
                "detail": str(e)
            })
