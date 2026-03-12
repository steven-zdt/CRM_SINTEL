"""
ViewSets para Cotizaciones v2.60 - Standalone & Resiliente
⚠️ v2.60: Integración total con DNA Dinámico y Service Layer.
⚠️ Tabulator Factory v2.40: Paginación remota y búsqueda en tiempo real.
⚠️ Error Boundary Pattern: Todos los errores retornan JSON nativo (sin template_name).
"""
import logging
from django.conf import settings
from rest_framework import viewsets, status, permissions, serializers
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.authentication import SessionAuthentication
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from django.db import transaction, IntegrityError
from django.db.models import Sum, Count, Q, DecimalField
from django.db.models.functions import Coalesce
from decimal import Decimal

from apps.tenant.api.base import BaseTenantViewSet
from apps.tenant.api.permissions import IsTenantMember
from apps.config.api.pagination import StandardResultsSetPagination
from ..models import Cotizacion, CotizacionItem
from .serializers import CotizacionSerializer, CotizacionItemSerializer
from ..services import CotizacionService

logger = logging.getLogger(__name__)

class CotizacionViewSet(BaseTenantViewSet):
    """
    ViewSet para Cotizaciones v2.60.
    
    ⚠️ Tabulator Factory v2.40:
    - Endpoint: GET /api/v1/cotizaciones/ con StandardResultsSetPagination
    - Soporte ?search= para búsqueda en tiempo real
    - Lookup por UUID para seguridad
    """
    lookup_field = 'uuid'
    serializer_class = CotizacionSerializer
    authentication_classes = [SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsTenantMember]
    renderer_classes = [JSONRenderer]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        """
        Filtrado por empresa del tenant actual (singleton).
        
        ⚠️ SSoT v2.60: La empresa se obtiene del tenant, no del usuario.
        """
        from apps.tenant.empresa.models import Empresa
        
        # ⚠️ SSoT: Obtener empresa del tenant actual (singleton)
        empresa = Empresa.objects.first()
        if not empresa:
            return Cotizacion.objects.none()
        
        queryset = Cotizacion.objects.filter(
            empresa=empresa
        ).select_related('cliente', 'configuracion').prefetch_related('items')
        
        # ⚠️ Tabulator Factory: Soporte para búsqueda
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                numero_cotizacion__icontains=search
            ) | queryset.filter(
                cliente__razon_social__icontains=search
            )
        
        return queryset.order_by('-fecha_emision', '-numero_cotizacion')

    def create(self, request, *args, **kwargs):
        """
        ⚠️ v2.60: Sobrescribir create para asegurar que se devuelva el UUID correctamente.
        El serializer.create() ya maneja la creación vía Service Layer.
        
        ⚠️ Error Boundary Pattern: Todos los errores retornan JSON nativo (sin template_name).
        ⚠️ CRÍTICO: get_serializer() ya incluye el contexto del request automáticamente.
        ⚠️ FUERZA BRUTA ARQUITECTÓNICA: Inyección explícita de empresa en el contexto.
        """
        try:
            # ⚠️ FUERZA BRUTA ARQUITECTÓNICA: Obtener empresa del tenant actual
            empresa = getattr(request, 'empresa', None)
            
            # ⚠️ FUERZA BRUTA ARQUITECTÓNICA: Inyectar empresa y request explícitamente en el contexto
            # Esto garantiza que el serializador SIEMPRE tenga acceso a la empresa
            serializer = self.get_serializer(
                data=request.data, 
                context={
                    'request': request,
                    'empresa': empresa  # ⚠️ CRÍTICO: Empresa siempre disponible en el contexto
                }
            )
            serializer.is_valid(raise_exception=True)
            
            # ⚠️ CRÍTICO: El serializer.create() ya retorna la instancia creada
            # No llamamos a serializer.save() porque el método create() del serializer ya lo hace
            instance = serializer.save()
            
            # ⚠️ CRÍTICO: Re-serializar la instancia para obtener todos los campos (incluyendo UUID)
            # Esto asegura que se devuelvan todos los campos read_only como uuid, cliente_display, etc.
            output_serializer = self.get_serializer(instance)
            
            headers = self.get_success_headers(output_serializer.data)
            return Response(output_serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        
        except serializers.ValidationError as e:
            logger.error(f"[CotizacionViewSet] Error de validación en create: {str(e)}", exc_info=True)
            error_detail = e.detail if hasattr(e, 'detail') else str(e)
            # ⚠️ Error Boundary: Siempre devolver estructura {"error": "...", "detail": "..."}
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
        ⚠️ v2.60: Este método ya no se usa porque sobrescribimos create().
        Se mantiene para compatibilidad pero no hace nada.
        """
        pass

    def update(self, request, *args, **kwargs):
        """
        ⚠️ FASE 3: Actualización de cotización.
        
        ⚠️ Error Boundary Pattern: Todos los errores retornan JSON nativo.
        """
        try:
            instance = self.get_object()
            
            # ⚠️ FASE 3: Obtener empresa del tenant actual para inyectar en el contexto
            empresa = getattr(request, 'empresa', None)
            
            # ⚠️ FASE 3: Inyectar empresa y request en el contexto del serializer
            partial = kwargs.pop('partial', False)
            serializer = self.get_serializer(
                instance,
                data=request.data,
                partial=partial,
                context={
                    'request': request,
                    'empresa': empresa  # ⚠️ CRÍTICO: Empresa siempre disponible en el contexto
                }
            )
            serializer.is_valid(raise_exception=True)
            
            # ⚠️ FASE 3: El serializer.update() ya retorna la instancia actualizada
            instance = serializer.save()
            
            # ⚠️ FASE 3: Re-serializar la instancia para obtener todos los campos actualizados
            output_serializer = self.get_serializer(instance)
            
            return Response(output_serializer.data, status=status.HTTP_200_OK)
        
        except serializers.ValidationError as e:
            logger.error(f"[CotizacionViewSet] Error de validación en update: {str(e)}", exc_info=True)
            error_detail = e.detail if hasattr(e, 'detail') else str(e)
            # ⚠️ Error Boundary: Siempre devolver estructura {"error": "...", "detail": "..."}
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
        
        ⚠️ ARQUITECTURA MODULAR: Usa CotizacionPDFGenerator directamente.
        ⚠️ GENERACIÓN MÚLTIPLE: Permite generar el PDF siempre que se solicite, independientemente del estado.
        ⚠️ TRANSICIÓN DE ESTADO: Solo cambia de BORRADOR a ENVIADA la primera vez (transaction.atomic).
        
        GET /api/v1/cotizaciones/{uuid}/exportar-pdf/
        
        Returns:
            - 200 OK: PDF file
            - 404 NOT FOUND: Si la cotización no existe
            - 500 INTERNAL SERVER ERROR: Si hay error generando el PDF
        """
        from django.http import HttpResponse
        from django.template.loader import TemplateDoesNotExist
        from apps.tenant.empresa.models import Empresa
        from apps.tenant.cotizaciones.utils.pdf_generator import CotizacionPDFGenerator
        from apps.tenant.cotizaciones.pdf_service import preparar_contexto_pdf
        
        try:
            # Obtener cotización
            cotizacion = self.get_object()
            
            # Obtener empresa del tenant
            empresa = Empresa.objects.first()
            if not empresa:
                return Response(
                    {"error": "Empresa no encontrada"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # ⚠️ ARQUITECTURA: Preparar contexto usando preparar_contexto_pdf (Snapshot Pattern v2.60)
            # Este método prepara el contexto completo con totales, AIU, secciones agrupadas, etc.
            context = preparar_contexto_pdf(cotizacion, empresa, request)
            
            # ⚠️ ARQUITECTURA MODULAR: Invocación directa del generador
            # El generador es el único que conoce xhtml2pdf
            # ⚠️ Template: formato_profesional.html con layout de tablas clásico (compatible xhtml2pdf)
            # ⚠️ RUTA: Intentar múltiples rutas posibles para compatibilidad
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
            
            # ⚠️ TRANSICIÓN DE ESTADO: Solo ocurre si el PDF se generó exitosamente Y está en BORRADOR
            # Esto está dentro de transaction.atomic, por lo que si algo falla después,
            # el cambio de estado se revierte automáticamente
            # ⚠️ GENERACIÓN MÚLTIPLE: Permite generar PDF siempre, pero solo cambia estado la primera vez
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
            
            logger.info(f"[CotizacionViewSet] ✅ PDF generado para cotización {cotizacion.id} (estado: {cotizacion.estado})")
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
            # ⚠️ TRANSICIÓN DE ESTADO: Si hay error, la transacción se revierte automáticamente
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
        Endpoint HTMX RESTful para cargar offcanvas de creación de cotizaciones.
        
        ⚠️ v2.61: Feature-Sliced Architecture - Template dedicado EXCLUSIVAMENTE para creación
        - GET /api/v1/cotizaciones/render-offcanvas/crear/ → Modo creación
        
        Returns:
            Template HTML: tenant/core/partials/cotizaciones/offcanvas_crear_cotizacion.html
        """
        from apps.tenant.empresa.models import Empresa
        from apps.tenant.clientes.models import Cliente
        from ..configuracion.models import ConfiguracionCotizacion
        
        # ⚠️ v2.61: Obtener contexto necesario para el template (clientes y configuraciones)
        empresa = Empresa.objects.first()
        context = {
            'cotizacion': None,
            'is_draft': True,
            'clientes': Cliente.objects.filter(activo=True).order_by('razon_social')[:100] if empresa else [],
            'configuraciones': ConfiguracionCotizacion.objects.filter(es_activo=True).order_by('nombre_configuracion') if empresa else []
        }
        return Response(context, template_name='tenant/core/partials/cotizaciones/offcanvas_crear_cotizacion.html')
    
    @action(detail=True, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='render-offcanvas/editar')
    def render_offcanvas_editar(self, request, **kwargs):
        """
        Endpoint HTMX RESTful para cargar offcanvas de edición de cotizaciones.
        
        ⚠️ v2.61: Feature-Sliced Architecture - Template dedicado EXCLUSIVAMENTE para edición
        ⚠️ v2.61: BaseTenantViewSet usa lookup_field="uuid", pero el frontend puede enviar IDs numéricos
        - GET /api/v1/cotizaciones/{uuid}/render-offcanvas/editar/ → Modo edición
        
        Returns:
            Template HTML: tenant/core/partials/cotizaciones/offcanvas_editar_cotizacion.html
        """
        import traceback
        try:
            # ⚠️ v2.61: BaseTenantViewSet usa lookup_field="uuid", pero el frontend puede enviar IDs numéricos
            # El router de DRF pone el valor en kwargs['uuid'] cuando lookup_field="uuid"
            cotizacion_identifier = kwargs.get('uuid') or kwargs.get('pk')
            
            if not cotizacion_identifier:
                return Response(
                    {"detail": ["ID de cotización no proporcionado en la URL."]},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Intentar obtener por UUID primero, luego por ID numérico
            try:
                cotizacion = self.get_queryset().get(uuid=cotizacion_identifier)
            except (Cotizacion.DoesNotExist, ValueError):
                # Si falla con UUID, intentar con ID numérico
                try:
                    cotizacion = self.get_queryset().get(id=cotizacion_identifier)
                except (Cotizacion.DoesNotExist, ValueError):
                    return Response(
                        {"detail": [f"Cotización con ID {cotizacion_identifier} no encontrada."]},
                        status=status.HTTP_404_NOT_FOUND
                    )
            
            from apps.tenant.empresa.models import Empresa
            from apps.tenant.clientes.models import Cliente
            from ..configuracion.models import ConfiguracionCotizacion
            
            empresa = Empresa.objects.first()
            context = {
                'cotizacion': cotizacion,
                'is_draft': False,
                'clientes': Cliente.objects.filter(activo=True).order_by('razon_social')[:100] if empresa else [],
                'configuraciones': ConfiguracionCotizacion.objects.filter(es_activo=True).order_by('nombre_configuracion') if empresa else []
            }
            return Response(context, template_name='tenant/core/partials/cotizaciones/offcanvas_editar_cotizacion.html')
        
        except Exception as e:
            logger.error(f"Error en render_offcanvas_editar: {e}")
            logger.error(traceback.format_exc())
            return Response(
                {"detail": [f"Error al cargar cotización: {str(e)}"]},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='render-offcanvas/detalle')
    def render_offcanvas_detalle(self, request):
        """
        Endpoint HTMX RESTful para cargar offcanvas de detalle de cotizaciones (read-only).
        
        ⚠️ v2.61: Feature-Sliced Architecture - Template dedicado para detalle
        - GET /api/v1/cotizaciones/render-offcanvas/detalle/?id={uuid} → Modo detalle
        
        Query params:
        - id: ID de la cotización (requerido, puede ser numérico o UUID)
        
        Returns:
            Template HTML: tenant/core/partials/cotizaciones/offcanvas_cotizacion_detalle.html
        """
        import traceback
        try:
            cotizacion_id = request.query_params.get('id')
            if not cotizacion_id:
                context = {
                    'cotizacion': None,
                    'error': 'ID de cotización no proporcionado'
                }
                return Response(context, template_name='tenant/core/partials/cotizaciones/offcanvas_cotizacion_detalle.html', status=400)
            
            # Intentar obtener por UUID primero, luego por ID numérico
            cotizacion = None
            try:
                cotizacion = self.get_queryset().select_related('cliente', 'configuracion').prefetch_related('items').get(uuid=cotizacion_id)
                logger.info(f"[CotizacionViewSet] Cotización encontrada por UUID: {cotizacion_id}")
            except (Cotizacion.DoesNotExist, ValueError) as e:
                logger.debug(f"[CotizacionViewSet] No se encontró por UUID {cotizacion_id}, intentando por ID numérico: {e}")
                # Si falla con UUID, intentar con ID numérico
                try:
                    cotizacion = self.get_queryset().select_related('cliente', 'configuracion').prefetch_related('items').get(id=cotizacion_id)
                    logger.info(f"[CotizacionViewSet] Cotización encontrada por ID numérico: {cotizacion_id}")
                except (Cotizacion.DoesNotExist, ValueError) as e2:
                    logger.warning(f"[CotizacionViewSet] Cotización no encontrada con ID {cotizacion_id}: {e2}")
                    context = {
                        'cotizacion': None,
                        'error': f'Cotización con ID {cotizacion_id} no encontrada'
                    }
                    return Response(context, template_name='tenant/core/partials/cotizaciones/offcanvas_cotizacion_detalle.html', status=404)
            
            if not cotizacion:
                context = {
                    'cotizacion': None,
                    'error': f'Cotización con ID {cotizacion_id} no encontrada'
                }
                return Response(context, template_name='tenant/core/partials/cotizaciones/offcanvas_cotizacion_detalle.html', status=404)
            
            # Preparar contexto con validaciones
            context = {
                'cotizacion': cotizacion
            }
            
            logger.info(f"[CotizacionViewSet] Renderizando detalle de cotización {cotizacion.id} (UUID: {cotizacion.uuid})")
            
            # ⚠️ v2.61: Intentar renderizar el template y capturar errores específicos
            try:
                return Response(context, template_name='tenant/core/partials/cotizaciones/offcanvas_cotizacion_detalle.html')
            except Exception as template_error:
                logger.error(f"[CotizacionViewSet] Error al renderizar template: {template_error}", exc_info=True)
                logger.error(f"[CotizacionViewSet] Traceback del template: {traceback.format_exc()}")
                # Retornar error más específico
                context = {
                    'cotizacion': None,
                    'error': f'Error al renderizar template: {str(template_error)}'
                }
                return Response(context, template_name='tenant/core/partials/cotizaciones/offcanvas_cotizacion_detalle.html', status=500)
        
        except Exception as e:
            logger.error(f"[CotizacionViewSet] Error en render_offcanvas_detalle: {e}", exc_info=True)
            logger.error(f"[CotizacionViewSet] Traceback completo: {traceback.format_exc()}")
            context = {
                'cotizacion': None,
                'error': f'Error al cargar cotización: {str(e)}'
            }
            return Response(context, template_name='tenant/core/partials/cotizaciones/offcanvas_cotizacion_detalle.html', status=500)

    @action(detail=False, methods=['get'], url_path='estadisticas')
    def estadisticas(self, request):
        """
        ⚠️ v2.61: Endpoint para obtener estadísticas de cotizaciones.
        
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
            from apps.tenant.empresa.models import Empresa
            
            # ⚠️ SSoT: Obtener empresa del tenant actual (singleton)
            empresa = Empresa.objects.first()
            if not empresa:
                return Response({
                    "total_neto": "0.00",
                    "cantidad_total": 0,
                    "cantidad_aceptadas": 0,
                    "cantidad_enviadas": 0,
                    "cantidad_borrador": 0
                }, status=status.HTTP_200_OK)
            
            # Base queryset filtrado por empresa
            base_qs = Cotizacion.objects.filter(empresa=empresa)
            
            # Agregaciones para total neto y cantidad total
            totales = base_qs.aggregate(
                total_neto=Coalesce(Sum('total_con_impuestos', output_field=DecimalField()), Decimal('0.00')),
                cantidad_total=Count('id')
            )
            
            # Conteos por estado
            cantidad_aceptadas = base_qs.filter(estado=Cotizacion.Estado.ACEPTADA).count()
            cantidad_enviadas = base_qs.filter(estado=Cotizacion.Estado.ENVIADA).count()
            cantidad_borrador = base_qs.filter(estado=Cotizacion.Estado.BORRADOR).count()
            
            return Response({
                "total_neto": str(totales['total_neto'] or Decimal('0.00')),
                "cantidad_total": totales['cantidad_total'] or 0,
                "cantidad_aceptadas": cantidad_aceptadas,
                "cantidad_enviadas": cantidad_enviadas,
                "cantidad_borrador": cantidad_borrador
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"[CotizacionViewSet] Error calculando estadísticas: {e}", exc_info=True)
            return Response(
                {"error": "error_calculando_estadisticas", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def recalcular(self, request, uuid=None):
        """
        ⚠️ v2.60: Dispara el recálculo total de la cabecera usando el servicio (SSoT).
        
        ⚠️ Error Boundary Pattern: Todos los errores retornan JSON nativo (sin template_name).
        """
        try:
            cotizacion = self.get_object()
            
            # ⚠️ v2.60: Usar calcular_totales() del servicio (SSoT)
            CotizacionService.calcular_totales(cotizacion.id)
            # Refrescar la instancia para obtener los valores actualizados
            cotizacion.refresh_from_db()
            return Response(self.get_serializer(cotizacion).data)
        
        except serializers.ValidationError as e:
            logger.error(f"[CotizacionViewSet] Error de validación en recalcular: {str(e)}", exc_info=True)
            error_detail = e.detail if hasattr(e, 'detail') else str(e)
            # ⚠️ Error Boundary: Siempre devolver estructura {"error": "...", "detail": "..."}
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
    authentication_classes = [SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsTenantMember]
    renderer_classes = [JSONRenderer]

    def get_queryset(self):
        """
        Filtrado por empresa del tenant actual (singleton).
        
        ⚠️ SSoT v2.60: La empresa se obtiene del tenant, no del usuario.
        """
        from apps.tenant.empresa.models import Empresa
        
        # ⚠️ SSoT: Obtener empresa del tenant actual (singleton)
        empresa = Empresa.objects.first()
        if not empresa:
            return CotizacionItem.objects.none()
        
        return CotizacionItem.objects.filter(
            cotizacion__empresa=empresa
        ).select_related('cotizacion', 'producto', 'servicio')

    def perform_create(self, serializer):
        """
        ⚠️ SSoT v2.60: Validar que la cotización pertenezca a la empresa del usuario.
        
        ⚠️ Error Boundary Pattern: Errores se propagan al método create() del ViewSet.
        """
        try:
            # Validar que la cotización pertenezca a la empresa del usuario
            cotizacion_id = serializer.validated_data.get('cotizacion')
            if cotizacion_id:
                empresa = getattr(self.request.user, 'empresa', None)
                if empresa and cotizacion_id.empresa != empresa:
                    from rest_framework.exceptions import PermissionDenied
                    raise PermissionDenied("No tiene permisos para agregar items a esta cotización.")
            
            item = serializer.save()
            # ⚠️ v2.60: Usar calcular_totales() del servicio (SSoT)
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
        ⚠️ Error Boundary Pattern: Errores se propagan al método update() del ViewSet.
        """
        try:
            item = serializer.save()
            # ⚠️ v2.60: Usar calcular_totales() del servicio (SSoT)
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
        ⚠️ Error Boundary Pattern: Errores se propagan al método destroy() del ViewSet.
        """
        try:
            cotizacion = instance.cotizacion
            cotizacion_id = cotizacion.id
            instance.delete()
            # ⚠️ v2.60: Usar calcular_totales() del servicio (SSoT)
            CotizacionService.calcular_totales(cotizacion_id)
        
        except Exception as e:
            logger.error(f"[CotizacionItemViewSet] Error inesperado en perform_destroy: {str(e)}", exc_info=True)
            raise serializers.ValidationError({
                "error": "Ocurrió un error inesperado al eliminar el item.",
                "detail": str(e)
            })