import calendar
import logging
import uuid

from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from django.db.models import Count, OuterRef, Q, Subquery, Sum
from django.db.models.deletion import ProtectedError
from django.utils.functional import cached_property
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, serializers, status
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError as DRFValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from rest_framework.response import Response

from apps.config.api.pagination import StandardResultsSetPagination
from apps.tenant.api.base import BaseTenantViewSet
from apps.tenant.api.mixins import SintelDSVMixin
from apps.tenant.api.permissions import HasTenantRole, IsTenantAdminOrReadOnly, IsTenantMember
from apps.tenant.api.utils import resolve_tenant_empresa
from apps.tenant.empleados.api.serializers import (
    ContratoNestedSerializer,
    DevengoSerializer,
    EmpleadoDetailSerializer,
    EmpleadoListSerializer,
    ResolucionDIANSerializer,
    LiquidacionPrestacionSerializer,
    PeriodoNominaSerializer,
)
from apps.tenant.empleados.models import Contrato, Devengo, Empleado, ResolucionDIAN, LiquidacionPrestacion, PeriodoNomina
from apps.tenant.empleados.services.business_service import PeriodoNominaBusinessService
from apps.tenant.empleados.services.selectors import PeriodoNominaSelector
from apps.tenant.empleados.choices import (
    EPS_CHOICES,
    AFP_CHOICES,
    ARL_CHOICES,
    RIESGO_ARL_CHOICES,
)
from apps.tenant.empleados.services import (
    ContratoServiceMixin,
    DevengoServiceMixin,
    EmpleadoServiceMixin,
)
from apps.tenant.empleados.services.selectors import ContratoSelector, EmpleadoSelector
from apps.tenant.empleados.services.business_service import NominaCalculationService

logger = logging.getLogger(__name__)


