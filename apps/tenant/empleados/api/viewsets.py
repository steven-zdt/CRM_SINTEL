import logging

from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import SAFE_METHODS
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from rest_framework.response import Response

from django.db.utils import ProgrammingError
from django.utils.functional import cached_property
from rest_framework.exceptions import NotFound

from apps.config.api.pagination import StandardResultsSetPagination
from apps.tenant.api.base import BaseTenantViewSet
from apps.tenant.api.mixins import SintelDSVMixin, SintelServiceMixin
from apps.tenant.api.permissions import IsTenantAdmin, IsTenantAdminOrReadOnly, IsTenantMember
from apps.tenant.api.utils import resolve_tenant_empresa
from apps.tenant.empleados.api.serializers import (
    ContratoNestedSerializer,
    DevengoSerializer,
    EmpleadoDetailSerializer,
    EmpleadoListSerializer,
)
from apps.tenant.empleados.models import Contrato, Devengo, Empleado
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
    anular_devengo_service,
    calcular_liquidacion_nomina,
    calcular_nomina_colombia,
    qs_empleado_detail,
    qs_historial_list,
)
from apps.tenant.empresa.models import Empresa

logger = logging.getLogger(__name__)


class EmpleadoViewSet(SintelDSVMixin, EmpleadoServiceMixin, BaseTenantViewSet):
    """
    WARNING: v2.62.4: ViewSet para Empleados migrado a BaseTenantViewSet.
    v3.6.1: UUID lookup field (AGENTS.md §14) - hereda lookup_field="uuid" de BaseTenantViewSet.
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
        v3.6.1: UUID lookup con fallback a PK para retrocompatibilidad (AGENTS.md §14).
        """
        lookup_value = self.kwargs.get(self.lookup_url_kwarg or self.lookup_field)
        empresa = self.get_empresa()

        if not empresa:
            raise NotFound("No se encontró configuración de Empresa para este tenant")

        if lookup_value and len(str(lookup_value)) > 10:
            obj = Empleado.objects.filter(uuid=lookup_value, empresa_id=empresa.id).first()
            if obj:
                return obj

        if str(lookup_value).isdigit():
            obj = Empleado.objects.filter(pk=lookup_value, empresa_id=empresa.id).first()
            if obj:
                return obj

        raise NotFound(f'Empleado {lookup_value} no encontrado o no pertenece a este tenant.')
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['empresa'] = self.get_empresa()
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
        
        # Si no hay paginación, retornar formato compatible
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
            logger.error(f"[EmpleadoViewSet] Error de validación en create: {str(e)}", exc_info=True)
            return Response(
                {"error": "Error de validación", "detail": str(e.detail) if hasattr(e, 'detail') else str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except IntegrityError as e:
            logger.error(f"[EmpleadoViewSet] Error de integridad en create: {str(e)}", exc_info=True)
            # Verificar si es un error de unicidad
            if 'uniq_empleado_per_tenant' in str(e):
                return Response(
                    {"error": "Ya existe un empleado con este tipo y número de documento en esta empresa."},
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
        self.service_crear_empleado(serializer)
    
    def update(self, request, *args, **kwargs):
        """
        WARNING: Paso 4: Sobrescribir update para devolver respuesta JSON con was_updated.
        Permite que los listeners JS distingan entre creación y actualización.
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
        cancelar automáticamente todos los contratos activos.
        """
        return self.service_actualizar_empleado(serializer)
    
    def destroy(self, request, *args, **kwargs):
        """
        WARNING: v2.40: Eliminación definitiva (Hard Delete) solo para empleados RETIRADOS.
        Usa el service layer para eliminar en cascada todas las dependencias.
        """
        from django.core.exceptions import ValidationError
        
        instance = self.get_object()
        
        try:
            # WARNING: v2.40: Usar service layer para eliminación en cascada
            resultado = self.service_eliminar_empleado_retirado(instance)
            
            logger.info(
                f"[EmpleadoViewSet] Empleado {instance.id} eliminado exitosamente. "
                f"Contratos eliminados: {resultado['contratos_eliminados']}, "
                f"Devengos eliminados: {resultado['devengos_eliminados']}"
            )
            
            return Response({
                'detail': 'Empleado eliminado exitosamente',
                'resumen': resultado
            }, status=status.HTTP_200_OK)
            
        except ValidationError as e:
            logger.warning(f"[EmpleadoViewSet] Intento de eliminar empleado {instance.id} con estado inválido: {instance.estado}")
            return Response({
                'detail': str(e),
                'estado': instance.estado,
                'estado_requerido': 'RETIRADO'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"[EmpleadoViewSet] Error al eliminar empleado {instance.id}: {error_msg}", exc_info=True)
            
            # Manejar ProtectedError específicamente (por si acaso Django lo lanza de todas formas)
            from django.db.models.deletion import ProtectedError
            if isinstance(e, ProtectedError):
                return Response({
                    'detail': 'No se puede eliminar el empleado porque tiene registros relacionados protegidos. Intente nuevamente.',
                    'error_type': 'protected_relation'
                }, status=status.HTTP_409_CONFLICT)
            
            return Response({
                'detail': f'Error al eliminar empleado: {error_msg}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        summary = self.service_get_nomina_summary(request)
        if not summary:
            return Response({"error": "sin_empresa"}, status=404)
        return Response(summary)
    
    @action(detail=True, methods=["get"], renderer_classes=[TemplateHTMLRenderer, JSONRenderer], url_path="historial-nominas")
    def historial_nominas(self, request, id=None):
        """
        WARNING: v2.60: Devuelve el HTML del historial de nóminas para un empleado específico (HTMX)
        o los datos JSON para Tabulator (paginación remota).
        
        Endpoint: GET /api/v1/empleados/{id}/historial-nominas/
        
        Query params:
        - format=json: Retorna datos JSON para Tabulator (paginación remota)
        - Sin format: Retorna template HTML del offcanvas
        
        Returns:
            Template HTML renderizado con el offcanvas del historial de nóminas
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
            qs = qs_historial_list(empleado.id, empresa.id, search=search)
            
            # Paginación usando StandardResultsSetPagination
            paginator = StandardResultsSetPagination()
            page = paginator.paginate_queryset(qs, request)
            
            if page is not None:
                serializer = DevengoSerializer(page, many=True)
                return paginator.get_paginated_response(serializer.data)
            
            # Si no hay paginación, retornar todos los resultados
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
        Centraliza la entrega de templates para los módulos features/*.js
        """
        # WARNING: Paso 4: Zero Trust - La empresa se extrae del usuario autenticado
        empresa = getattr(request.user, 'empresa', None)
        if not empresa:
            # Fallback: usar método get_empresa() si existe
            try:
                empresa = self.get_empresa()
            except:
                return Response({"error": "Sin tenant asignado"}, status=status.HTTP_403_FORBIDDEN)
        
        if not empresa:
            return Response({"error": "Sin tenant asignado"}, status=status.HTTP_403_FORBIDDEN)
        
        empresa_id = empresa.id
        
        tipo = request.query_params.get('tipo', 'empleado')
        obj_id = request.query_params.get('id')
        empleado_id = request.query_params.get('empleado')
        context = {'empresa_id': empresa_id}
        
        if tipo == 'empleado':
            context.update({
                'EPS_CHOICES': EPS_CHOICES,
                'AFP_CHOICES': AFP_CHOICES,
                'ARL_CHOICES': ARL_CHOICES,
                'RIESGO_ARL_CHOICES': RIESGO_ARL_CHOICES,
            })
            if obj_id:
                instance = get_object_or_404(Empleado, id=obj_id, empresa_id=empresa_id)
                # v3.5: Usar serializer para resolver cuenta_contable_label (Pull Model)
                serializer = EmpleadoDetailSerializer(instance, context={'empresa': empresa})
                context['empleado'] = serializer.data
                return Response(context, template_name='tenant/empleados/offcanvas_editar_empleado.html')
            return Response(context, template_name='tenant/empleados/offcanvas_crear_empleado.html')
            
        elif tipo == 'contrato':
            if obj_id:
                contrato = get_object_or_404(Contrato, id=obj_id, empresa_id=empresa_id)
                context['contrato'] = contrato
                context['empleado'] = contrato.empleado
                return Response(context, template_name='tenant/empleados/offcanvas_editar_contrato.html')
            if empleado_id:
                context['empleado'] = get_object_or_404(Empleado, id=empleado_id, empresa_id=empresa_id)
            return Response(context, template_name='tenant/empleados/offcanvas_crear_contrato.html')
            
        elif tipo == 'devengo':
            if obj_id:
                devengo = get_object_or_404(Devengo, id=obj_id, empresa_id=empresa_id)
                context['devengo'] = devengo
                context['empleado'] = devengo.empleado
                context['contrato'] = devengo.contrato
            if empleado_id:
                empleado = get_object_or_404(Empleado, id=empleado_id, empresa_id=empresa_id)
                context['empleado'] = empleado
                # Obtener contrato ACTIVO del empleado
                contrato_activo = Contrato.objects.filter(
                    empleado=empleado,
                    estado='ACTIVO',
                    empresa_id=empresa_id
                ).first()
                if contrato_activo:
                    context['contrato'] = contrato_activo
            return Response(context, template_name='tenant/empleados/offcanvas_crear_devengo.html')
            
        return Response({"error": "Tipo no válido"}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["get"], url_path="contrato-disponible")
    def contrato_disponible(self, request, id=None):
        """
        WARNING: v2.40: Valida si el empleado tiene contrato activo disponible para nómina.
        Verifica que no exista ya un devengo para el periodo_mes actual.
        """
        from datetime import datetime

        empresa = self.get_empresa()
        if not empresa:
            return Response({"error": "sin_empresa"}, status=status.HTTP_404_NOT_FOUND)

        empleado = self.get_object()
        
        # 1. Buscar contrato activo del empleado (WARNING: v2.40: Máquina de Estados - usar estado='ACTIVO')
        contrato_activo = Contrato.objects.filter(
            empleado=empleado,
            estado='ACTIVO'
        ).first()
        
        # Fallback: también buscar por campo activo legacy para compatibilidad
        if not contrato_activo:
            contrato_activo = Contrato.objects.filter(
                empleado=empleado,
                activo=True
            ).first()
        
        if not contrato_activo:
            return Response({
                "disponible": False,
                "error": "El empleado no tiene un contrato activo"
            }, status=status.HTTP_404_NOT_FOUND)
        
        # WARNING: v2.40: Máquina de Estados - Validar que el contrato esté ACTIVO
        if contrato_activo.estado != 'ACTIVO':
            return Response({
                "disponible": False,
                "error": f"El contrato no está activo (estado: {contrato_activo.estado})"
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
                "error": f"Formato de periodo inválido: {periodo_mes}. Debe ser YYYY-MM"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 3. Verificar que NO exista ya un devengo para ese empleado en ese periodo
        devengo_existente = Devengo.objects.filter(
            empleado=empleado,
            periodo_mes=periodo_mes,
            anulado=False
        ).exists()
        
        if devengo_existente:
            return Response({
                "disponible": False,
                "error": f"Ya existe una nómina registrada para el periodo {periodo_mes}"
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
    v3.6.1: UUID lookup field (AGENTS.md §14) - hereda lookup_field="uuid" de BaseTenantViewSet.
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
        v3.6.1: UUID lookup con fallback a PK para retrocompatibilidad (AGENTS.md §14).
        """
        lookup_value = self.kwargs.get(self.lookup_url_kwarg or self.lookup_field)
        empresa = self.get_empresa()

        if not empresa:
            raise NotFound("No se encontró configuración de Empresa para este tenant")

        if lookup_value and len(str(lookup_value)) > 10:
            obj = Contrato.objects.filter(uuid=lookup_value, empresa_id=empresa.id).first()
            if obj:
                return obj

        if str(lookup_value).isdigit():
            obj = Contrato.objects.filter(pk=lookup_value, empresa_id=empresa.id).first()
            if obj:
                return obj

        raise NotFound(f'Contrato {lookup_value} no encontrado o no pertenece a este tenant.')

    def create(self, request, *args, **kwargs):
        """
        WARNING: v2.95: Sobrescribir create para manejar errores y validaciones.
        """
        try:
            # WARNING: DEBUG: Log de datos recibidos
            logger.info(f"[ContratoViewSet] Datos recibidos en create: {request.data}")
            logger.info(f"[ContratoViewSet] Tipo de datos: {type(request.data)}")
            
            # Validar que el campo empleado esté presente
            if 'empleado' not in request.data:
                logger.error("[ContratoViewSet] Campo 'empleado' no encontrado en request.data")
                return Response(
                    {"error": "Error de validación", "detail": {"empleado": ["Este campo es requerido."]}},
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
            logger.error(f"[ContratoViewSet] Error de validación en create: {str(e)}", exc_info=True)
            # WARNING: v2.60: Error Boundary Pattern - Retornar formato JSON estructurado para UIManager
            error_detail = e.detail if hasattr(e, 'detail') else str(e)
            if isinstance(error_detail, dict):
                return Response(error_detail, status=status.HTTP_400_BAD_REQUEST)
            return Response(
                {"error": "Error de validación en el contrato", "detail": str(error_detail)},
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
                {"error": "Ocurrió un error inesperado al procesar el contrato.", "detail": str(e)},
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
        
        # Si no hay paginación, retornar formato compatible
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
        from rest_framework.exceptions import ValidationError
        
        # WARNING: DEBUG: Log de validated_data
        logger.info(f"[ContratoViewSet] validated_data en perform_create: {serializer.validated_data}")
        
        empleado = serializer.validated_data.get('empleado')
        if not empleado:
            logger.error("[ContratoViewSet] Campo 'empleado' no encontrado en validated_data")
            raise ValidationError({'empleado': ['Este campo es requerido.']})
        
        # Validar que el empleado sea una instancia de Empleado
        if not isinstance(empleado, Empleado):
            logger.error(f"[ContratoViewSet] Campo 'empleado' no es una instancia de Empleado: {type(empleado)}")
            raise ValidationError({'empleado': ['El empleado debe ser un ID válido.']})
        
        # Extraer datos del serializer (excluyendo empleado que ya está validado)
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
        Permite que los listeners JS distingan entre creación y actualización.
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
            logger.error(f"[ContratoViewSet] Error de validación en update: {str(e)}", exc_info=True)
            # WARNING: v2.60: Error Boundary Pattern - Retornar formato JSON estructurado para UIManager
            error_detail = e.detail if hasattr(e, 'detail') else str(e)
            if isinstance(error_detail, dict):
                return Response(error_detail, status=status.HTTP_400_BAD_REQUEST)
            return Response(
                {"error": "Error de validación en el contrato", "detail": str(error_detail)},
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
                {"error": "Ocurrió un error inesperado al procesar el contrato.", "detail": str(e)},
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
        WARNING: Paso 4: Método para actualizar contrato existente.
        Usa service layer para garantizar integridad.
        """
        from rest_framework.exceptions import ValidationError
        
        instance = serializer.instance
        empleado = serializer.validated_data.get('empleado', instance.empleado)
        
        # Extraer datos del serializer (excluyendo empleado que ya está validado)
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
        Endpoint HTMX RESTful para cargar offcanvas de creación de contratos.
        
        WARNING: v2.61: Feature-Sliced Architecture - Template dedicado para creación
        - GET /api/v1/empleados/contratos/render-offcanvas/crear/?empleado={id} → Modo creación
        
        Query params:
        - empleado: ID del empleado (requerido para crear contrato)
        
        Returns:
            Template HTML: tenant/core/partials/empleados/contrato_offcanvas_form.html
        """
        empresa = self.get_empresa()
        
        empleado_id = request.query_params.get('empleado')
        if not empleado_id:
            return Response(
                {"error": "Se requiere el parámetro 'empleado' para crear un contrato."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            empleado = get_object_or_404(Empleado, id=empleado_id, empresa_id=empresa.id)
        except Exception as e:
            logger.error(f"[ContratoViewSet] Error al obtener empleado: {str(e)}", exc_info=True)
            return Response(
                {"error": "Empleado no encontrado o no pertenece a este tenant."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        context = {
            'empleado': empleado,
            'contrato': None,
            'empresa': empresa
        }
        return Response(context, template_name='tenant/empleados/offcanvas_crear_contrato.html')
    
    @action(detail=True, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='render-offcanvas/editar')
    def render_offcanvas_editar(self, request, **kwargs):
        """
        Endpoint HTMX RESTful para cargar offcanvas de edición de contratos.
        
        WARNING: v2.61: Feature-Sliced Architecture - Template dedicado para edición
        - GET /api/v1/empleados/contratos/{id}/render-offcanvas/editar/ → Modo edición
        
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
            logger.error(f"[ContratoViewSet] Contrato no encontrado: {kwargs.get('id')}")
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
    def cancelar(self, request, id=None):
        """
        WARNING: v2.40: Máquina de Estados - Cambia el estado de un contrato a INACTIVO.
        WARNING: v2.60: Error Boundary Pattern - Manejo de errores estandarizado.
        """
        try:
            contrato = self.get_object()
            if contrato.estado == 'INACTIVO':
                return Response(
                    {"error": "El contrato ya está inactivo.", "detail": "No se puede cancelar un contrato que ya está inactivo."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            contrato.estado = 'INACTIVO'
            contrato.activo = False  # Sincronizar campo legacy
            contrato.save(update_fields=['estado', 'activo'])
            
            serializer = self.get_serializer(contrato)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"[ContratoViewSet] Error al cancelar contrato: {str(e)}", exc_info=True)
            return Response(
                {"error": "Ocurrió un error inesperado al cancelar el contrato.", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class DevengoViewSet(SintelDSVMixin, DevengoServiceMixin, BaseTenantViewSet):
    """
    WARNING: v2.62.4: ViewSet para Nómina migrado a BaseTenantViewSet.
    v3.6.1: UUID lookup field (AGENTS.md §14) - hereda lookup_field="uuid" de BaseTenantViewSet.
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
        WARNING: v2.60: QuerySet optimizado usando service layer.
        """
        if self.action == 'list':
            queryset = self.get_qs_list()
            
            # WARNING: v2.95: Filtros de fecha para historial de nómina (adicionales al service layer)
            fecha_inicio = self.request.query_params.get('fecha_inicio')
            fecha_fin = self.request.query_params.get('fecha_fin')
            
            if fecha_inicio:
                try:
                    from datetime import datetime
                    fecha_inicio_obj = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
                    queryset = queryset.filter(fecha_pago__gte=fecha_inicio_obj)
                except (ValueError, TypeError):
                    logger.warning(f"[DevengoViewSet] Formato de fecha_inicio inválido: {fecha_inicio}")
            
            if fecha_fin:
                try:
                    from datetime import datetime
                    fecha_fin_obj = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
                    queryset = queryset.filter(fecha_pago__lte=fecha_fin_obj)
                except (ValueError, TypeError):
                    logger.warning(f"[DevengoViewSet] Formato de fecha_fin inválido: {fecha_fin}")
            
            return queryset

        return self.get_qs_detail()

    def get_object(self):
        """
        v3.6.1: UUID lookup con fallback a PK para retrocompatibilidad (AGENTS.md §14).
        """
        lookup_value = self.kwargs.get(self.lookup_url_kwarg or self.lookup_field)
        empresa = self.get_empresa()

        if not empresa:
            raise NotFound("No se encontró configuración de Empresa para este tenant")

        if lookup_value and len(str(lookup_value)) > 10:
            obj = Devengo.objects.filter(uuid=lookup_value, empresa_id=empresa.id).first()
            if obj:
                return obj

        if str(lookup_value).isdigit():
            obj = Devengo.objects.filter(pk=lookup_value, empresa_id=empresa.id).first()
            if obj:
                return obj

        raise NotFound(f'Nomina {lookup_value} no encontrada o no pertenece a este tenant.')
    
    def list(self, request, *args, **kwargs):
        """
        WARNING: v2.60: Listado paginado con formato DRF {count, results} para Tabulator Factory.
        """
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        # Si no hay paginación, retornar formato compatible
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'count': len(serializer.data),
            'next': None,
            'previous': None,
            'results': serializer.data
        })

    @action(detail=False, methods=["get"], url_path="ultima-nomina")
    def ultima_nomina(self, request):
        """
        WARNING: v2.40: Obtiene la última nómina pagada para un empleado o contrato.
        Query params: empleado_id (requerido) o contrato_id (opcional).
        Retorna la última nómina no anulada para sugerir periodo y fecha de pago siguiente.
        """
        from datetime import datetime, timedelta

        from dateutil.relativedelta import relativedelta
        
        empresa = Empresa.objects.only('id').first()
        if not empresa:
            return Response({"error": "sin_empresa"}, status=status.HTTP_404_NOT_FOUND)
        
        empresa_id = empresa.id
        
        empleado_id = request.query_params.get('empleado_id')
        contrato_id = request.query_params.get('contrato_id')
        
        if not empleado_id:
            return Response({
                "error": "empleado_id es requerido"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # WARNING: v2.60: Buscar última nómina no anulada del empleado usando empresa_id
        ultima_nomina = Devengo.objects.filter(
            empleado_id=empleado_id,
            anulado=False,
            empresa_id=empresa_id
        ).order_by('-fecha_pago', '-periodo_mes').first()
        
        if not ultima_nomina:
            # Primer pago: usar mes actual y fecha actual
            ahora = datetime.now()
            periodo_sugerido = ahora.strftime('%Y-%m')
            fecha_sugerida = ahora.strftime('%Y-%m-%d')
            
            return Response({
                "es_primer_pago": True,
                "periodo_sugerido": periodo_sugerido,
                "fecha_pago_sugerida": fecha_sugerida,
                "ultima_nomina": None
            }, status=status.HTTP_200_OK)
        
        # Calcular periodo siguiente (mes siguiente al último pagado)
        try:
            # Parsear periodo_mes (YYYY-MM)
            ultimo_periodo = datetime.strptime(ultima_nomina.periodo_mes, '%Y-%m')
            # Mes siguiente
            siguiente_periodo = ultimo_periodo + relativedelta(months=1)
            periodo_sugerido = siguiente_periodo.strftime('%Y-%m')
        except (ValueError, AttributeError):
            # Si hay error, usar mes actual
            ahora = datetime.now()
            periodo_sugerido = ahora.strftime('%Y-%m')
        
        # Calcular fecha de pago sugerida
        # Si la última nómina fue quincenal (dias_laborados < 30), sugerir 15 días después
        # Si fue mensual (dias_laborados = 30), sugerir mes siguiente
        ultima_fecha_pago = ultima_nomina.fecha_pago
        if ultima_nomina.dias_laborados and ultima_nomina.dias_laborados < 30:
            # Quincenal: 15 días después
            fecha_sugerida = (ultima_fecha_pago + timedelta(days=15)).strftime('%Y-%m-%d')
        else:
            # Mensual: mes siguiente, misma fecha del mes
            try:
                siguiente_fecha = ultima_fecha_pago + relativedelta(months=1)
                fecha_sugerida = siguiente_fecha.strftime('%Y-%m-%d')
            except:
                # Fallback: 30 días después
                fecha_sugerida = (ultima_fecha_pago + timedelta(days=30)).strftime('%Y-%m-%d')
        
        return Response({
            "es_primer_pago": False,
            "periodo_sugerido": periodo_sugerido,
            "fecha_pago_sugerida": fecha_sugerida,
            "ultima_nomina": {
                "id": ultima_nomina.id,
                "periodo_mes": ultima_nomina.periodo_mes,
                "fecha_pago": ultima_nomina.fecha_pago.strftime('%Y-%m-%d') if ultima_nomina.fecha_pago else None,
                "dias_laborados": ultima_nomina.dias_laborados
            }
        }, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        """
        WARNING: v2.60: Sobrescribir create con validación estricta de duplicados (Zero Trust).
        Prohíbe el Upsert automático para proteger la evidencia legal de la nómina.
        Retorna errores en formato JSON para UIManager.handleError.
        
        WARNING: Validación Preventiva: Verifica duplicados ANTES de validar serializer.
        Si existe una nómina para el mismo empleado y periodo, retorna error 409 Conflict.
        """
        try:
            # WARNING: DEBUG: Log de datos recibidos
            logger.info(f"[DevengoViewSet] Datos recibidos en create: {request.data}")
            logger.info(f"[DevengoViewSet] Tipo de datos: {type(request.data)}")

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
                                    "error": "Ya existe una nómina para este empleado, periodo y fecha de pago. Debe anular la nómina existente antes de crear una nueva.",
                                    "detail": "No se puede crear una nómina duplicada para el mismo empleado, periodo y fecha de pago. Puede registrar múltiples nóminas en el mismo mes usando diferentes fechas de pago.",
                                    "code": "duplicate_nomina"
                                },
                                status=status.HTTP_409_CONFLICT
                            )
                
                # WARNING: v2.60: Retornar errores de validación en formato estructurado para UIManager
                logger.error(f"[DevengoViewSet] Error de validación en create: {serializer.errors}")
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                validacion = self.service_validar_limite_dias(request.data)
                if validacion:
                    logger.info(
                        f"[DevengoViewSet] Validación preventiva de días: Total={validacion['total_dias']}, "
                        f"Nuevos={validacion['nuevos_dias']}, Final={validacion['total_final']}"
                    )
            except serializers.ValidationError as e:
                error_detail = str(e.detail) if hasattr(e, 'detail') else str(e)
                return Response(
                    {
                        "error": "La suma de días laborados excede los 31 días permitidos del mes.",
                        "detail": error_detail,
                        "code": "dias_excedidos"
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            except Exception as e:
                logger.warning(f"[DevengoViewSet] Error al validar días laborados: {str(e)}")
            
            # Ejecutar perform_create que calcula valores y guarda (creación nueva)
            self.perform_create(serializer)
            
            # WARNING: Paso 4: Retornar respuesta con was_updated para listeners JS
            headers = self.get_success_headers(serializer.data)
            response_data = {
                **serializer.data,
                "was_updated": False,
                "message": "Nómina creada correctamente"
            }
            return Response(
                response_data,
                status=status.HTTP_201_CREATED,
                headers=headers
            )
            
        except serializers.ValidationError as e:
            logger.error(f"[DevengoViewSet] Error de validación en create: {str(e)}", exc_info=True)
            # WARNING: v2.60: Error Boundary Pattern - Retornar formato JSON estructurado para UIManager
            error_detail = e.detail if hasattr(e, 'detail') else str(e)
            if isinstance(error_detail, dict):
                return Response(error_detail, status=status.HTTP_400_BAD_REQUEST)
            return Response(
                {"error": "Error de validación en la nómina", "detail": str(error_detail)},
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
            # WARNING: v2.60: Error Boundary Pattern - Capturar error de unicidad específico
            error_str = str(e).lower()
            if 'uniq_nomina_per_empleado_periodo' in error_str or 'unique constraint' in error_str:
                return Response(
                    {
                        "error": "Ya existe una nómina registrada para este empleado en el periodo seleccionado.",
                        "detail": "No se puede crear una nómina duplicada. Si desea modificarla, debe anular la nómina existente primero.",
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
                {"error": "Ocurrió un error inesperado al procesar la nómina.", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def update(self, request, *args, **kwargs):
        """
        WARNING: v2.60: Permite actualización solo a través de lógica de Upsert en create().
        Método directo bloqueado para mantener inmutabilidad explícita.
        """
        return Response(
            {"detail": "Para actualizar una nómina, use el endpoint de creación. El sistema detectará automáticamente si existe una nómina para el mismo periodo y la actualizará."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )
    
    def partial_update(self, request, *args, **kwargs):
        """
        WARNING: v2.60: Permite actualización solo a través de lógica de Upsert en create().
        Método directo bloqueado para mantener inmutabilidad explícita.
        """
        return Response(
            {"detail": "Para actualizar una nómina, use el endpoint de creación. El sistema detectará automáticamente si existe una nómina para el mismo periodo y la actualizará."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )
    
    def destroy(self, request, *args, **kwargs):
        """
        WARNING: v2.60: Eliminación de nómina (Hard Delete).
        Valida Zero Trust y registra en log de auditoría.
        """
        instance = self.get_object()
        
        try:
            devengo_id = self.service_eliminar_devengo(instance, request)
            
            return Response(
                {"detail": "Nómina eliminada correctamente", "id": devengo_id},
                status=status.HTTP_200_OK
            )
        except serializers.ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            logger.error(f"[DevengoViewSet] Error al eliminar nómina: {str(e)}", exc_info=True)
            return Response(
                {"error": "Ocurrió un error inesperado al eliminar la nómina.", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def perform_update(self, serializer):
        """
        WARNING: v2.60: Método para actualizar nómina existente (usado en lógica de Upsert).
        Recalcula todos los valores usando la Capa de Servicio antes de guardar (Zero Trust).
        """
        serializer.instance = self.service_procesar_devengo(serializer, instance=serializer.instance)

    def perform_create(self, serializer):
        """
        WARNING: v2.40: Usa el service layer para calcular valores proporcionales antes de guardar.
        """
        serializer.instance = self.service_procesar_devengo(serializer)

    @action(detail=True, methods=["post"], url_path="anular")
    def anular(self, request, id=None):
        instance = self.get_object()
        devengo = self.service_anular_devengo(instance)
        return Response({"status": "Anulado correctamente", "id": devengo.id})
    
    @action(detail=False, methods=["post"], renderer_classes=[TemplateHTMLRenderer, JSONRenderer], url_path="preview-calculo", permission_classes=[IsTenantMember])
    def preview_calculo(self, request):
        """
        WARNING: v2.60: Endpoint para previsualizar cálculo de nómina en tiempo real (HTMX Partial).
        Devuelve un partial HTML con los valores calculados actualizados.
        """
        from decimal import Decimal, InvalidOperation
        
        # Template para errores (opcional, si queremos mostrar error dentro del wrapper)
        ERROR_TEMPLATE = 'tenant/empleados/devengo_error_partial.html'
        
        # WARNING: v2.60: SSoT - Obtener empresa desde el contexto del tenant (BaseTenantViewSet)
        empresa = self.get_empresa()
        
        if not empresa:
            return Response(
                {"error": "No se encontró configuración de Empresa para este tenant."}, 
                status=status.HTTP_403_FORBIDDEN,
                template_name=ERROR_TEMPLATE
            )
        
        empresa_id = empresa.id
        
        try:
            # WARNING: v2.60: Extraer datos del request.POST (HTMX envía datos como form-data)
            # Soporta tanto request.data (DRF) como request.POST (HTMX form-data)
            contrato_id = request.data.get('contrato') or request.POST.get('contrato')
            dias_laborados = request.data.get('dias_laborados') or request.POST.get('dias_laborados')
            periodo_mes = request.data.get('periodo_mes') or request.POST.get('periodo_mes')
            fecha_pago = request.data.get('fecha_pago') or request.POST.get('fecha_pago')
            horas_trabajadas = request.data.get('horas_trabajadas') or request.POST.get('horas_trabajadas')
            
            # WARNING: v2.60: Validar datos requeridos
            if not contrato_id:
                return Response({
                    "error": "El campo 'contrato' es obligatorio. Asegúrese de que el empleado tenga un contrato activo."
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if not dias_laborados:
                return Response({
                    "error": "El campo 'dias_laborados' es obligatorio."
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # WARNING: v2.60: Zero Trust - Obtener contrato ACTIVO validando empresa_id
            try:
                contrato = Contrato.objects.get(id=contrato_id, estado='ACTIVO', empresa_id=empresa_id)
            except Contrato.DoesNotExist:
                return Response({
                    "error": "Contrato no encontrado o no está activo. Verifique que el contrato pertenezca a este tenant y esté en estado ACTIVO."
                }, status=status.HTTP_404_NOT_FOUND)
            
            # WARNING: v2.60: Validar días laborados (permite decimales 0.5-30)
            try:
                dias_laborados = Decimal(str(dias_laborados))
            except (ValueError, InvalidOperation):
                return Response({
                    "error": "Los días laborados deben ser un número válido"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if dias_laborados < Decimal('0.5') or dias_laborados > Decimal('30'):
                return Response({
                    "error": "Los días laborados deben estar entre 0.5 y 30"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # WARNING: v2.60: Validar horas trabajadas si se proporciona
            horas_trabajadas_decimal = None
            if horas_trabajadas is not None:
                try:
                    horas_trabajadas_decimal = Decimal(str(horas_trabajadas))
                    if horas_trabajadas_decimal < 0:
                        return Response({
                            "error": "Las horas trabajadas no pueden ser negativas"
                        }, status=status.HTTP_400_BAD_REQUEST)
                except (ValueError, InvalidOperation):
                    return Response({
                        "error": "Las horas trabajadas deben ser un número válido"
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            # Obtener valores opcionales (con valores por defecto 0 para evitar None)
            # WARNING: v2.60: Normalización de decimales usando Decimal para precisión
            try:
                otros_devengos = Decimal(str(request.data.get('otros_devengos', 0) or request.POST.get('otros_devengos', 0) or 0))
                prestamos = Decimal(str(request.data.get('prestamos', 0) or request.POST.get('prestamos', 0) or 0))
                descuentos_operativos = Decimal(str(request.data.get('descuentos_operativos', 0) or request.POST.get('descuentos_operativos', 0) or 0))
            except (ValueError, InvalidOperation, TypeError) as e:
                return Response({
                    "error": f"Error en formato de datos numéricos: {str(e)}"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # WARNING: v2.60: Validar que el préstamo a descontar no sea mayor al disponible en el contrato
            if prestamos > 0:
                prestamo_disponible = Decimal(str(contrato.prestamos_empresa or 0))
                if prestamos > prestamo_disponible:
                    return Response({
                        "error": f"El monto a descontar (${prestamos:,.2f}) no puede ser mayor al préstamo disponible en el contrato (${prestamo_disponible:,.2f})"
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            # WARNING: v2.60: Calcular usando NominaCalculationService.calcular_liquidacion (SSoT - Normativa Colombiana)
            # WARNING: Zero Trust: Pasar empresa_id para validación
            from apps.tenant.empleados.services.business_service import NominaCalculationService
            calculo = NominaCalculationService.calcular_liquidacion(
                contrato=contrato,
                dias_laborados=dias_laborados,
                horas_trabajadas=horas_trabajadas_decimal,
                otros_devengos=otros_devengos,
                prestamos=prestamos,
                descuentos_operativos=descuentos_operativos,
                empresa_id=empresa_id
            )
            
            # WARNING: Error Boundary Pattern: Validar que el neto no sea negativo
            neto_pagar = Decimal(calculo['neto_pagar'])
            if neto_pagar < 0:
                return Response({
                    "error": f"El neto a pagar no puede ser negativo (${neto_pagar:,.2f}). Revise los descuentos y préstamos.",
                    "calculo": calculo
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Retornar partial HTML con los valores calculados
            context = {
                "calculo": calculo,
                "contrato": contrato
            }
            
            return Response(context, template_name='tenant/empleados/devengo_calculo_partial.html')
            
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST, template_name=ERROR_TEMPLATE)
        except (InvalidOperation, TypeError) as e:
            return Response({"error": f"Error en formato de datos numéricos: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST, template_name=ERROR_TEMPLATE)
        except Exception as e:
            logger.error(f"[DevengoViewSet] Error en preview_calculo: {str(e)}", exc_info=True)
            return Response({
                "error": "Ocurrió un error inesperado al calcular la nómina.",
                "detail": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR, template_name=ERROR_TEMPLATE)
    
    @action(detail=False, methods=["post"], url_path="previsualizar")
    def previsualizar(self, request):
        """
        WARNING: v2.60: Endpoint para previsualizar cálculo de nómina sin guardar.
        Usa calcular_liquidacion_nomina() como única fuente de verdad (SSoT).
        Cumple con normativa laboral colombiana (Ley 2101 - 46 horas semanales).
        
        Recibe:
        - contrato_id: ID del contrato (requerido)
        - dias_laborados: Días trabajados (0.5-30, requerido)
        - horas_trabajadas: Horas trabajadas (opcional, para cálculo por horas)
        - otros_devengos: Otros devengos en COP (opcional, default: 0)
        - prestamos: Préstamos a descontar en COP (opcional, default: 0)
        - descuentos_operativos: Descuentos operativos en COP (opcional, default: 0)
        
        Retorna:
        - salario_base: Salario base proporcional calculado
        - auxilio_transporte: Auxilio de transporte proporcional
        - ibc: Ingreso Base de Cotización (para referencia)
        - salud_empleado: Deducción de salud (4% sobre IBC)
        - pension_empleado: Deducción de pensión (4% sobre IBC)
        - neto_pagar: Neto a pagar calculado
        """
        from decimal import Decimal, InvalidOperation

        from apps.tenant.empleados.models import Contrato
        
        empresa = Empresa.objects.only('id').first()
        if not empresa:
            return Response({"error": "sin_empresa"}, status=status.HTTP_404_NOT_FOUND)
        
        empresa_id = empresa.id
        
        try:
            # Validar y obtener datos requeridos
            contrato_id = request.data.get('contrato')
            dias_laborados = request.data.get('dias_laborados', 30)
            horas_trabajadas = request.data.get('horas_trabajadas', None)  # WARNING: v2.60: Soporte para cálculo por horas
            
            if not contrato_id:
                return Response({
                    "error": "El campo 'contrato' es obligatorio"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # WARNING: v2.60: Máquina de Estados - Obtener contrato ACTIVO con Zero Trust
            try:
                contrato = Contrato.objects.get(id=contrato_id, estado='ACTIVO', empresa_id=empresa_id)
            except Contrato.DoesNotExist:
                # Fallback: buscar por campo activo legacy
                try:
                    contrato = Contrato.objects.get(id=contrato_id, activo=True, empresa_id=empresa_id)
                    # Si existe pero no está ACTIVO, rechazar
                    if contrato.estado != 'ACTIVO':
                        return Response({
                            "error": f"Contrato no está activo (estado: {contrato.estado})"
                        }, status=status.HTTP_400_BAD_REQUEST)
                except Contrato.DoesNotExist:
                    return Response({
                        "error": "Contrato no encontrado o no está activo"
                    }, status=status.HTTP_404_NOT_FOUND)
            
            # WARNING: v2.60: Validar días laborados (permite decimales 0.5-30)
            try:
                dias_laborados = Decimal(str(dias_laborados))
            except (ValueError, InvalidOperation):
                return Response({
                    "error": "Los días laborados deben ser un número válido"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if dias_laborados < Decimal('0.5') or dias_laborados > Decimal('30'):
                return Response({
                    "error": "Los días laborados deben estar entre 0.5 y 30"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # WARNING: v2.60: Validar horas trabajadas si se proporciona
            horas_trabajadas_decimal = None
            if horas_trabajadas is not None:
                try:
                    horas_trabajadas_decimal = Decimal(str(horas_trabajadas))
                    if horas_trabajadas_decimal < 0:
                        return Response({
                            "error": "Las horas trabajadas no pueden ser negativas"
                        }, status=status.HTTP_400_BAD_REQUEST)
                except (ValueError, InvalidOperation):
                    return Response({
                        "error": "Las horas trabajadas deben ser un número válido"
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            # Obtener valores opcionales (con valores por defecto 0 para evitar None)
            otros_devengos = Decimal(str(request.data.get('otros_devengos', 0) or 0))
            prestamos = Decimal(str(request.data.get('prestamos', 0) or 0))
            descuentos_operativos = Decimal(str(request.data.get('descuentos_operativos', 0) or 0))
            
            # WARNING: v2.60: Validar que el préstamo a descontar no sea mayor al disponible en el contrato
            if prestamos > 0:
                prestamo_disponible = Decimal(str(contrato.prestamos_empresa or 0))
                if prestamos > prestamo_disponible:
                    return Response({
                        "error": f"El monto a descontar (${prestamos:,.2f}) no puede ser mayor al préstamo disponible en el contrato (${prestamo_disponible:,.2f})"
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            # WARNING: v2.60: Calcular usando NominaCalculationService.calcular_liquidacion (SSoT - Normativa Colombiana)
            from apps.tenant.empleados.services.business_service import NominaCalculationService
            calculo = NominaCalculationService.calcular_liquidacion(
                contrato=contrato,
                dias_laborados=dias_laborados,
                horas_trabajadas=horas_trabajadas_decimal,
                otros_devengos=otros_devengos,
                prestamos=prestamos,
                descuentos_operativos=descuentos_operativos
            )
            
            # Retornar valores calculados
            return Response({
                "ok": True,
                "calculo": calculo
            }, status=status.HTTP_200_OK)
            
        except ValueError as e:
            return Response({
                "error": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except (InvalidOperation, TypeError) as e:
            return Response({
                "error": f"Error en formato de datos numéricos: {str(e)}"
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"[DevengoViewSet] Error en previsualizar: {str(e)}", exc_info=True)
            return Response({
                "error": "Ocurrió un error inesperado al calcular la previsualización.",
                "detail": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)