class EmpleadoViewSet(SintelDSVMixin, EmpleadoServiceMixin, BaseTenantViewSet):
    """
    WARNING: v2.62.4: ViewSet para Empleados migrado a BaseTenantViewSet.
    v3.6.1: UUID lookup field (AGENTS.md 14) - hereda lookup_field="uuid" de BaseTenantViewSet.
    """
    queryset = Empleado.objects.none()
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["numero_documento", "primer_nombre", "primer_apellido"]

    @cached_property
    def tenant_empresa(self):
        return resolve_tenant_empresa(self.request, self)

    def get_empresa(self):
        return self.tenant_empresa

    def get_queryset(self):
        """
        WARNING: v2.62.4: QuerySet optimizado usando service layer.
        """
        if self.action == 'list':
            return self.get_qs_list()
        return self.get_qs_detail()
    
    def get_object(self):
        """
        v3.6.1: UUID lookup estricto (AGENTS.md Sec. 14).
        """
        try:
            return self.get_qs_detail()
        except Empleado.DoesNotExist as exc:
            lookup_value = self.kwargs.get(self.lookup_url_kwarg or self.lookup_field)
            raise NotFound(
                f'Empleado {lookup_value} no encontrado o no pertenece a este tenant.'
            ) from exc
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        empresa = self.get_empresa()
        context['empresa'] = empresa
        context['empresa_id'] = empresa.id if empresa else None
        return context

    def list(self, request, *args, **kwargs):
        """
        WARNING: v2.60: Listado paginado con formato DRF {count, results} para Tabulator Factory.
        """
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        # Si no hay paginacion, retornar formato compatible
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'count': len(serializer.data),
            'next': None,
            'previous': None,
            'results': serializer.data
        })

    def get_serializer_class(self):
        return EmpleadoListSerializer if self.action == "list" else EmpleadoDetailSerializer

    def create(self, request, *args, **kwargs):
        """
        WARNING: v2.40: Sobrescribir create para manejar errores de empresa no encontrada y validaciones.
        v3.7.4: Mejorado manejo de errores de validacion para JSON limpio.
        """
        try:
            # Validar datos del serializer primero
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            # Ejecutar perform_create que asigna empresa
            self.perform_create(serializer)

            # WARNING: Paso 4: Retornar respuesta con was_updated para listeners JS
            response_data = serializer.data
            response_data['was_updated'] = False
            response_data['message'] = 'Empleado creado correctamente'

            headers = self.get_success_headers(response_data)
            return Response(response_data, status=status.HTTP_201_CREATED, headers=headers)

        except ValueError as e:
            logger.error(f"[EmpleadoViewSet] Error en create (ValueError): {str(e)}", exc_info=True)
            return Response(
                {"error": str(e), "detail": "No se puede crear el empleado sin una empresa configurada."},
                status=status.HTTP_400_BAD_REQUEST
            )
        except serializers.ValidationError as e:
            logger.error(f"[EmpleadoViewSet] Error de validacion en create: {e.detail}", exc_info=True)
            # v3.7.4: Asegurarse de que detail sea JSON limpio, no string de Python
            detail_data = e.detail if isinstance(e.detail, dict) else str(e.detail)
            return Response(
                {"error": "Error de validacion", "detail": detail_data},
                status=status.HTTP_400_BAD_REQUEST
            )
        except IntegrityError as e:
            logger.error(f"[EmpleadoViewSet] Error de integridad en create: {str(e)}", exc_info=True)
            # Verificar si es un error de unicidad
            if 'uniq_empleado_per_tenant' in str(e):
                return Response(
                    {"error": "Ya existe un empleado con este tipo y numero de documento en esta empresa."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            return Response(
                {"error": "Error de integridad de datos", "detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"[EmpleadoViewSet] Error inesperado en create: {str(e)}", exc_info=True, stack_info=True)
            return Response(
                {"error": "Error interno del servidor", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def perform_create(self, serializer):
        serializer.instance = self.service_crear_empleado(serializer)
    
    def update(self, request, *args, **kwargs):
        """
        WARNING: Paso 4: Sobrescribir update para devolver respuesta JSON con was_updated.
        Permite que los listeners JS distingan entre creacion y actualizacion.
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        # WARNING: Paso 4: Devolver respuesta con was_updated para listeners JS
        response_data = serializer.data
        response_data['was_updated'] = True
        response_data['message'] = 'Empleado actualizado correctamente'
        
        return Response(response_data, status=status.HTTP_200_OK)
    
    def partial_update(self, request, *args, **kwargs):
        """
        WARNING: Paso 4: Sobrescribir partial_update para devolver respuesta JSON con was_updated.
        """
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)
    
    def perform_update(self, serializer):
        """
        WARNING: v2.40: Al actualizar un empleado, si el estado cambia a RETIRADO,
        cancelar automaticamente todos los contratos activos.
        """
        serializer.instance = self.service_actualizar_empleado(serializer)
    
    def destroy(self, request, *args, **kwargs):
        """
        Hard Delete solo para empleados RETIRADOS.
        Elimina en cascada: devengos → contratos → empleado.
        DSV: empresa_id validado via get_queryset() y verificacion explicita en service.
        """
        instance = self.get_object()

        # DSV explícito: garantiza que el empleado pertenece al tenant activo
        empresa_id = self.get_empresa_id()
        if instance.empresa_id != empresa_id:
            return Response(
                {'detail': 'El empleado no pertenece a la empresa activa.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            resultado = self.service_eliminar_empleado_retirado(instance)
            logger.info(
                f"[EmpleadoViewSet] Empleado uuid={instance.uuid} eliminado. "
                f"Contratos: {resultado['contratos_eliminados']}, "
                f"Devengos: {resultado['devengos_eliminados']}"
            )
            return Response({
                'detail': 'Empleado eliminado exitosamente.',
                'resumen': resultado,
            }, status=status.HTTP_200_OK)

        except (DjangoValidationError, DRFValidationError) as e:
            msg = e.detail if hasattr(e, 'detail') else str(e)
            if isinstance(msg, list):
                msg = ' '.join(str(m) for m in msg)
            logger.warning(
                f"[EmpleadoViewSet] Eliminacion rechazada uuid={instance.uuid}: {msg}"
            )
            return Response({'detail': msg}, status=status.HTTP_409_CONFLICT)

        except ProtectedError:
            logger.error(f"[EmpleadoViewSet] ProtectedError al eliminar uuid={instance.uuid}", exc_info=True)
            return Response({
                'detail': 'No se puede eliminar: el empleado tiene registros protegidos relacionados.',
                'error_type': 'protected_relation',
            }, status=status.HTTP_409_CONFLICT)

        except Exception as e:
            logger.error(f"[EmpleadoViewSet] Error inesperado al eliminar uuid={instance.uuid}: {e}", exc_info=True)
            return Response(
                {'detail': f'Error al eliminar empleado: {e}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        summary = self.service_get_nomina_summary(request)
        if not summary:
            return Response({"error": "sin_empresa"}, status=404)
        return Response(summary)
    
    @action(detail=True, methods=["get"], renderer_classes=[TemplateHTMLRenderer, JSONRenderer], url_path="historial-nominas")
    def historial_nominas(self, request, uuid=None):
        """
        WARNING: v2.60: Devuelve el HTML del historial de nominas para un empleado especifico (HTMX)
        o los datos JSON para Tabulator (paginacion remota).
        
        Endpoint: GET /api/v1/empleados/{id}/historial-nominas/
        
        Query params:
        - format=json: Retorna datos JSON para Tabulator (paginacion remota)
        - Sin format: Retorna template HTML del offcanvas
        
        Returns:
            Template HTML renderizado con el offcanvas del historial de nominas
            o JSON con datos paginados para Tabulator
        """
        empresa = self.get_empresa()
        empleado = self.get_object()
        
        # WARNING: v2.60: Zero Trust - Validar que el empleado pertenezca al tenant
        if empleado.empresa_id != empresa.id:
            return Response(
                {"error": "El empleado no pertenece a este tenant."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # WARNING: v2.60: Si se solicita formato JSON, retornar datos para Tabulator
        format_param = request.query_params.get('format', '')
        if format_param == 'json' or request.accepted_renderer.format == 'json':
            # Usar el queryset optimizado del service layer
            search = request.query_params.get('search', None)
            qs = self.get_historial_qs(empleado.id)
            
            # Paginacion usando StandardResultsSetPagination
            paginator = StandardResultsSetPagination()
            page = paginator.paginate_queryset(qs, request)
            
            if page is not None:
                serializer = DevengoSerializer(page, many=True)
                return paginator.get_paginated_response(serializer.data)
            
            # Si no hay paginacion, retornar todos los resultados
            serializer = DevengoSerializer(qs, many=True)
            return Response(serializer.data)
        
        # WARNING: v2.60: Retornar template HTML del offcanvas
        context = {
            'empresa': empresa,
            'empleado': empleado,
        }
        
        return Response(context, template_name='tenant/empleados/offcanvas_historial_nominas.html')

    @action(detail=False, methods=["get"], renderer_classes=[TemplateHTMLRenderer, JSONRenderer], url_path="gestor-offcanvas")
    def gestor_offcanvas(self, request):
        """
        WARNING: Paso 4: Devuelve el HTML del formulario para HTMX Offcanvas (Zero Trust).
        Centraliza la entrega de templates para los modulos features/*.js
        """
        # WARNING: Paso 4: Zero Trust - La empresa se extrae del usuario autenticado
        empresa = getattr(request.user, 'empresa', None)
        if not empresa:
            # Fallback: usar metodo get_empresa() si existe
            try:
                empresa = self.get_empresa()
            except:
                return Response({"error": "Sin tenant asignado"}, status=status.HTTP_403_FORBIDDEN)
        
        if not empresa:
            return Response({"error": "Sin tenant asignado"}, status=status.HTTP_403_FORBIDDEN)
        
        empresa_id = empresa.id
        
        tipo = request.query_params.get('tipo', 'empleado')
        obj_uuid = request.query_params.get('uuid')
        empleado_id = request.query_params.get('empleado')
        context = {'empresa_id': empresa_id}
        
        if tipo == 'empleado':
            from apps.tenant.empresa.services.selectors import SedeSelector, AreaSelector
            resoluciones_activas = (
                ResolucionDIAN.objects
                .filter(empresa_id=empresa_id, vigente=True)
                .only('id', 'uuid', 'numero_resolucion', 'prefijo',
                      'fecha_fin', 'consecutivo', 'rango_hasta', 'empresa_id')
                .order_by('-fecha_fin')
            )
            context.update({
                'EPS_CHOICES':         EPS_CHOICES,
                'AFP_CHOICES':         AFP_CHOICES,
                'ARL_CHOICES':         ARL_CHOICES,
                'RIESGO_ARL_CHOICES':  RIESGO_ARL_CHOICES,
                'sedes':               SedeSelector.get_list(empresa_id),
                'areas':               AreaSelector.get_list(empresa_id),
                'resoluciones_activas': resoluciones_activas,
            })
            if obj_uuid:
                instance = self.selector_class.get_detail(empresa_id, obj_uuid)
                context['empleado'] = instance
                if request.query_params.get('mode') == 'ver':
                    return Response(context, template_name='tenant/empleados/offcanvas_detalle_empleado.html')
                return Response(context, template_name='tenant/empleados/offcanvas_editar_empleado.html')
            return Response(context, template_name='tenant/empleados/offcanvas_crear_empleado.html')
            
        elif tipo == 'contrato':
            if obj_uuid:
                contrato = self.contrato_selector.get_detail(empresa_id, obj_uuid)
                context['contrato'] = contrato
                context['empleado'] = contrato.empleado
                return Response(context, template_name='tenant/empleados/offcanvas_editar_contrato.html')
            if empleado_id:
                context['empleado'] = self.selector_class.get_by_id(empresa_id, empleado_id)
            return Response(context, template_name='tenant/empleados/offcanvas_crear_contrato.html')
            
        elif tipo == 'devengo':
            if obj_uuid:
                devengo = self.devengo_selector.get_detail(empresa_id, obj_uuid)
                context['devengo'] = devengo
                context['empleado'] = devengo.empleado
                context['contrato'] = devengo.contrato
            if empleado_id:
                empleado = self.selector_class.get_by_id(empresa_id, empleado_id)
                context['empleado'] = empleado
                contrato_activo = self.contrato_selector.get_activo_for_empleado(
                    empresa_id,
                    empleado.id,
                )
                if contrato_activo:
                    context['contrato'] = contrato_activo
            return Response(context, template_name='tenant/empleados/offcanvas_crear_devengo.html')
            
        return Response({"error": "Tipo no valido"}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["get"], url_path="contrato-disponible")
    def contrato_disponible(self, request, uuid=None):
        """
        WARNING: v2.40: Valida si el empleado tiene contrato activo disponible para nomina.
        Verifica que no exista ya un devengo para el periodo_mes actual.
        """
        empresa = self.get_empresa()
        if not empresa:
            return Response({"error": "sin_empresa"}, status=status.HTTP_404_NOT_FOUND)

        empleado = self.get_object()
        
        # 1. Buscar contrato activo del empleado (WARNING: v2.40: Maquina de Estados - usar estado='ACTIVO')
        contrato_activo = self.contrato_selector.get_activo_for_empleado(
            empresa.id,
            empleado.id,
        )
        
        if not contrato_activo:
            return Response({
                "disponible": False,
                "error": "El empleado no tiene un contrato activo"
            }, status=status.HTTP_404_NOT_FOUND)
        
        # WARNING: v2.40: Maquina de Estados - Validar que el contrato este ACTIVO
        if contrato_activo.estado != 'ACTIVO':
            return Response({
                "disponible": False,
                "error": f"El contrato no esta activo (estado: {contrato_activo.estado})"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 2. Obtener periodo_mes actual (YYYY-MM) desde query params o usar el mes actual
        periodo_mes = request.query_params.get('periodo_mes', None)
        if not periodo_mes:
            # Si no se proporciona, usar el mes actual
            ahora = datetime.now()
            periodo_mes = ahora.strftime('%Y-%m')
        
        # Validar formato YYYY-MM
        try:
            datetime.strptime(periodo_mes, '%Y-%m')
        except ValueError:
            return Response({
                "disponible": False,
                "error": f"Formato de periodo invalido: {periodo_mes}. Debe ser YYYY-MM"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 3. Verificar que NO exista ya un devengo para ese empleado en ese periodo
        devengo_existente = self.devengo_selector.exists_for_periodo(
            empresa.id,
            empleado.id,
            periodo_mes,
        )
        
        if devengo_existente:
            return Response({
                "disponible": False,
                "error": f"Ya existe una nomina registrada para el periodo {periodo_mes}"
            }, status=status.HTTP_409_CONFLICT)
        
        # 4. Retornar datos del contrato disponible
        return Response({
            "disponible": True,
            "contrato": {
                "id": contrato_activo.id,
                "salario_mensual": str(contrato_activo.salario_mensual),
                "auxilio_transporte": str(contrato_activo.auxilio_transporte or 0),
                "prestamos_empresa": str(contrato_activo.prestamos_empresa or 0),
                "tipo": contrato_activo.tipo,
                "cargo": contrato_activo.cargo,
                "estado": contrato_activo.estado
            },
            "periodo_mes": periodo_mes
        }, status=status.HTTP_200_OK)

class ContratoViewSet(SintelDSVMixin, ContratoServiceMixin, BaseTenantViewSet):
    """
    WARNING: v2.62.4: ViewSet para Contratos migrado a BaseTenantViewSet.
    v3.6.1: UUID lookup field (AGENTS.md 14) - hereda lookup_field="uuid" de BaseTenantViewSet.
    """
    serializer_class = ContratoNestedSerializer
    # WARNING: v2.40: Permitir subida de archivos PDF (opcional)
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['empleado', 'estado', 'activo']

    @cached_property
    def tenant_empresa(self):
        return resolve_tenant_empresa(self.request, self)

    def get_empresa(self):
        return self.tenant_empresa
    
    def get_queryset(self):
        """
        WARNING: v2.60: QuerySet optimizado usando service layer.
        """
        if self.action == 'list':
            return self.get_qs_list()
        return self.get_qs_detail()

    def get_object(self):
        """
        v3.6.1: UUID lookup estricto (AGENTS.md Sec. 14).
        """
        try:
            return self.get_qs_detail()
        except Contrato.DoesNotExist as exc:
            lookup_value = self.kwargs.get(self.lookup_url_kwarg or self.lookup_field)
            raise NotFound(
                f'Contrato {lookup_value} no encontrado o no pertenece a este tenant.'
            ) from exc

    def get_serializer_context(self):
        context = super().get_serializer_context()
        empresa = self.get_empresa()
        context['empresa'] = empresa
        context['empresa_id'] = empresa.id if empresa else None
        return context

    def create(self, request, *args, **kwargs):
        """
        WARNING: v2.95: Sobrescribir create para manejar errores y validaciones.
        """
        try:
            # WARNING: [SEC-M6] Solo nombres de campo y tipo, no valores (salario y
            # demas datos del contrato son sensibles/PII).
            logger.info(f"[ContratoViewSet] Campos recibidos en create: {list(request.data.keys()) if hasattr(request.data, 'keys') else type(request.data).__name__}")
            
            # Validar que el campo empleado este presente
            if 'empleado' not in request.data:
                logger.error("[ContratoViewSet] Campo 'empleado' no encontrado en request.data")
                return Response(
                    {"error": "Error de validacion", "detail": {"empleado": ["Este campo es requerido."]}},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Ejecutar create del padre
            response = super().create(request, *args, **kwargs)
            
            # WARNING: Paso 4: Agregar was_updated a la respuesta para listeners JS
            if response.status_code == status.HTTP_201_CREATED:
                response_data = response.data
                if isinstance(response_data, dict):
                    response_data['was_updated'] = False
                    response_data['message'] = 'Contrato creado correctamente'
            
            return response
        except serializers.ValidationError as e:
            logger.error(f"[ContratoViewSet] Error de validacion en create: {str(e)}", exc_info=True)
            # WARNING: v2.60: Error Boundary Pattern - Retornar formato JSON estructurado para UIManager
            error_detail = e.detail if hasattr(e, 'detail') else str(e)
            if isinstance(error_detail, dict):
                return Response(error_detail, status=status.HTTP_400_BAD_REQUEST)
            return Response(
                {"error": "Error de validacion en el contrato", "detail": str(error_detail)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except IntegrityError as e:
            logger.error(f"[ContratoViewSet] Error de integridad en create: {str(e)}", exc_info=True)
            # WARNING: v2.60: Error Boundary Pattern - Verificar si es un error de unicidad (contrato activo duplicado)
            error_str = str(e).lower()
            if 'uniq_contrato_activo' in error_str:
                return Response(
                    {
                        "error": "Ya existe un contrato activo para este empleado.",
                        "detail": "Debe cancelar el contrato anterior antes de crear uno nuevo.",
                        "code": "duplicate_contrato"
                    },
                    status=status.HTTP_409_CONFLICT
                )
            return Response(
                {"error": "Error de integridad de datos", "detail": "Verifique los datos ingresados."},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"[ContratoViewSet] Error inesperado en create: {str(e)}", exc_info=True)
            return Response(
                {"error": "Ocurrio un error inesperado al procesar el contrato.", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    
    def list(self, request, *args, **kwargs):
        """
        WARNING: v2.60: Listado paginado con formato DRF {count, results} para Tabulator Factory.
        """
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        # Si no hay paginacion, retornar formato compatible
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'count': len(serializer.data),
            'next': None,
            'previous': None,
            'results': serializer.data
        })
    
    def perform_create(self, serializer):
        """
        WARNING: v2.40: Usa service layer para crear contrato y garantizar unicidad.
        """
        # WARNING: DEBUG: Log de validated_data
        logger.info(f"[ContratoViewSet] validated_data en perform_create: {serializer.validated_data}")
        
        empleado = serializer.validated_data.get('empleado')
        if not empleado:
            logger.error("[ContratoViewSet] Campo 'empleado' no encontrado en validated_data")
            raise ValidationError({'empleado': ['Este campo es requerido.']})
        
        # Validar que el empleado sea una instancia de Empleado
        if not isinstance(empleado, Empleado):
            logger.error(f"[ContratoViewSet] Campo 'empleado' no es una instancia de Empleado: {type(empleado)}")
            raise ValidationError({'empleado': ['El empleado debe ser un ID valido.']})
        
        # Extraer datos del serializer (excluyendo empleado que ya esta validado)
        data = {k: v for k, v in serializer.validated_data.items() if k != 'empleado'}
        data = self.service_preparar_datos_contrato(data)
        
        # Usar service layer para crear contrato
        try:
            contrato = self.service_gestionar_contrato(empleado, data)
            # Actualizar el serializer con la instancia creada
            serializer.instance = contrato
        except ValidationError as ve:
            # Re-lanzar ValidationError sin modificar
            raise ve
        except Exception as e:
            logger.error(f"[ContratoViewSet] Error en perform_create: {str(e)}", exc_info=True)
            raise ValidationError({'detail': [f'Error al crear contrato: {str(e)}']})
    
    def update(self, request, *args, **kwargs):
        """
        WARNING: Paso 4: Sobrescribir update para devolver respuesta JSON con was_updated.
        Permite que los listeners JS distingan entre creacion y actualizacion.
        WARNING: v2.60: Error Boundary Pattern - Manejo de errores estandarizado.
        """
        try:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            
            # WARNING: Paso 4: Devolver respuesta con was_updated para listeners JS
            response_data = serializer.data
            response_data['was_updated'] = True
            response_data['message'] = 'Contrato actualizado correctamente'
            
            return Response(response_data, status=status.HTTP_200_OK)
        except serializers.ValidationError as e:
            logger.error(f"[ContratoViewSet] Error de validacion en update: {str(e)}", exc_info=True)
            # WARNING: v2.60: Error Boundary Pattern - Retornar formato JSON estructurado para UIManager
            error_detail = e.detail if hasattr(e, 'detail') else str(e)
            if isinstance(error_detail, dict):
                return Response(error_detail, status=status.HTTP_400_BAD_REQUEST)
            return Response(
                {"error": "Error de validacion en el contrato", "detail": str(error_detail)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except IntegrityError as e:
            logger.error(f"[ContratoViewSet] Error de integridad en update: {str(e)}", exc_info=True)
            # WARNING: v2.60: Error Boundary Pattern - Verificar si es un error de unicidad
            error_str = str(e).lower()
            if 'uniq_contrato_activo' in error_str:
                return Response(
                    {
                        "error": "Ya existe un contrato activo para este empleado.",
                        "detail": "Debe cancelar el contrato anterior antes de crear uno nuevo.",
                        "code": "duplicate_contrato"
                    },
                    status=status.HTTP_409_CONFLICT
                )
            return Response(
                {"error": "Error de integridad de datos", "detail": "Verifique los datos ingresados."},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"[ContratoViewSet] Error inesperado en update: {str(e)}", exc_info=True)
            return Response(
                {"error": "Ocurrio un error inesperado al procesar el contrato.", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def partial_update(self, request, *args, **kwargs):
        """
        WARNING: Paso 4: Sobrescribir partial_update para devolver respuesta JSON con was_updated.
        """
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)
    
    def perform_update(self, serializer):
        """
        WARNING: Paso 4: Metodo para actualizar contrato existente.
        Usa service layer para garantizar integridad.
        """
        instance = serializer.instance
        empleado = serializer.validated_data.get('empleado', instance.empleado)
        
        # Extraer datos del serializer (excluyendo empleado que ya esta validado)
        data = {k: v for k, v in serializer.validated_data.items() if k != 'empleado'}
        data = self.service_preparar_datos_contrato(data)
        
        # Usar service layer para actualizar contrato
        try:
            contrato = self.service_gestionar_contrato(empleado, data, contrato_existente=instance)
            # Actualizar el serializer con la instancia actualizada
            serializer.instance = contrato
        except ValidationError as ve:
            raise ve
        except Exception as e:
            logger.error(f"[ContratoViewSet] Error en perform_update: {str(e)}", exc_info=True)
            raise ValidationError({'detail': [f'Error al actualizar contrato: {str(e)}']})
    
    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='render-offcanvas/crear')
    def render_offcanvas_crear(self, request):
        """
        Endpoint HTMX para cargar offcanvas de creacion de contratos.
        - Con ?empleado=ID → modo directo (empleado pre-seleccionado)
        - Sin ?empleado    → modo independiente (selector de empleados activos)
        """
        empresa = self.get_empresa()
        empleado_id = request.query_params.get('empleado')

        if empleado_id:
            try:
                empleado = self.get_empleado_by_id(empleado_id)
            except Exception as e:
                logger.error(f"[ContratoViewSet] Empleado no encontrado: {str(e)}")
                return Response(
                    {"error": "Empleado no encontrado o no pertenece a este tenant."},
                    status=status.HTTP_404_NOT_FOUND
                )
            context = {
                'empleado': empleado,
                'contrato': None,
                'empresa': empresa,
                'modo_independiente': False,
            }
        else:
            # Empleados que ya tienen contrato activo — se excluyen del selector.
            # Un empleado con contrato activo no puede recibir un segundo contrato activo.
            ya_contratados = (
                Contrato.objects.filter(empresa_id=empresa.id, estado='ACTIVO')
                .values_list('empleado_id', flat=True)
            )
            empleados_qs = (
                Empleado.objects.filter(empresa_id=empresa.id, estado='ACTIVO')
                .exclude(id__in=ya_contratados)
                .only('id', 'primer_nombre', 'primer_apellido', 'numero_documento')
                .order_by('primer_apellido', 'primer_nombre')
            )
            context = {
                'empleado': None,
                'contrato': None,
                'empresa': empresa,
                'modo_independiente': True,
                'empleados_disponibles': empleados_qs,
            }

        return Response(context, template_name='tenant/empleados/offcanvas_crear_contrato.html')
    
    @action(detail=True, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='render-offcanvas/editar')
    def render_offcanvas_editar(self, request, **kwargs):
        """
        Endpoint HTMX RESTful para cargar offcanvas de edicion de contratos.
        
        WARNING: v2.61: Feature-Sliced Architecture - Template dedicado para edicion
        - GET /api/v1/empleados/contratos/{id}/render-offcanvas/editar/  Modo edicion
        
        Returns:
            Template HTML: tenant/core/partials/empleados/contrato_offcanvas_editar.html
        """
        empresa = self.get_empresa()
        
        try:
            contrato = self.get_object()
            # WARNING: Zero Trust: Validar que el contrato pertenezca al tenant
            if contrato.empresa_id != empresa.id:
                return Response(
                    {"error": "El contrato no pertenece a este tenant."},
                    status=status.HTTP_403_FORBIDDEN
                )
        except Contrato.DoesNotExist:
            logger.error(f"[ContratoViewSet] Contrato no encontrado: {kwargs.get('uuid')}")
            return Response(
                {"error": "Contrato no encontrado."},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"[ContratoViewSet] Error al obtener contrato: {str(e)}", exc_info=True)
            return Response(
                {"error": "Error al cargar el contrato."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        context = {
            'contrato': contrato,
            'empleado': contrato.empleado,
            'empresa': empresa
        }
        return Response(context, template_name='tenant/empleados/offcanvas_editar_contrato.html')

    @action(detail=True, methods=['get'], renderer_classes=[TemplateHTMLRenderer, JSONRenderer], url_path='render-offcanvas/detalle')
    def render_offcanvas_detalle(self, request, **kwargs):
        """
        Endpoint HTMX para cargar offcanvas de detalle de contrato.
        """
        empresa = self.get_empresa()
        try:
            contrato = self.get_object()
            if contrato.empresa_id != empresa.id:
                return Response({"error": "No autorizado"}, status=status.HTTP_403_FORBIDDEN)
        except:
            return Response({"error": "No encontrado"}, status=status.HTTP_404_NOT_FOUND)
            
        context = {'contrato': contrato, 'empleado': contrato.empleado, 'empresa': empresa}
        return Response(context, template_name='tenant/empleados/offcanvas_detalle_contrato.html')
    
    @action(detail=True, methods=['post'], url_path='cancelar')
    def cancelar(self, request, uuid=None):
        """
        WARNING: v2.40: Maquina de Estados - Cambia el estado de un contrato a INACTIVO.
        WARNING: v2.60: Error Boundary Pattern - Manejo de errores estandarizado.
        """
        try:
            contrato = self.get_object()
            if contrato.estado == 'INACTIVO':
                return Response(
                    {"error": "El contrato ya esta inactivo.", "detail": "No se puede cancelar un contrato que ya esta inactivo."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            contrato = self.service_gestionar_contrato(
                contrato.empleado,
                {'estado': 'INACTIVO'},
                contrato_existente=contrato,
            )
            
            serializer = self.get_serializer(contrato)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"[ContratoViewSet] Error al cancelar contrato: {str(e)}", exc_info=True)
            return Response(
                {"error": "Ocurrio un error inesperado al cancelar el contrato.", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'], url_path='simular-liquidacion')
    def simular_liquidacion(self, request, uuid=None):
        """
        Simula la liquidacion de prestaciones sociales para un contrato a una fecha corte dada.
        """
        try:
            contrato = self.get_object()
            fecha_corte = request.query_params.get('fecha_corte')
            tipo_liquidacion = request.query_params.get('tipo_liquidacion', 'DEFINITIVA')
            
            dias_salario_pendiente = request.query_params.get('dias_salario_pendiente', 0)
            indemnizacion = request.query_params.get('indemnizacion', 0)
            try:
                dias_salario_pendiente = int(dias_salario_pendiente) if dias_salario_pendiente else 0
            except (ValueError, TypeError):
                dias_salario_pendiente = 0
            try:
                indemnizacion = Decimal(str(indemnizacion)) if indemnizacion else Decimal('0.00')
            except (ValueError, TypeError):
                indemnizacion = Decimal('0.00')

            if not fecha_corte:
                fecha_corte = date.today().isoformat()

            resultados = NominaCalculationService.calcular_liquidacion_prestaciones(
                contrato=contrato,
                tipo_liquidacion=tipo_liquidacion,
                fecha_corte=fecha_corte,
                dias_salario_pendiente=dias_salario_pendiente,
                indemnizacion=indemnizacion
            )

            # Convertir Decimal a String para JSONResponse
            for k, v in list(resultados.items()):
                if isinstance(v, Decimal):
                    resultados[k] = str(v)

            return Response(resultados, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"[ContratoViewSet] Error al simular liquidacion: {str(e)}", exc_info=True)
            return Response(
                {"error": "Ocurrio un error al simular la liquidacion.", "detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class DevengoViewSet(SintelDSVMixin, DevengoServiceMixin, BaseTenantViewSet):
    """
    WARNING: v2.62.4: ViewSet para Nomina migrado a BaseTenantViewSet.
    v3.6.1: UUID lookup field (AGENTS.md 14) - hereda lookup_field="uuid" de BaseTenantViewSet.
    """
    serializer_class = DevengoSerializer
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['empleado', 'anulado']
    ordering_fields = ['fecha_pago', 'periodo_mes', 'id']
    ordering = ['-fecha_pago', '-periodo_mes', 'id']

    @cached_property
    def tenant_empresa(self):
        return resolve_tenant_empresa(self.request, self)

    def get_empresa(self):
        return self.tenant_empresa
    
    def get_queryset(self):
        """
        WARNING: v4.8.0: QuerySet optimizado usando service layer con soporte Master-Detail.
        El parametro empleado_uuid filtra el historial del panel Detail.
        """
        if self.action == 'list':
            queryset = self.get_qs_list()

            # v4.8.0: Master-Detail — filtrar por empleado en el panel Detail
            empleado_uuid = self.request.query_params.get('empleado_uuid')
            if empleado_uuid:
                queryset = queryset.filter(empleado__uuid=empleado_uuid)

            # Filtros de fecha para historial (mantiene compatibilidad v2.95)
            fecha_inicio = self.request.query_params.get('fecha_inicio')
            fecha_fin = self.request.query_params.get('fecha_fin')

            if fecha_inicio:
                try:
                    fecha_inicio_obj = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
                    queryset = queryset.filter(fecha_pago__gte=fecha_inicio_obj)
                except (ValueError, TypeError):
                    logger.warning(f"[DevengoViewSet] Formato de fecha_inicio invalido: {fecha_inicio}")

            if fecha_fin:
                try:
                    fecha_fin_obj = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
                    queryset = queryset.filter(fecha_pago__lte=fecha_fin_obj)
                except (ValueError, TypeError):
                    logger.warning(f"[DevengoViewSet] Formato de fecha_fin invalido: {fecha_fin}")

            return queryset

        return self.get_qs_detail()

    def get_object(self):
        """
        v3.6.1: UUID lookup estricto (AGENTS.md Sec. 14).
        """
        try:
            return self.get_qs_detail()
        except Devengo.DoesNotExist as exc:
            lookup_value = self.kwargs.get(self.lookup_url_kwarg or self.lookup_field)
            raise NotFound(
                f'Nomina {lookup_value} no encontrada o no pertenece a este tenant.'
            ) from exc

    def get_serializer_context(self):
        context = super().get_serializer_context()
        empresa = self.get_empresa()
        context['empresa'] = empresa
        context['empresa_id'] = empresa.id if empresa else None
        return context
    
    def list(self, request, *args, **kwargs):
        """
        WARNING: v2.60: Listado paginado con formato DRF {count, results} para Tabulator Factory.
        """
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        # Si no hay paginacion, retornar formato compatible
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'count': len(serializer.data),
            'next': None,
            'previous': None,
            'results': serializer.data
        })

    def create(self, request, *args, **kwargs):
        """
        WARNING: v2.60: Sobrescribir create con validacion estricta de duplicados (Zero Trust).
        Prohibe el Upsert automatico para proteger la evidencia legal de la nomina.
        Retorna errores en formato JSON para UIManager.handleError.
        
        WARNING: Validacion Preventiva: Verifica duplicados ANTES de validar serializer.
        Si existe una nomina para el mismo empleado y periodo, retorna error 409 Conflict.
        """
        try:
            # WARNING: [SEC-M6] Solo nombres de campo y tipo, no valores (montos de
            # devengo son datos salariales/PII).
            logger.info(f"[DevengoViewSet] Campos recibidos en create: {list(request.data.keys()) if hasattr(request.data, 'keys') else type(request.data).__name__}")

            duplicate_error = self.service_validar_duplicado(request.data)
            if duplicate_error:
                return Response(duplicate_error, status=status.HTTP_409_CONFLICT)
            
            # Validar datos del serializer
            serializer = self.get_serializer(data=request.data)
            
            if not serializer.is_valid():
                # WARNING: v2.60: Capturar error de unicidad en non_field_errors si viene del modelo
                if 'non_field_errors' in serializer.errors:
                    for error in serializer.errors['non_field_errors']:
                        if 'unique' in str(error).lower() or 'duplicate' in str(error).lower():
                            return Response(
                                {
                                    "error": "Ya existe una nomina para este empleado, periodo y fecha de pago. Debe anular la nomina existente antes de crear una nueva.",
                                    "detail": "No se puede crear una nomina duplicada para el mismo empleado, periodo y fecha de pago. Puede registrar multiples nominas en el mismo mes usando diferentes fechas de pago.",
                                    "code": "duplicate_nomina"
                                },
                                status=status.HTTP_409_CONFLICT
                            )
                
                # WARNING: v2.60: Retornar errores de validacion en formato estructurado para UIManager
                logger.error(f"[DevengoViewSet] Error de validacion en create: {serializer.errors}")
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            # Ejecutar perform_create que calcula valores y guarda (creacion nueva)
            self.perform_create(serializer)
            
            # WARNING: Paso 4: Retornar respuesta con was_updated para listeners JS
            headers = self.get_success_headers(serializer.data)
            response_data = {
                **serializer.data,
                "was_updated": False,
                "message": "Nomina creada correctamente"
            }
            return Response(
                response_data,
                status=status.HTTP_201_CREATED,
                headers=headers
            )
            
        except serializers.ValidationError as e:
            logger.error(f"[DevengoViewSet] Error de validacion en create: {str(e)}", exc_info=True)
            # WARNING: v2.60: Error Boundary Pattern - Retornar formato JSON estructurado para UIManager
            error_detail = e.detail if hasattr(e, 'detail') else str(e)
            if isinstance(error_detail, dict):
                return Response(error_detail, status=status.HTTP_400_BAD_REQUEST)
            return Response(
                {"error": "Error de validacion en la nomina", "detail": str(error_detail)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except ValueError as e:
            logger.error(f"[DevengoViewSet] Error en create (ValueError): {str(e)}", exc_info=True)
            return Response(
                {"error": str(e), "detail": "Error en los datos proporcionados."},
                status=status.HTTP_400_BAD_REQUEST
            )
        except IntegrityError as e:
            logger.error(f"[DevengoViewSet] Error de integridad en create: {str(e)}", exc_info=True)
            # WARNING: v2.60: Error Boundary Pattern - Capturar error de unicidad especifico
            error_str = str(e).lower()
            if 'uniq_nomina_per_empleado_periodo' in error_str or 'unique constraint' in error_str:
                return Response(
                    {
                        "error": "Ya existe una nomina registrada para este empleado en el periodo seleccionado.",
                        "detail": "No se puede crear una nomina duplicada. Si desea modificarla, debe anular la nomina existente primero.",
                        "code": "duplicate_nomina"
                    },
                    status=status.HTTP_409_CONFLICT
                )
            return Response(
                {"error": "Error de integridad de datos", "detail": "Verifique los datos ingresados."},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"[DevengoViewSet] Error inesperado en create: {str(e)}", exc_info=True)
            return Response(
                {"error": "Ocurrio un error inesperado al procesar la nomina.", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def update(self, request, *args, **kwargs):
        """
        WARNING: v2.60: Permite actualizacion solo a traves de logica de Upsert en create().
        Metodo directo bloqueado para mantener inmutabilidad explicita.
        """
        return Response(
            {"detail": "Para actualizar una nomina, use el endpoint de creacion. El sistema detectara automaticamente si existe una nomina para el mismo periodo y la actualizara."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )
    
    def partial_update(self, request, *args, **kwargs):
        """
        WARNING: v2.60: Permite actualizacion solo a traves de logica de Upsert en create().
        Metodo directo bloqueado para mantener inmutabilidad explicita.
        """
        return Response(
            {"detail": "Para actualizar una nomina, use el endpoint de creacion. El sistema detectara automaticamente si existe una nomina para el mismo periodo y la actualizara."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )
    
    def destroy(self, request, *args, **kwargs):
        """
        WARNING: v2.60: Eliminacion de nomina (Hard Delete).
        Valida Zero Trust y registra en log de auditoria.
        """
        instance = self.get_object()
        
        try:
            devengo_id = self.service_eliminar_devengo(instance, request)
            
            return Response(
                {"detail": "Nomina eliminada correctamente", "id": devengo_id},
                status=status.HTTP_200_OK
            )
        except serializers.ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            logger.error(f"[DevengoViewSet] Error al eliminar nomina: {str(e)}", exc_info=True)
            return Response(
                {"error": "Ocurrio un error inesperado al eliminar la nomina.", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def perform_update(self, serializer):
        """
        WARNING: v2.60: Metodo para actualizar nomina existente (usado en logica de Upsert).
        Recalcula todos los valores usando la Capa de Servicio antes de guardar (Zero Trust).
        """
        serializer.instance = self.service_procesar_devengo(serializer, instance=serializer.instance)

    def perform_create(self, serializer):
        """
        WARNING: v2.40: Usa el service layer para calcular valores proporcionales antes de guardar.
        """
        serializer.instance = self.service_procesar_devengo(serializer)

    @action(detail=True, methods=["post"], url_path="anular")
    def anular(self, request, uuid=None):
        instance = self.get_object()
        devengo = self.service_anular_devengo(instance)
        return Response({"status": "Anulado correctamente", "id": devengo.id})
    
    @action(detail=False, methods=["post"], renderer_classes=[TemplateHTMLRenderer, JSONRenderer], url_path="preview-calculo", permission_classes=[IsTenantMember])
    def preview_calculo(self, request):
        """
        WARNING: v2.60: Endpoint para previsualizar calculo de nomina en tiempo real (HTMX Partial).
        Devuelve un partial HTML con los valores calculados actualizados.
        """
        ERROR_TEMPLATE = 'tenant/empleados/devengo_error_partial.html'
        PENDING_TEMPLATE = 'tenant/empleados/devengo_pending_partial.html'

        empresa = self.get_empresa()
        if not empresa:
            return Response(
                {"error": "No se encontro configuracion de Empresa para este tenant."},
                status=status.HTTP_403_FORBIDDEN,
                template_name=ERROR_TEMPLATE,
            )

        empresa_id = empresa.id

        try:
            contrato_id    = request.data.get('contrato')     or request.POST.get('contrato')
            dias_laborados = request.data.get('dias_laborados') or request.POST.get('dias_laborados')
            periodo_mes    = request.data.get('periodo_mes')  or request.POST.get('periodo_mes')
            fecha_pago     = request.data.get('fecha_pago')   or request.POST.get('fecha_pago')
            horas_trabajadas = request.data.get('horas_trabajadas') or request.POST.get('horas_trabajadas')

            # Estado transiente normal del formulario reactivo HTMX:
            # el contrato se carga async; si aún no llegó, devolvemos placeholder 200.
            if not contrato_id:
                return Response(
                    {"mensaje": "Seleccione un empleado para calcular el neto a pagar."},
                    status=status.HTTP_200_OK,
                    template_name=PENDING_TEMPLATE,
                )

            if not dias_laborados:
                return Response(
                    {"mensaje": "Ingrese los dias laborados para previsualizar el calculo."},
                    status=status.HTTP_200_OK,
                    template_name=PENDING_TEMPLATE,
                )
            
            # WARNING: v2.60: Zero Trust - Obtener contrato ACTIVO validando empresa_id
            try:
                contrato = self.get_contrato_by_id(contrato_id)
                if contrato.estado != 'ACTIVO' or not contrato.activo:
                    raise Contrato.DoesNotExist
            except Contrato.DoesNotExist:
                return Response({
                    "error": "Contrato no encontrado o no esta activo."
                }, status=status.HTTP_404_NOT_FOUND, template_name=ERROR_TEMPLATE)

            # WARNING: v2.60: Validar dias laborados (permite decimales 0.5-30)
            try:
                dias_laborados = Decimal(str(dias_laborados))
            except (ValueError, InvalidOperation):
                return Response({
                    "error": "Los dias laborados deben ser un numero valido."
                }, status=status.HTTP_400_BAD_REQUEST, template_name=ERROR_TEMPLATE)

            if dias_laborados < Decimal('0.5'):
                return Response({
                    "error": "Los dias laborados deben ser al menos 0.5."
                }, status=status.HTTP_400_BAD_REQUEST, template_name=ERROR_TEMPLATE)

            # WARNING: v2.60: Validar horas trabajadas si se proporciona
            horas_trabajadas_decimal = None
            if horas_trabajadas is not None:
                try:
                    horas_trabajadas_decimal = Decimal(str(horas_trabajadas))
                    if horas_trabajadas_decimal < 0:
                        return Response({
                            "error": "Las horas trabajadas no pueden ser negativas."
                        }, status=status.HTTP_400_BAD_REQUEST, template_name=ERROR_TEMPLATE)
                except (ValueError, InvalidOperation):
                    return Response({
                        "error": "Las horas trabajadas deben ser un numero valido."
                    }, status=status.HTTP_400_BAD_REQUEST, template_name=ERROR_TEMPLATE)

            # WARNING: v2.60: Normalizacion de decimales usando Decimal para precision
            try:
                otros_devengos = Decimal(str(request.data.get('otros_devengos', 0) or request.POST.get('otros_devengos', 0) or 0))
                prestamos = Decimal(str(request.data.get('prestamos', 0) or request.POST.get('prestamos', 0) or 0))
                descuentos_operativos = Decimal(str(request.data.get('descuentos_operativos', 0) or request.POST.get('descuentos_operativos', 0) or 0))
            except (ValueError, InvalidOperation, TypeError) as e:
                return Response({
                    "error": f"Error en formato de datos numericos: {str(e)}"
                }, status=status.HTTP_400_BAD_REQUEST, template_name=ERROR_TEMPLATE)

            if prestamos > 0:
                prestamo_disponible = Decimal(str(contrato.prestamos_empresa or 0))
                if prestamos > prestamo_disponible:
                    return Response({
                        "error": f"El monto a descontar (${prestamos:,.2f}) supera el prestamo disponible en el contrato (${prestamo_disponible:,.2f})."
                    }, status=status.HTTP_400_BAD_REQUEST, template_name=ERROR_TEMPLATE)
            
            # WARNING: v2.60: Calcular usando NominaCalculationService.calcular_liquidacion (SSoT - Normativa Colombiana)
            # WARNING: Zero Trust: Pasar empresa_id para validacion
            def _get_decimal(key, default=0):
                val = request.data.get(key) or request.POST.get(key) or default
                try:
                    return Decimal(str(val))
                except Exception:
                    return Decimal('0')

            calculo = NominaCalculationService.calcular_liquidacion(
                contrato=contrato,
                dias_laborados=dias_laborados,
                horas_trabajadas=horas_trabajadas_decimal,
                otros_devengos=otros_devengos,
                prestamos=prestamos,
                descuentos_operativos=descuentos_operativos,
                empresa_id=empresa_id,
                horas_extras_diurnas=_get_decimal('horas_extras_diurnas'),
                horas_extras_nocturnas=_get_decimal('horas_extras_nocturnas'),
                recargo_nocturno_horas=_get_decimal('recargo_nocturno_horas'),
                recargo_festivo_horas=_get_decimal('recargo_festivo_horas'),
            )
            
            # WARNING: Error Boundary Pattern: Validar que el neto no sea negativo
            neto_pagar = Decimal(calculo['neto_pagar'])
            if neto_pagar < 0:
                return Response({
                    "error": f"El neto a pagar no puede ser negativo (${neto_pagar:,.2f}). Revise los descuentos y prestamos."
                }, status=status.HTTP_400_BAD_REQUEST, template_name=ERROR_TEMPLATE)
            
            # Retornar partial HTML con los valores calculados
            context = {
                "calculo": calculo,
                "contrato": contrato
            }
            
            return Response(context, template_name='tenant/empleados/devengo_calculo_partial.html')
            
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST, template_name=ERROR_TEMPLATE)
        except (InvalidOperation, TypeError) as e:
            return Response({"error": f"Error en formato de datos numericos: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST, template_name=ERROR_TEMPLATE)
        except Exception as e:
            logger.error(f"[DevengoViewSet] Error en preview_calculo: {str(e)}", exc_info=True)
            return Response({
                "error": "Ocurrio un error inesperado al calcular la nomina.",
                "detail": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR, template_name=ERROR_TEMPLATE)
    
    @action(detail=False, methods=['get'], url_path='empleados-disponibles', permission_classes=[IsTenantMember])
    def empleados_disponibles(self, request):
        """
        GET /api/v1/empleados/devengos/empleados-disponibles/?fecha_inicio=YYYY-MM-DD&fecha_fin=YYYY-MM-DD
        Retorna empleados ACTIVOS con contrato activo que NO tienen nominas solapadas en ese rango.
        """
        empresa = self.get_empresa()
        if not empresa:
            return Response({"error": "sin_empresa"}, status=status.HTTP_404_NOT_FOUND)

        fecha_inicio_str = request.query_params.get('fecha_inicio')
        fecha_fin_str    = request.query_params.get('fecha_fin')

        if not fecha_inicio_str or not fecha_fin_str:
            return Response({"error": "fecha_inicio y fecha_fin son requeridos"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            fecha_inicio = date.fromisoformat(fecha_inicio_str)
            fecha_fin    = date.fromisoformat(fecha_fin_str)
        except (ValueError, TypeError):
            return Response({"error": "Formato de fecha invalido. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)

        if fecha_inicio > fecha_fin:
            return Response({"error": "fecha_inicio no puede ser mayor que fecha_fin"}, status=status.HTTP_400_BAD_REQUEST)

        empleados = EmpleadoSelector.get_disponibles_para_periodo(
            empresa_id=empresa.id,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin
        )

        return Response([
            {
                "id":               emp.id,
                "uuid":             str(emp.uuid),
                "primer_nombre":    emp.primer_nombre,
                "primer_apellido":  emp.primer_apellido,
                "numero_documento": emp.numero_documento,
                "nombre_completo":  f"{emp.primer_nombre} {emp.primer_apellido}",
            }
            for emp in empleados
        ], status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='ultimo-periodo', permission_classes=[IsTenantMember])
    def ultimo_periodo(self, request):
        """
        GET /api/v1/empleados/devengos/ultimo-periodo/?empleado=ID
        Retorna el ultimo devengo no anulado del empleado con fecha_inicio/fin garantizadas.
        Si el devengo es legacy (sin fechas), las deriva del periodo_mes.
        """
        empresa  = self.get_empresa()
        if not empresa:
            return Response({'tiene_nominas': False, 'ultimo': None})

        empleado_id = request.query_params.get('empleado', '')
        if not empleado_id:
            return Response({'tiene_nominas': False, 'ultimo': None})

        ultimo = (
            Devengo.objects
            .filter(empresa_id=empresa.id, empleado_id=empleado_id, anulado=False)
            .order_by('-fecha_fin', '-fecha_pago', '-periodo_mes')
            .only('id', 'periodo_mes', 'fecha_inicio', 'fecha_fin', 'fecha_pago',
                  'dias_laborados', 'neto_pagar')
            .first()
        )

        if not ultimo:
            return Response({'tiene_nominas': False, 'ultimo': None})

        fi = ultimo.fecha_inicio
        ff = ultimo.fecha_fin
        if not fi or not ff:
            try:
                y, m = map(int, ultimo.periodo_mes.split('-'))
                fi = date(y, m, 1)
                ff = date(y, m, calendar.monthrange(y, m)[1])
            except Exception:
                fi = ff = None

        return Response({
            'tiene_nominas': True,
            'ultimo': {
                'id':            ultimo.id,
                'periodo_mes':   ultimo.periodo_mes,
                'fecha_inicio':  str(fi) if fi else None,
                'fecha_fin':     str(ff) if ff else None,
                'fecha_pago':    str(ultimo.fecha_pago) if ultimo.fecha_pago else None,
                'dias_laborados': str(ultimo.dias_laborados),
                'neto_pagar':    str(ultimo.neto_pagar),
            }
        })

    @action(detail=False, methods=['get'], url_path='verificar-periodo', permission_classes=[IsTenantMember])
    def verificar_periodo(self, request):
        """
        GET /api/v1/empleados/devengos/verificar-periodo/?empleado=ID&periodo_mes=YYYY-MM
                                                          &dias=N&fecha_inicio=YYYY-MM-DD&fecha_fin=YYYY-MM-DD
        Detecta solapamiento exacto por rango de fechas.
        Retorna: puede_crear, conflictos[], dias_registrados, dias_disponibles.
        """
        empresa = self.get_empresa()
        if not empresa:
            return Response({'puede_crear': False, 'error': 'sin_empresa'}, status=status.HTTP_403_FORBIDDEN)

        empleado_id  = request.query_params.get('empleado')
        periodo_mes  = request.query_params.get('periodo_mes')
        dias_str     = request.query_params.get('dias', '0')
        fecha_inicio = request.query_params.get('fecha_inicio')
        fecha_fin    = request.query_params.get('fecha_fin')

        if not empleado_id or not periodo_mes:
            return Response({'puede_crear': True, 'conflictos': [], 'dias_registrados': '0', 'dias_disponibles': '31'})

        qs_base = Devengo.objects.filter(
            empresa_id=empresa.id,
            empleado_id=empleado_id,
            anulado=False,
        )

        conflictos_qs = qs_base
        if fecha_inicio and fecha_fin:
            conflictos_qs = qs_base.filter(
                fecha_inicio__lte=fecha_fin,
                fecha_fin__gte=fecha_inicio,
            )
        else:
            conflictos_qs = qs_base.filter(periodo_mes=periodo_mes)

        conflictos_qs = conflictos_qs.only(
            'id', 'uuid', 'periodo_mes', 'fecha_inicio', 'fecha_fin', 'dias_laborados'
        )

        conflictos = [
            {
                'id':            c.id,
                'uuid':          str(c.uuid),
                'periodo_mes':   c.periodo_mes,
                'fecha_inicio':  str(c.fecha_inicio) if c.fecha_inicio else None,
                'fecha_fin':     str(c.fecha_fin) if c.fecha_fin else None,
                'dias_laborados': str(c.dias_laborados),
            }
            for c in conflictos_qs[:5]
        ]

        dias_registrados = qs_base.filter(periodo_mes=periodo_mes).aggregate(
            total=Sum('dias_laborados')
        )['total'] or Decimal('0')

        try:
            dias_solicitados = Decimal(str(dias_str))
        except Exception:
            dias_solicitados = Decimal('0')

        dias_disponibles = max(Decimal('0'), Decimal('31') - dias_registrados)
        puede_crear = len(conflictos) == 0

        return Response({
            'puede_crear':       puede_crear,
            'conflictos':        conflictos,
            'dias_registrados':  str(dias_registrados),
            'dias_disponibles':  str(dias_disponibles),
        })

    @action(detail=False, methods=['get'], url_path='empleados-con-nominas', permission_classes=[IsTenantMember])
    def empleados_con_nominas(self, request):
        """
        GET /api/v1/empleados/devengos/empleados-con-nominas/
        Retorna empleados que tienen al menos una nomina registrada, con info agregada
        (total nominas, ultimo periodo, ultimo neto) para la vista de lista por empleado.
        """
        empresa = self.get_empresa()
        if not empresa:
            return Response({'error': 'Sin empresa'}, status=status.HTTP_403_FORBIDDEN)

        counts = dict(
            Devengo.objects.filter(empresa=empresa)
            .values('empleado_id')
            .annotate(cnt=Count('id'))
            .values_list('empleado_id', 'cnt')
        )

        if not counts:
            return Response({'count': 0, 'results': []})

        latest_sq = Devengo.objects.filter(
            empresa=empresa,
            empleado_id=OuterRef('id'),
        ).order_by('-fecha_pago', '-id')

        empleados_qs = Empleado.objects.filter(
            empresa=empresa,
            id__in=counts.keys(),
        ).annotate(
            ultimo_neto=Subquery(latest_sq.values('neto_pagar')[:1]),
            ultimo_periodo=Subquery(latest_sq.values('periodo_mes')[:1]),
            ultimo_cargo=Subquery(latest_sq.values('contrato__cargo')[:1]),
        ).only(
            'id', 'uuid', 'primer_nombre', 'primer_apellido', 'numero_documento'
        ).order_by('primer_apellido', 'primer_nombre')

        search = request.query_params.get('search', '').strip()
        if search:
            empleados_qs = empleados_qs.filter(
                Q(primer_nombre__icontains=search) |
                Q(primer_apellido__icontains=search) |
                Q(numero_documento__icontains=search)
            )

        results = [{
            'empleado_id': emp.id,
            'empleado_uuid': str(emp.uuid),
            'empleado_nombre': f"{emp.primer_nombre} {emp.primer_apellido}",
            'empleado_documento': emp.numero_documento,
            'cargo': emp.ultimo_cargo or '',
            'total_nominas': counts.get(emp.id, 0),
            'ultimo_periodo': emp.ultimo_periodo or '',
            'ultimo_neto': str(emp.ultimo_neto or '0.00'),
        } for emp in empleados_qs]

        return Response({'count': len(results), 'results': results})

    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='render-offcanvas/crear')
    def render_offcanvas_crear(self, request):
        """Sirve el formulario unificado de Registrar Nomina (un solo paso)."""
        empresa = self.get_empresa()
        return Response({'empresa': empresa}, template_name='tenant/empleados/offcanvas_crear_devengo.html')

    @action(detail=False, methods=['get'], url_path='info-empleado', permission_classes=[IsTenantMember])
    def info_empleado(self, request):
        """
        GET /api/v1/empleados/devengos/info-empleado/?empleado=ID
        Retorna contrato activo + datos del empleado para el formulario unificado de nomina.
        """
        empresa = self.get_empresa()
        empleado_param = request.query_params.get('empleado')
        if not empleado_param:
            return Response({'error': 'empleado es requerido'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            emp = Empleado.objects.filter(
                empresa_id=empresa.id, uuid=empleado_param, estado='ACTIVO'
            ).only(
                'id', 'uuid', 'primer_nombre', 'primer_apellido',
                'numero_documento', 'eps', 'afp', 'arl'
            ).get()
        except Empleado.DoesNotExist:
            return Response({'error': 'Empleado no encontrado'}, status=status.HTTP_404_NOT_FOUND)

        contrato = ContratoSelector.get_activo_for_empleado(empresa.id, emp.id)
        if not contrato:
            return Response({'error': 'El empleado no tiene contrato activo'}, status=status.HTTP_404_NOT_FOUND)

        eps_map = dict(EPS_CHOICES)
        afp_map = dict(AFP_CHOICES)
        arl_map = dict(ARL_CHOICES)

        return Response({
            'empleado': {
                'id':               emp.id,
                'nombre_completo':  f"{emp.primer_nombre} {emp.primer_apellido}",
                'numero_documento': emp.numero_documento,
                'eps_label':        eps_map.get(emp.eps, emp.eps),
                'afp_label':        afp_map.get(emp.afp, emp.afp),
                'arl_label':        arl_map.get(emp.arl, emp.arl),
            },
            'contrato': {
                'id':              contrato.id,
                'uuid':            str(contrato.uuid),
                'tipo':            contrato.tipo,
                'cargo':           contrato.cargo or '',
                'salario_mensual': str(contrato.salario_mensual),
                'auxilio_transporte': str(contrato.auxilio_transporte),
                'horas_semanales': contrato.horas_semanales or 42,
            }
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='render-offcanvas/crear', permission_classes=[IsTenantMember])
    def render_offcanvas_crear(self, request):
        """
        Endpoint HTMX para renderizar el formulario de creacion de devengos.
        """
        empresa = self.get_empresa()
        if not empresa:
            return Response({"error": "Sin tenant asignado"}, status=403)
        
        context = {'empresa_id': empresa.id}
        empleado_param = request.query_params.get('empleado')

        if empleado_param:
            try:
                empleado = EmpleadoSelector.get_detail(empresa.id, empleado_param)
                context['empleado'] = empleado
                contrato_activo = ContratoSelector.get_activo_for_empleado(empresa.id, empleado.id)
                if contrato_activo:
                    context['contrato'] = contrato_activo
            except Empleado.DoesNotExist:
                pass

        # Inject defaults if present
        context['periodo_mes_default'] = request.query_params.get('periodo_mes', '')
        context['fecha_inicio_default'] = request.query_params.get('fecha_inicio', '')
        context['fecha_fin_default'] = request.query_params.get('fecha_fin', '')
        context['fecha_pago_default'] = request.query_params.get('fecha_pago', '')
        context['dias_laborados_default'] = request.query_params.get('dias_laborados', '')

        return Response(context, template_name='tenant/empleados/offcanvas_crear_devengo.html')

    @action(detail=True, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='render-offcanvas/editar', permission_classes=[IsTenantMember])
    def render_offcanvas_editar(self, request, uuid=None):
        """
        Endpoint HTMX para renderizar el formulario de edicion de devengos.
        """
        instance = self.get_object()
        return Response({'devengo': instance}, template_name='tenant/empleados/offcanvas_crear_devengo.html')

    @action(detail=True, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='render-offcanvas/detalle', permission_classes=[IsTenantMember])
    def render_offcanvas_detalle(self, request, uuid=None):
        """
        Endpoint HTMX para renderizar los detalles del devengo.
        """
        instance = self.get_object()
        return Response({'devengo': instance}, template_name='tenant/empleados/offcanvas_crear_devengo.html')


_RESOLUCION_LIST_FIELDS = (
    'id', 'uuid', 'empresa_id',
    'numero_resolucion', 'prefijo',
    'rango_desde', 'rango_hasta', 'consecutivo',
    'fecha_resolucion', 'fecha_inicio', 'fecha_fin',
    'vigente', 'clave_tecnica',
)


class ResolucionDIANViewSet(SintelDSVMixin, BaseTenantViewSet):
    """
    ViewSet para configuracion de Resoluciones DIAN para nomina electronica.
    """
    serializer_class = ResolucionDIANSerializer
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["numero_resolucion", "prefijo"]

    @cached_property
    def tenant_empresa(self):
        return resolve_tenant_empresa(self.request, self)

    def get_empresa(self):
        return self.tenant_empresa

    def get_queryset(self):
        empresa = self.get_empresa()
        if not empresa:
            return ResolucionDIAN.objects.none()
        return (
            ResolucionDIAN.objects
            .filter(empresa_id=empresa.id)
            .only(*_RESOLUCION_LIST_FIELDS)
            .order_by('-vigente', '-fecha_inicio')
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        empresa = self.get_empresa()
        context['empresa'] = empresa
        context['empresa_id'] = empresa.id if empresa else None
        return context

    def perform_create(self, serializer):
        empresa = self.get_empresa()
        serializer.save(empresa=empresa)

    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='render-offcanvas/crear', permission_classes=[IsTenantMember])
    def render_offcanvas_crear(self, request):
        """
        GET /api/v1/empleados/resoluciones-dian/render-offcanvas/crear/
        """
        empresa = self.get_empresa()
        if not empresa:
            return Response({"error": "Sin tenant asignado"}, status=status.HTTP_403_FORBIDDEN)
        context = {
            'empresa_id': empresa.id,
        }
        return Response(context, template_name='tenant/empleados/offcanvas_crear_resolucion.html')



_LIQUIDACION_LIST_FIELDS = (
    'id', 'uuid', 'empresa_id',
    'empleado', 'contrato',
    'tipo_liquidacion', 'fecha_corte',
    'dias_base_calculo', 'base_salarial', 'valor_total', 'estado',
)
_LIQUIDACION_LIST_TRAVERSALS = (
    'empleado__id', 'empleado__uuid',
    'empleado__primer_nombre', 'empleado__primer_apellido',
    'contrato__id', 'contrato__uuid', 'contrato__cargo', 'contrato__tipo',
)


class LiquidacionPrestacionViewSet(SintelDSVMixin, BaseTenantViewSet):
    """
    ViewSet para registro de Liquidaciones de Prestaciones Sociales.
    """
    serializer_class = LiquidacionPrestacionSerializer
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["empleado__primer_nombre", "empleado__primer_apellido", "empleado__numero_documento"]

    @cached_property
    def tenant_empresa(self):
        return resolve_tenant_empresa(self.request, self)

    def get_empresa(self):
        return self.tenant_empresa

    def get_queryset(self):
        empresa = self.get_empresa()
        if not empresa:
            return LiquidacionPrestacion.objects.none()

        qs = (
            LiquidacionPrestacion.objects
            .filter(empresa_id=empresa.id)
            .select_related('empleado', 'contrato')
            .only(*_LIQUIDACION_LIST_FIELDS, *_LIQUIDACION_LIST_TRAVERSALS)
            .order_by('-fecha_corte')
        )

        # Filtro opcional por empleado (usado por Detail panel del Master-Detail)
        empleado_uuid = self.request.query_params.get('empleado_uuid')
        if empleado_uuid:
            qs = qs.filter(empleado__uuid=empleado_uuid)

        return qs


    def get_serializer_context(self):
        context = super().get_serializer_context()
        empresa = self.get_empresa()
        context['empresa'] = empresa
        context['empresa_id'] = empresa.id if empresa else None
        return context

    def create(self, request, *args, **kwargs):
        """
        POST /api/v1/empleados/liquidaciones-prestaciones/
        Calcula dias/base/valor ANTES de llamar is_valid() para que el serializer
        reciba todos los campos requeridos del modelo.
        El form envia: empleado_id, contrato_id, tipo_liquidacion, fecha_corte.
        """
        empresa = self.get_empresa()
        if not empresa:
            return Response({'detail': 'Empresa no configurada.'}, status=status.HTTP_400_BAD_REQUEST)

        contrato_id = request.data.get('contrato_id')
        fecha_corte = request.data.get('fecha_corte')
        tipo_liq    = request.data.get('tipo_liquidacion', 'LIQUIDACION_DEFINITIVA')

        # Nuevos parametros opcionales
        dias_salario_pendiente = request.data.get('dias_salario_pendiente', 0)
        indemnizacion = request.data.get('indemnizacion', 0)
        observaciones = request.data.get('observaciones', '')

        try:
            dias_salario_pendiente = int(dias_salario_pendiente) if dias_salario_pendiente else 0
        except (ValueError, TypeError):
            dias_salario_pendiente = 0

        try:
            indemnizacion = Decimal(str(indemnizacion)) if indemnizacion else Decimal('0.00')
        except (ValueError, TypeError):
            indemnizacion = Decimal('0.00')

        if not contrato_id or not fecha_corte:
            return Response(
                {'detail': 'contrato_id y fecha_corte son requeridos.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # DSV: verificar contrato en el tenant
        try:
            contrato = Contrato.objects.filter(
                empresa_id=empresa.id, id=int(contrato_id)
            ).only(
                'id', 'uuid', 'tipo', 'estado', 'empresa_id',
                'salario_mensual', 'auxilio_transporte', 'fecha_inicio',
                'prestamos_empresa',
            ).get()
        except (Contrato.DoesNotExist, ValueError, TypeError):
            return Response(
                {'detail': 'Contrato no encontrado o no pertenece a este tenant.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Calcular prestaciones con NominaCalculationService
        resultados = NominaCalculationService.calcular_liquidacion_prestaciones(
            contrato=contrato,
            tipo_liquidacion=tipo_liq,
            fecha_corte=fecha_corte,
            dias_salario_pendiente=dias_salario_pendiente,
            indemnizacion=indemnizacion
        )

        if tipo_liq == 'PRIMA_SERVICIOS':
            dias  = resultados['dias_primas']
            valor = resultados['valor_primas']
        elif tipo_liq == 'CESANTIAS':
            dias  = resultados['dias_cesantias']
            valor = resultados['valor_cesantias']
        elif tipo_liq == 'VACACIONES':
            dias  = resultados['dias_vacaciones']
            valor = resultados['valor_vacaciones']
        else:   # LIQUIDACION_DEFINITIVA
            dias  = resultados['dias_cesantias']
            valor = resultados['total_neto']

        salario_base_liq = (
            Decimal(str(contrato.salario_mensual)) +
            Decimal(str(contrato.auxilio_transporte))
        )

        # Serializar desglose para almacenar en JSONField
        desglose = {
            'dias_primas': resultados['dias_primas'],
            'dias_cesantias': resultados['dias_cesantias'],
            'dias_intereses': resultados['dias_intereses'],
            'dias_vacaciones': resultados['dias_vacaciones'],
            'valor_primas': str(resultados['valor_primas']),
            'valor_cesantias': str(resultados['valor_cesantias']),
            'valor_intereses': str(resultados['valor_intereses']),
            'valor_vacaciones': str(resultados['valor_vacaciones']),
            'total_prestaciones': str(resultados['total_prestaciones']),
            'dias_salario_pendiente': resultados['dias_salario_pendiente'],
            'salario_pendiente': str(resultados['salario_pendiente']),
            'indemnizacion': str(resultados['indemnizacion']),
            'prestamos_deducidos': str(resultados['prestamos_deducidos']),
            'total_neto': str(resultados['total_neto']),
            'fecha_inicio_contrato': resultados['fecha_inicio_contrato'],
            'fecha_corte': resultados['fecha_corte'],
            'fecha_inicio_primas': resultados['fecha_inicio_primas'],
            'fecha_inicio_cesantias': resultados['fecha_inicio_cesantias'],
            'fecha_inicio_vacaciones': resultados['fecha_inicio_vacaciones'],
        }

        # Inyectar valores calculados en el payload para que el serializer pase is_valid()
        full_data = dict(request.data)
        full_data['dias_base_calculo'] = dias
        full_data['base_salarial']     = str(salario_base_liq)
        full_data['valor_total']       = str(valor)
        full_data['desglose_conceptos'] = desglose
        full_data['observaciones']     = observaciones

        serializer = LiquidacionPrestacionSerializer(
            data=full_data,
            context=self.get_serializer_context(),
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(empresa=empresa, estado='PROYECTADO')
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='empleados-con-liquidaciones', permission_classes=[IsTenantMember])
    def empleados_con_liquidaciones(self, request):
        """
        GET /api/v1/empleados/liquidaciones-prestaciones/empleados-con-liquidaciones/
        Retorna lista de empleados del tenant con su conteo de liquidaciones.
        Empleados con liquidaciones aparecen primero (orden DESC por conteo).
        Soporta ?q=texto para filtrar por nombre o documento.
        """
        empresa = self.get_empresa()
        if not empresa:
            return Response({'detail': 'Empresa no configurada.'}, status=status.HTTP_400_BAD_REQUEST)

        from django.db.models import Count, Q
        q = request.query_params.get('q', '').strip()

        qs = (
            Empleado.objects
            .filter(empresa_id=empresa.id)
            .annotate(total_liquidaciones=Count(
                'contratos__liquidaciones',
                filter=Q(contratos__liquidaciones__empresa_id=empresa.id),
                distinct=True,
            ))
            .only('id', 'uuid', 'primer_nombre', 'primer_apellido', 'numero_documento')
            .order_by('-total_liquidaciones', 'primer_apellido', 'primer_nombre')
        )

        if q:
            qs = qs.filter(
                Q(primer_nombre__icontains=q) |
                Q(primer_apellido__icontains=q) |
                Q(numero_documento__icontains=q)
            )

        data = [
            {
                'uuid': str(emp.uuid),
                'nombre_completo': f"{emp.primer_nombre} {emp.primer_apellido}".strip(),
                'numero_documento': emp.numero_documento or '',
                'total_liquidaciones': emp.total_liquidaciones,
            }
            for emp in qs
        ]
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='render-offcanvas/crear', permission_classes=[IsTenantMember])
    def render_offcanvas_crear(self, request):
        """
        GET /api/v1/empleados/liquidaciones-prestaciones/render-offcanvas/crear/
        ?empleado_uuid=<uuid>  — UUID del empleado (AGENTS.md §14)
        """
        empresa = self.get_empresa()
        if not empresa:
            return Response({"error": "Sin tenant asignado"}, status=403)

        context = {
            'empresa_id': empresa.id,
            'tipos_liquidacion': LiquidacionPrestacion.TIPOS
        }

        empleado_uuid = request.query_params.get('empleado_uuid') or request.query_params.get('empleado')
        if empleado_uuid:
            try:
                emp = (
                    Empleado.objects
                    .filter(empresa_id=empresa.id, uuid=empleado_uuid)
                    .only('id', 'uuid', 'primer_nombre', 'primer_apellido', 'numero_documento')
                    .first()
                )
                if emp:
                    context['empleado'] = emp
                    context['contrato'] = (
                        Contrato.objects
                        .filter(empresa_id=empresa.id, empleado_id=emp.id, estado='ACTIVO')
                        .only('id', 'uuid', 'cargo', 'salario_mensual', 'auxilio_transporte',
                              'tipo', 'fecha_inicio')
                        .first()
                    )
            except Exception:
                pass

        if 'empleado' not in context:
            context['empleados_disponibles'] = (
                Empleado.objects
                .filter(empresa_id=empresa.id, contratos__estado='ACTIVO')
                .distinct()
                .only('id', 'uuid', 'primer_nombre', 'primer_apellido', 'numero_documento')
            )

        return Response(context, template_name='tenant/empleados/offcanvas_crear_liquidacion.html')

    @action(detail=False, methods=['get'], url_path='simular', permission_classes=[IsTenantMember])
    def simular(self, request):
        """
        GET /api/v1/empleados/liquidaciones-prestaciones/simular/
        ?contrato_uuid=<uuid>&fecha_corte=YYYY-MM-DD&tipo_liquidacion=TIPO
        Simula la liquidacion de prestaciones sin guardar en la base de datos.
        Acepta contrato_uuid (preferido, AGENTS.md §14) o contrato_id (legacy).
        """
        empresa = self.get_empresa()
        contrato_uuid = request.query_params.get('contrato_uuid')
        contrato_id   = request.query_params.get('contrato_id')
        fecha_corte   = request.query_params.get('fecha_corte')
        tipo_liq      = request.query_params.get('tipo_liquidacion', 'LIQUIDACION_DEFINITIVA')

        # Nuevos parametros opcionales
        dias_salario_pendiente = request.query_params.get('dias_salario_pendiente', 0)
        indemnizacion = request.query_params.get('indemnizacion', 0)

        try:
            dias_salario_pendiente = int(dias_salario_pendiente) if dias_salario_pendiente else 0
        except (ValueError, TypeError):
            dias_salario_pendiente = 0

        try:
            indemnizacion = Decimal(str(indemnizacion)) if indemnizacion else Decimal('0.00')
        except (ValueError, TypeError):
            indemnizacion = Decimal('0.00')

        if not (contrato_uuid or contrato_id) or not fecha_corte:
            return Response({'error': 'contrato_uuid (o contrato_id) y fecha_corte son requeridos'}, status=400)

        try:
            qs = Contrato.objects.filter(empresa_id=empresa.id).only(
                'id', 'uuid', 'tipo', 'estado', 'empresa_id',
                'salario_mensual', 'auxilio_transporte', 'fecha_inicio',
                'prestamos_empresa',
            )
            if contrato_uuid:
                contrato = qs.get(uuid=contrato_uuid)
            else:
                contrato = qs.get(id=int(contrato_id))
        except (Contrato.DoesNotExist, ValueError, TypeError):
            return Response({'error': 'Contrato no encontrado o no pertenece a este tenant'}, status=404)

        try:
            resultados = NominaCalculationService.calcular_liquidacion_prestaciones(
                contrato=contrato,
                tipo_liquidacion=tipo_liq,
                fecha_corte=fecha_corte,
                dias_salario_pendiente=dias_salario_pendiente,
                indemnizacion=indemnizacion
            )

            if tipo_liq == 'PRIMA_SERVICIOS':
                dias = resultados['dias_primas']
                valor = resultados['valor_primas']
            elif tipo_liq == 'CESANTIAS':
                dias = resultados['dias_cesantias']
                valor = resultados['valor_cesantias']
            elif tipo_liq == 'VACACIONES':
                dias = resultados['dias_vacaciones']
                valor = resultados['valor_vacaciones']
            else:
                dias = resultados['dias_cesantias']
                valor = resultados['total_neto']

            salario_base_liq = Decimal(str(contrato.salario_mensual)) + Decimal(str(contrato.auxilio_transporte))

            response_data = {
                'resultados': {
                    'dias_primas': resultados['dias_primas'],
                    'dias_cesantias': resultados['dias_cesantias'],
                    'dias_intereses': resultados['dias_intereses'],
                    'dias_vacaciones': resultados['dias_vacaciones'],
                    'valor_primas': str(resultados['valor_primas']),
                    'valor_cesantias': str(resultados['valor_cesantias']),
                    'valor_intereses': str(resultados['valor_intereses']),
                    'valor_vacaciones': str(resultados['valor_vacaciones']),
                    'total_prestaciones': str(resultados['total_prestaciones']),
                    'dias_salario_pendiente': resultados['dias_salario_pendiente'],
                    'salario_pendiente': str(resultados['salario_pendiente']),
                    'indemnizacion': str(resultados['indemnizacion']),
                    'prestamos_deducidos': str(resultados['prestamos_deducidos']),
                    'total_neto': str(resultados['total_neto']),
                    'fecha_inicio_contrato': resultados['fecha_inicio_contrato'],
                    'fecha_corte': resultados['fecha_corte'],
                    'fecha_inicio_primas': resultados['fecha_inicio_primas'],
                    'fecha_inicio_cesantias': resultados['fecha_inicio_cesantias'],
                    'fecha_inicio_vacaciones': resultados['fecha_inicio_vacaciones'],
                },
                'dias_base_calculo': dias,
                'base_salarial': str(salario_base_liq),
                'valor_total': str(valor),
                'total_neto': str(resultados['total_neto'])
            }
            return Response(response_data, status=200)
        except Exception as e:
            return Response({'error': str(e)}, status=400)

    @action(detail=True, methods=['get'], renderer_classes=[TemplateHTMLRenderer, JSONRenderer], url_path='render-offcanvas/detalle', permission_classes=[IsTenantMember])
    def render_offcanvas_detalle(self, request, **kwargs):
        """
        Endpoint HTMX para cargar offcanvas de detalle de liquidacion.
        GET /api/v1/empleados/liquidaciones-prestaciones/<uuid>/render-offcanvas/detalle/
        """
        empresa = self.get_empresa()
        if not empresa:
            return Response({"error": "Sin tenant asignado"}, status=403)
        try:
            liquidacion = self.get_object()
            if liquidacion.empresa_id != empresa.id:
                return Response({"error": "No autorizado"}, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            return Response({"error": "Liquidacion no encontrada"}, status=status.HTTP_404_NOT_FOUND)
            
        context = {
            'liquidacion': liquidacion,
            'empleado':    liquidacion.empleado,
            'contrato':    liquidacion.contrato,
            'empresa':     empresa,
            'desglose':    liquidacion.desglose_conceptos or {},
        }
        return Response(context, template_name='tenant/empleados/offcanvas_detalle_liquidacion.html')

    @action(detail=True, methods=['get'], renderer_classes=[TemplateHTMLRenderer],
            url_path='pdf', permission_classes=[IsTenantMember])
    def pdf(self, request, **kwargs):
        """
        GET /api/v1/empleados/liquidaciones-prestaciones/<uuid>/pdf/
        Renderiza un documento HTML listo para imprimir / guardar como PDF.
        """
        empresa = self.get_empresa()
        if not empresa:
            return Response({"error": "Sin tenant asignado"}, status=status.HTTP_403_FORBIDDEN)
        try:
            liquidacion = (
                LiquidacionPrestacion.objects
                .filter(empresa_id=empresa.id)
                .select_related('empleado', 'contrato', 'empresa')
                .get(uuid=self.kwargs.get(self.lookup_field))
            )
        except LiquidacionPrestacion.DoesNotExist:
            return Response({"error": "Liquidacion no encontrada"}, status=status.HTTP_404_NOT_FOUND)

        context = {
            'liquidacion': liquidacion,
            'empleado':    liquidacion.empleado,
            'contrato':    liquidacion.contrato,
            'empresa':     empresa,
            'desglose':    liquidacion.desglose_conceptos or {},
        }
        return Response(context, template_name='tenant/empleados/liquidacion_pdf.html')



class PeriodoNominaViewSet(SintelDSVMixin, BaseTenantViewSet):
    """
    ViewSet para PeriodoNomina (mision nomina 2026-08-21).

    WARNING: permisos por accion (FASE 22 de la mision, tabla de ejemplo):
    VISOR consulta; OPERADOR + consultar/crear/preliquidar/enviar-revision;
    ADMIN + aprobar/marcar-pagado/cerrar/anular/bloquear/desbloquear.
    Se reutiliza HasTenantRole (ya existente) fijando required_roles por
    accion en get_permissions() -- no se crea ninguna clase de permiso nueva.
    """
    queryset = PeriodoNomina.objects.none()
    serializer_class = PeriodoNominaSerializer
    permission_classes = [IsTenantMember]

    _ROLES_POR_ACCION = {
        'create': ['ADMIN', 'OPERADOR'],
        'preliquidar': ['ADMIN', 'OPERADOR'],
        'enviar_a_revision': ['ADMIN', 'OPERADOR'],
        'rechazar_revision': ['ADMIN', 'OPERADOR'],
        'aprobar': ['ADMIN'],
        'marcar_pagado': ['ADMIN'],
        'cerrar': ['ADMIN'],
        'anular': ['ADMIN'],
        'bloquear': ['ADMIN'],
        'desbloquear': ['ADMIN'],
    }

    def get_permissions(self):
        self.required_roles = self._ROLES_POR_ACCION.get(self.action, [])
        return [IsTenantMember(), HasTenantRole()]

    @cached_property
    def tenant_empresa(self):
        return resolve_tenant_empresa(self.request, self)

    def get_empresa(self):
        return self.tenant_empresa

    def get_queryset(self):
        empresa = self.get_empresa()
        if not empresa:
            return PeriodoNomina.objects.none()
        estado = self.request.query_params.get('estado')
        return PeriodoNominaSelector.get_list(empresa.id, estado=estado)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        empresa = self.get_empresa()
        context['empresa_id'] = empresa.id if empresa else None
        return context

    def perform_create(self, serializer):
        empresa = self.get_empresa()
        perfil = getattr(self.request.user, 'tenant_profile', None)
        periodo = PeriodoNominaBusinessService.crear_periodo(
            data=serializer.validated_data, empresa=empresa, creado_por=perfil,
        )
        serializer.instance = periodo

    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='render-offcanvas/crear', permission_classes=[IsTenantMember])
    def render_offcanvas_crear(self, request):
        """GET /api/v1/empleados/periodos-nomina/render-offcanvas/crear/"""
        empresa = self.get_empresa()
        if not empresa:
            return Response({"error": "Sin tenant asignado"}, status=status.HTTP_403_FORBIDDEN)
        return Response({'empresa_id': empresa.id}, template_name='tenant/empleados/offcanvas_crear_periodo.html')

    def _get_periodo_or_404(self):
        empresa = self.get_empresa()
        try:
            return PeriodoNominaSelector.get_detail(empresa.id, self.kwargs.get(self.lookup_field))
        except PeriodoNomina.DoesNotExist:
            raise NotFound('Periodo de nomina no encontrado.')

    @action(detail=True, methods=['get'])
    def resumen(self, request, **kwargs):
        """GET /periodos-nomina/<uuid>/resumen/ -- FASE 9: pantalla de revision."""
        periodo = self._get_periodo_or_404()
        data = PeriodoNominaSelector.get_resumen(self.get_empresa().id, periodo.id)
        data['periodo'] = PeriodoNominaSerializer(periodo, context=self.get_serializer_context()).data
        return Response(data)

    @action(detail=True, methods=['post'])
    def preliquidar(self, request, **kwargs):
        periodo = self._get_periodo_or_404()
        resultado = PeriodoNominaBusinessService.preliquidar_periodo(periodo, self.get_empresa().id)
        return Response(resultado, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='enviar-revision')
    def enviar_a_revision(self, request, **kwargs):
        periodo = self._get_periodo_or_404()
        periodo = PeriodoNominaBusinessService.enviar_a_revision(periodo)
        return Response(PeriodoNominaSerializer(periodo, context=self.get_serializer_context()).data)

    @action(detail=True, methods=['post'], url_path='rechazar-revision')
    def rechazar_revision(self, request, **kwargs):
        periodo = self._get_periodo_or_404()
        periodo = PeriodoNominaBusinessService.rechazar_revision(periodo)
        return Response(PeriodoNominaSerializer(periodo, context=self.get_serializer_context()).data)

    @action(detail=True, methods=['post'])
    def aprobar(self, request, **kwargs):
        periodo = self._get_periodo_or_404()
        perfil = getattr(request.user, 'tenant_profile', None)
        periodo = PeriodoNominaBusinessService.aprobar_periodo(periodo, aprobado_por=perfil)
        return Response(PeriodoNominaSerializer(periodo, context=self.get_serializer_context()).data)

    @action(detail=True, methods=['post'], url_path='marcar-pagado')
    def marcar_pagado(self, request, **kwargs):
        periodo = self._get_periodo_or_404()
        perfil = getattr(request.user, 'tenant_profile', None)
        fecha_pago_real = request.data.get('fecha_pago_real')
        periodo = PeriodoNominaBusinessService.marcar_pagado(periodo, pagado_por=perfil, fecha_pago_real=fecha_pago_real)
        return Response(PeriodoNominaSerializer(periodo, context=self.get_serializer_context()).data)

    @action(detail=True, methods=['post'])
    def cerrar(self, request, **kwargs):
        periodo = self._get_periodo_or_404()
        periodo = PeriodoNominaBusinessService.cerrar_periodo(periodo)
        return Response(PeriodoNominaSerializer(periodo, context=self.get_serializer_context()).data)

    @action(detail=True, methods=['post'])
    def anular(self, request, **kwargs):
        periodo = self._get_periodo_or_404()
        periodo = PeriodoNominaBusinessService.anular_periodo(periodo, self.get_empresa().id)
        return Response(PeriodoNominaSerializer(periodo, context=self.get_serializer_context()).data)

    @action(detail=True, methods=['post'])
    def bloquear(self, request, **kwargs):
        periodo = self._get_periodo_or_404()
        periodo = PeriodoNominaBusinessService.bloquear_periodo(periodo)
        return Response(PeriodoNominaSerializer(periodo, context=self.get_serializer_context()).data)

    @action(detail=True, methods=['post'])
    def desbloquear(self, request, **kwargs):
        periodo = self._get_periodo_or_404()
        estado_destino = request.data.get('estado_destino')
        periodo = PeriodoNominaBusinessService.desbloquear_periodo(periodo, estado_destino)
        return Response(PeriodoNominaSerializer(periodo, context=self.get_serializer_context()).data)
