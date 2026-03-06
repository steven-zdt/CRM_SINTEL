import logging
from rest_framework import viewsets, filters, status, serializers, mixins
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import SAFE_METHODS
from rest_framework.authentication import SessionAuthentication
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from django_filters.rest_framework import DjangoFilterBackend
from django.db import IntegrityError
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from apps.tenant.empresa.models import Empresa

from apps.tenant.api.permissions import IsTenantMember, IsTenantAdminOrReadOnly
from apps.tenant.empresa.permissions import IsTenantAdmin
from apps.config.api.pagination import StandardResultsSetPagination
from apps.tenant.empleados.models import Empleado, Contrato, Devengo
from apps.tenant.empleados.services import (
    qs_empleado_list, qs_empleado_detail,
    qs_contrato_list, qs_contrato_detail,
    qs_devengo_list, qs_devengo_detail,
    qs_historial_list,
    get_nomina_summary, anular_devengo_service,
    eliminar_empleado_retirado, cancelar_contratos_activos_al_retirar,
    gestionar_contrato_service, registrar_devengo_nomina_service,
    validar_limite_dias_mes,
    calcular_nomina_colombia, calcular_liquidacion_nomina
)
from apps.tenant.empleados.api.serializers import (
    EmpleadoListSerializer, EmpleadoDetailSerializer,
    ContratoNestedSerializer, DevengoSerializer
)

logger = logging.getLogger(__name__)

class EnforcedModeMixin:
    """Restricción de escritura v2.40 solo para ADMIN."""
    def check_mutation_permission(self, request):
        if request.method in SAFE_METHODS:
            return True, None
        if IsTenantAdmin().has_permission(request, self):
            return True, None
        return False, f"Solo usuarios ADMIN pueden realizar {request.method}."

    def dispatch(self, request, *args, **kwargs):
        if request.method not in SAFE_METHODS:
            ok, reason = self.check_mutation_permission(request)
            if not ok:
                return Response({"detail": reason}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
        return super().dispatch(request, *args, **kwargs)

class EmpleadoViewSet(EnforcedModeMixin, viewsets.ModelViewSet):
    """
    ⚠️ v2.40: ViewSet para Empleados con Tabulator Factory.
    Usa StandardResultsSetPagination para paginación remota.
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["numero_documento", "primer_nombre", "primer_apellido"]

    def get_queryset(self):
        """
        ⚠️ v2.60: QuerySet optimizado usando service layer.
        Soporta ?search= para filtrado en Tabulator.
        ⚠️ CORRECCIÓN: Filtra siempre por request.user.empresa para evitar 404.
        ⚠️ IMPORTANTE: get_queryset() debe retornar un queryset, no un objeto individual.
        DRF usa get_object() para obtener el objeto específico en retrieve.
        """
        # ⚠️ CORRECCIÓN: Obtener empresa del usuario autenticado
        user = getattr(self.request, 'user', None)
        if not user or not user.is_authenticated:
            return Empleado.objects.none()
        
        # Intentar obtener empresa del usuario
        empresa = None
        if hasattr(user, 'empresa'):
            empresa = user.empresa
        elif hasattr(user, 'empresa_id'):
            try:
                empresa = Empresa.objects.only('id').get(id=user.empresa_id)
            except Empresa.DoesNotExist:
                pass
        
        # Fallback: Si no hay empresa en el usuario, usar la del tenant (compatibilidad)
        if not empresa:
            empresa = Empresa.objects.only('id').first()
        
        if not empresa: 
            return Empleado.objects.none()
        
        empresa_id = empresa.id
        search = self.request.query_params.get('search', None)
        
        # ⚠️ CORRECCIÓN: get_queryset() debe retornar un queryset para todas las acciones
        # DRF usa get_object() para obtener el objeto específico en retrieve
        if self.action == 'list':
            # ⚠️ v2.60: Usar qs_empleado_list del service layer
            return qs_empleado_list(empresa_id, search=search)
        else:
            # Para retrieve y otras acciones, retornar queryset filtrado por empresa
            # DRF usará get_object() que internamente hace .get(pk=pk) sobre este queryset
            return Empleado.objects.filter(empresa_id=empresa_id).order_by('-fecha_ingreso', 'id')
    
    def get_object(self):
        """
        ⚠️ v2.60: Sobrescribir get_object() para usar qs_empleado_detail del service layer.
        Esto asegura que se use el queryset optimizado con .only() y select_related().
        """
        # Obtener empresa del usuario autenticado
        user = getattr(self.request, 'user', None)
        if not user or not user.is_authenticated:
            from rest_framework.exceptions import NotFound
            raise NotFound("Usuario no autenticado")
        
        # Intentar obtener empresa del usuario
        empresa = None
        if hasattr(user, 'empresa'):
            empresa = user.empresa
        elif hasattr(user, 'empresa_id'):
            try:
                empresa = Empresa.objects.only('id').get(id=user.empresa_id)
            except Empresa.DoesNotExist:
                pass
        
        # Fallback: Si no hay empresa en el usuario, usar la del tenant (compatibilidad)
        if not empresa:
            empresa = Empresa.objects.only('id').first()
        
        if not empresa:
            from rest_framework.exceptions import NotFound
            raise NotFound("No se encontró configuración de Empresa para este tenant")
        
        empresa_id = empresa.id
        empleado_id = self.kwargs.get('pk')
        
        # ⚠️ v2.60: Usar qs_empleado_detail del service layer para obtener el objeto optimizado
        try:
            return qs_empleado_detail(empresa_id, empleado_id)
        except Empleado.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound(f"Empleado con ID {empleado_id} no encontrado o no pertenece a este tenant")
    
    def list(self, request, *args, **kwargs):
        """
        ⚠️ v2.60: Listado paginado con formato DRF {count, results} para Tabulator Factory.
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
        ⚠️ v2.40: Sobrescribir create para manejar errores de empresa no encontrada y validaciones.
        """
        try:
            # Validar datos del serializer primero
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            # Ejecutar perform_create que asigna empresa
            self.perform_create(serializer)
            
            # ⚠️ Paso 4: Retornar respuesta con was_updated para listeners JS
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
        from apps.tenant.empresa.models import Empresa
        empresa = Empresa.objects.first()
        if not empresa:
            raise ValueError("No se encontró una empresa. Debe crear una empresa antes de crear empleados.")
        serializer.save(empresa=empresa)
    
    def update(self, request, *args, **kwargs):
        """
        ⚠️ Paso 4: Sobrescribir update para devolver respuesta JSON con was_updated.
        Permite que los listeners JS distingan entre creación y actualización.
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        # ⚠️ Paso 4: Devolver respuesta con was_updated para listeners JS
        response_data = serializer.data
        response_data['was_updated'] = True
        response_data['message'] = 'Empleado actualizado correctamente'
        
        return Response(response_data, status=status.HTTP_200_OK)
    
    def partial_update(self, request, *args, **kwargs):
        """
        ⚠️ Paso 4: Sobrescribir partial_update para devolver respuesta JSON con was_updated.
        """
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)
    
    def perform_update(self, serializer):
        """
        ⚠️ v2.40: Al actualizar un empleado, si el estado cambia a RETIRADO,
        cancelar automáticamente todos los contratos activos.
        """
        instance = serializer.instance
        nuevo_estado = serializer.validated_data.get('estado', instance.estado)
        estado_anterior = instance.estado
        
        # Guardar el empleado primero
        empleado = serializer.save()
        
        # ⚠️ v2.40: Si el estado cambió a RETIRADO, cancelar contratos activos
        if estado_anterior != 'RETIRADO' and nuevo_estado == 'RETIRADO':
            contratos_cancelados = cancelar_contratos_activos_al_retirar(empleado)
            if contratos_cancelados > 0:
                logger.info(
                    f"[EmpleadoViewSet] Empleado {empleado.id} retirado. "
                    f"Se cancelaron {contratos_cancelados} contrato(s) activo(s)."
                )
        
        return empleado
    
    def destroy(self, request, *args, **kwargs):
        """
        ⚠️ v2.40: Eliminación definitiva (Hard Delete) solo para empleados RETIRADOS.
        Usa el service layer para eliminar en cascada todas las dependencias.
        """
        from django.core.exceptions import ValidationError
        
        instance = self.get_object()
        
        try:
            # ⚠️ v2.40: Usar service layer para eliminación en cascada
            resultado = eliminar_empleado_retirado(instance)
            
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
        empresa = Empresa.objects.only('id').first()
        if not empresa: 
            return Response({"error": "sin_empresa"}, status=404)
        return Response(get_nomina_summary(empresa.id))
    
    @action(detail=True, methods=["get"], renderer_classes=[TemplateHTMLRenderer, JSONRenderer], url_path="historial-nominas")
    def historial_nominas(self, request, pk=None):
        """
        ⚠️ v2.60: Devuelve el HTML del historial de nóminas para un empleado específico (HTMX)
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
        
        # ⚠️ v2.60: Zero Trust - Validar que el empleado pertenezca al tenant
        if empleado.empresa_id != empresa.id:
            return Response(
                {"error": "El empleado no pertenece a este tenant."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # ⚠️ v2.60: Si se solicita formato JSON, retornar datos para Tabulator
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
        
        # ⚠️ v2.60: Retornar template HTML del offcanvas
        context = {
            'empresa': empresa,
            'empleado': empleado,
        }
        
        return Response(context, template_name='tenant/core/partials/empleados/historial_nominas_offcanvas.html')
    
    def get_empresa(self):
        """
        ⚠️ v2.60: Zero Trust - Obtiene la empresa del tenant actual.
        """
        empresa = Empresa.objects.only('id').first()
        if not empresa:
            raise serializers.ValidationError("No se encontró configuración de Empresa para este tenant.")
        return empresa
    
    @action(detail=False, methods=["get"], renderer_classes=[TemplateHTMLRenderer, JSONRenderer], url_path="gestor-offcanvas")
    def gestor_offcanvas(self, request):
        """
        ⚠️ Paso 4: Devuelve el HTML del formulario para HTMX Offcanvas (Zero Trust).
        Centraliza la entrega de templates para los módulos features/*.js
        """
        # ⚠️ Paso 4: Zero Trust - La empresa se extrae del usuario autenticado
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
        context = {'empresa': empresa}
        
        if tipo == 'empleado':
            if obj_id:
                context['empleado'] = get_object_or_404(Empleado, id=obj_id, empresa_id=empresa_id)
            return Response(context, template_name='tenant/core/partials/empleados/empleado_offcanvas.html')
            
        elif tipo == 'contrato':
            if obj_id:
                contrato = get_object_or_404(Contrato, id=obj_id, empresa_id=empresa_id)
                context['contrato'] = contrato
                context['empleado'] = contrato.empleado
            if empleado_id:
                context['empleado'] = get_object_or_404(Empleado, id=empleado_id, empresa_id=empresa_id)
            return Response(context, template_name='tenant/core/partials/empleados/contrato_offcanvas.html')
            
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
            return Response(context, template_name='tenant/core/partials/empleados/devengo_offcanvas.html')
            
        return Response({"error": "Tipo no válido"}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["get"], url_path="contrato-disponible")
    def contrato_disponible(self, request, pk=None):
        """
        ⚠️ v2.40: Valida si el empleado tiene contrato activo disponible para nómina.
        Verifica que no exista ya un devengo para el periodo_mes actual.
        """
        from apps.tenant.empresa.models import Empresa
        from datetime import datetime
        
        empresa = Empresa.objects.first()
        if not empresa:
            return Response({"error": "sin_empresa"}, status=status.HTTP_404_NOT_FOUND)
        
        empleado = self.get_object()
        
        # 1. Buscar contrato activo del empleado (⚠️ v2.40: Máquina de Estados - usar estado='ACTIVO')
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
        
        # ⚠️ v2.40: Máquina de Estados - Validar que el contrato esté ACTIVO
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

class ContratoViewSet(EnforcedModeMixin, viewsets.ModelViewSet):
    """
    ⚠️ v2.40: ViewSet para gestionar la relación Empleado-Contrato.
    Usa service layer para garantizar unicidad de contratos activos.
    """
    serializer_class = ContratoNestedSerializer
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
    # ⚠️ v2.40: Permitir subida de archivos PDF (opcional)
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['empleado', 'estado', 'activo']  # ⚠️ v2.40: Permite filtrar por empleado, estado y activo (legacy)
    
    def create(self, request, *args, **kwargs):
        """
        ⚠️ v2.95: Sobrescribir create para manejar errores y validaciones.
        """
        try:
            # ⚠️ DEBUG: Log de datos recibidos
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
            
            # ⚠️ Paso 4: Agregar was_updated a la respuesta para listeners JS
            if response.status_code == status.HTTP_201_CREATED:
                response_data = response.data
                if isinstance(response_data, dict):
                    response_data['was_updated'] = False
                    response_data['message'] = 'Contrato creado correctamente'
            
            return response
        except serializers.ValidationError as e:
            logger.error(f"[ContratoViewSet] Error de validación en create: {str(e)}", exc_info=True)
            # ⚠️ v2.60: Error Boundary Pattern - Retornar formato JSON estructurado para UIManager
            error_detail = e.detail if hasattr(e, 'detail') else str(e)
            if isinstance(error_detail, dict):
                return Response(error_detail, status=status.HTTP_400_BAD_REQUEST)
            return Response(
                {"error": "Error de validación en el contrato", "detail": str(error_detail)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except IntegrityError as e:
            logger.error(f"[ContratoViewSet] Error de integridad en create: {str(e)}", exc_info=True)
            # ⚠️ v2.60: Error Boundary Pattern - Verificar si es un error de unicidad (contrato activo duplicado)
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

    def get_queryset(self):
        """
        ⚠️ v2.60: QuerySet optimizado usando service layer.
        """
        empresa = Empresa.objects.only('id').first()
        if not empresa:
            return Contrato.objects.none()
        
        empresa_id = empresa.id
        search = self.request.query_params.get('search', None)
        empleado_id = self.request.query_params.get('empleado', None)
        
        if self.action == 'list':
            # ⚠️ v2.60: Usar qs_contrato_list del service layer
            return qs_contrato_list(empresa_id, search=search, empleado_id=empleado_id)
        elif self.action == 'retrieve':
            # ⚠️ v2.60: Usar qs_contrato_detail del service layer
            contrato_id = self.kwargs.get('pk')
            try:
                return qs_contrato_detail(empresa_id, contrato_id)
            except Contrato.DoesNotExist:
                return Contrato.objects.none()
        
        # Fallback para otras acciones
        return Contrato.objects.filter(empresa_id=empresa_id).order_by('-fecha_inicio', 'id')
    
    def list(self, request, *args, **kwargs):
        """
        ⚠️ v2.60: Listado paginado con formato DRF {count, results} para Tabulator Factory.
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
        ⚠️ v2.40: Usa service layer para crear contrato y garantizar unicidad.
        """
        from rest_framework.exceptions import ValidationError
        from decimal import Decimal
        
        # ⚠️ DEBUG: Log de validated_data
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
        
        # ⚠️ v2.95: Manejar fecha_fin vacía o null
        if 'fecha_fin' in data and (data['fecha_fin'] == '' or data['fecha_fin'] is None):
            data['fecha_fin'] = None
        
        # ⚠️ v2.95: Asegurar valores numéricos por defecto (usar Decimal)
        if 'auxilio_transporte' not in data or data['auxilio_transporte'] is None:
            data['auxilio_transporte'] = Decimal('0.00')
        else:
            # Convertir a Decimal si viene como string
            if isinstance(data['auxilio_transporte'], str):
                data['auxilio_transporte'] = Decimal(data['auxilio_transporte'] or '0.00')
        
        if 'prestamos_empresa' not in data or data['prestamos_empresa'] is None:
            data['prestamos_empresa'] = Decimal('0.00')
        else:
            # Convertir a Decimal si viene como string
            if isinstance(data['prestamos_empresa'], str):
                data['prestamos_empresa'] = Decimal(data['prestamos_empresa'] or '0.00')
        
        # ⚠️ v2.95: Asegurar que estado esté presente (default: ACTIVO)
        if 'estado' not in data or data['estado'] is None:
            data['estado'] = 'ACTIVO'
        
        # Usar service layer para crear contrato
        try:
            contrato = gestionar_contrato_service(empleado, data)
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
        ⚠️ Paso 4: Sobrescribir update para devolver respuesta JSON con was_updated.
        Permite que los listeners JS distingan entre creación y actualización.
        ⚠️ v2.60: Error Boundary Pattern - Manejo de errores estandarizado.
        """
        try:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            
            # ⚠️ Paso 4: Devolver respuesta con was_updated para listeners JS
            response_data = serializer.data
            response_data['was_updated'] = True
            response_data['message'] = 'Contrato actualizado correctamente'
            
            return Response(response_data, status=status.HTTP_200_OK)
        except serializers.ValidationError as e:
            logger.error(f"[ContratoViewSet] Error de validación en update: {str(e)}", exc_info=True)
            # ⚠️ v2.60: Error Boundary Pattern - Retornar formato JSON estructurado para UIManager
            error_detail = e.detail if hasattr(e, 'detail') else str(e)
            if isinstance(error_detail, dict):
                return Response(error_detail, status=status.HTTP_400_BAD_REQUEST)
            return Response(
                {"error": "Error de validación en el contrato", "detail": str(error_detail)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except IntegrityError as e:
            logger.error(f"[ContratoViewSet] Error de integridad en update: {str(e)}", exc_info=True)
            # ⚠️ v2.60: Error Boundary Pattern - Verificar si es un error de unicidad
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
        ⚠️ Paso 4: Sobrescribir partial_update para devolver respuesta JSON con was_updated.
        """
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)
    
    def perform_update(self, serializer):
        """
        ⚠️ Paso 4: Método para actualizar contrato existente.
        Usa service layer para garantizar integridad.
        """
        from rest_framework.exceptions import ValidationError
        from decimal import Decimal
        
        instance = serializer.instance
        empleado = serializer.validated_data.get('empleado', instance.empleado)
        
        # Extraer datos del serializer (excluyendo empleado que ya está validado)
        data = {k: v for k, v in serializer.validated_data.items() if k != 'empleado'}
        
        # ⚠️ Manejar fecha_fin vacía o null
        if 'fecha_fin' in data and (data['fecha_fin'] == '' or data['fecha_fin'] is None):
            data['fecha_fin'] = None
        
        # ⚠️ Asegurar valores numéricos por defecto (usar Decimal)
        if 'auxilio_transporte' not in data or data['auxilio_transporte'] is None:
            data['auxilio_transporte'] = Decimal('0.00')
        else:
            if isinstance(data['auxilio_transporte'], str):
                data['auxilio_transporte'] = Decimal(data['auxilio_transporte'] or '0.00')
        
        if 'prestamos_empresa' not in data or data['prestamos_empresa'] is None:
            data['prestamos_empresa'] = Decimal('0.00')
        else:
            if isinstance(data['prestamos_empresa'], str):
                data['prestamos_empresa'] = Decimal(data['prestamos_empresa'] or '0.00')
        
        # Usar service layer para actualizar contrato
        try:
            contrato = gestionar_contrato_service(empleado, data, contrato_existente=instance)
            # Actualizar el serializer con la instancia actualizada
            serializer.instance = contrato
        except ValidationError as ve:
            raise ve
        except Exception as e:
            logger.error(f"[ContratoViewSet] Error en perform_update: {str(e)}", exc_info=True)
            raise ValidationError({'detail': [f'Error al actualizar contrato: {str(e)}']})
    
    @action(detail=True, methods=['post'], url_path='cancelar')
    def cancelar(self, request, pk=None):
        """
        ⚠️ v2.40: Máquina de Estados - Cambia el estado de un contrato a INACTIVO.
        ⚠️ v2.60: Error Boundary Pattern - Manejo de errores estandarizado.
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

class DevengoViewSet(EnforcedModeMixin, viewsets.ModelViewSet):
    """Nómina Inmutable v2.40."""
    serializer_class = DevengoSerializer
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
    # ⚠️ v2.40: Filtrado por empleado para el historial de pagos
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['empleado', 'anulado']  # Permite filtrar por empleado y estado anulado
    ordering_fields = ['fecha_pago', 'periodo_mes', 'id']
    ordering = ['-fecha_pago', '-periodo_mes', 'id']
    
    def get_queryset(self):
        """
        ⚠️ v2.60: QuerySet optimizado usando service layer.
        Ordena por fecha de pago (más reciente primero), luego por periodo y ID.
        """
        empresa = Empresa.objects.only('id').first()
        if not empresa:
            return Devengo.objects.none()
        
        empresa_id = empresa.id
        search = self.request.query_params.get('search', None)
        empleado_id = self.request.query_params.get('empleado', None)
        periodo_mes = self.request.query_params.get('periodo_mes', None)
        
        # ⚠️ v2.60: Convertir empleado_id a int si viene como string
        if empleado_id:
            try:
                empleado_id = int(empleado_id)
            except (ValueError, TypeError):
                logger.warning(f"[DevengoViewSet] empleado_id inválido: {empleado_id}")
                empleado_id = None
        
        if self.action == 'list':
            # ⚠️ v2.60: Usar qs_devengo_list del service layer
            queryset = qs_devengo_list(empresa_id, search=search, empleado_id=empleado_id, periodo_mes=periodo_mes)
            
            # ⚠️ v2.95: Filtros de fecha para historial de nómina (adicionales al service layer)
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
        elif self.action == 'retrieve':
            # ⚠️ v2.60: Usar qs_devengo_detail del service layer
            devengo_id = self.kwargs.get('pk')
            try:
                return qs_devengo_detail(empresa_id, devengo_id)
            except Devengo.DoesNotExist:
                return Devengo.objects.none()
        
        # Fallback para otras acciones
        return Devengo.objects.filter(empresa_id=empresa_id).order_by('-fecha_pago', '-periodo_mes', 'id')
    
    def list(self, request, *args, **kwargs):
        """
        ⚠️ v2.60: Listado paginado con formato DRF {count, results} para Tabulator Factory.
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
        ⚠️ v2.40: Obtiene la última nómina pagada para un empleado o contrato.
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
        
        # ⚠️ v2.60: Buscar última nómina no anulada del empleado usando empresa_id
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
        ⚠️ v2.60: Sobrescribir create con validación estricta de duplicados (Zero Trust).
        Prohíbe el Upsert automático para proteger la evidencia legal de la nómina.
        Retorna errores en formato JSON para UIManager.handleError.
        
        ⚠️ Validación Preventiva: Verifica duplicados ANTES de validar serializer.
        Si existe una nómina para el mismo empleado y periodo, retorna error 409 Conflict.
        """
        try:
            # ⚠️ DEBUG: Log de datos recibidos
            logger.info(f"[DevengoViewSet] Datos recibidos en create: {request.data}")
            logger.info(f"[DevengoViewSet] Tipo de datos: {type(request.data)}")
            
            # ⚠️ v2.60: Validación Preventiva - Verificar duplicados ANTES de validar serializer
            # ⚠️ Nómina Multitanda: Duplicado solo si coincide empleado + periodo_mes + fecha_pago
            empleado_id = request.data.get('empleado')
            periodo_mes = request.data.get('periodo_mes')
            fecha_pago = request.data.get('fecha_pago')
            
            if empleado_id and periodo_mes and fecha_pago:
                empresa = Empresa.objects.only('id').first()
                if empresa:
                    # ⚠️ v2.60: Convertir fecha_pago a objeto date si viene como string
                    from datetime import datetime
                    try:
                        if isinstance(fecha_pago, str):
                            fecha_pago_obj = datetime.strptime(fecha_pago, '%Y-%m-%d').date()
                        else:
                            fecha_pago_obj = fecha_pago
                    except (ValueError, TypeError) as e:
                        logger.warning(f"[DevengoViewSet] Formato de fecha_pago inválido: {fecha_pago}")
                        fecha_pago_obj = None
                    
                    if fecha_pago_obj:
                        # Buscar nómina existente para este empleado, periodo y fecha de pago (no anulada)
                        devengo_existente = Devengo.objects.filter(
                            empleado_id=empleado_id,
                            periodo_mes=periodo_mes,
                            fecha_pago=fecha_pago_obj,
                            anulado=False,
                            empresa_id=empresa.id
                        ).first()
                        
                        if devengo_existente:
                            logger.warning(
                                f"[DevengoViewSet] Intento de crear nómina duplicada: "
                                f"empleado_id={empleado_id}, periodo_mes={periodo_mes}, "
                                f"fecha_pago={fecha_pago_obj}, devengo_existente_id={devengo_existente.id}"
                            )
                            # ⚠️ v2.60: Retornar error 409 Conflict con mensaje claro
                            return Response(
                                {
                                    "error": "Ya existe una nómina para este empleado, periodo y fecha de pago. Debe anular la nómina existente antes de crear una nueva.",
                                    "detail": f"Ya existe una nómina registrada para el periodo {periodo_mes} con fecha de pago {fecha_pago_obj.strftime('%Y-%m-%d')}. "
                                             f"Para modificar, vaya al Historial de Nóminas, anule la existente y luego cree una nueva.",
                                    "devengo_existente_id": devengo_existente.id,
                                    "periodo_mes": periodo_mes,
                                    "fecha_pago": fecha_pago_obj.strftime('%Y-%m-%d'),
                                    "code": "duplicate_nomina"
                                },
                                status=status.HTTP_409_CONFLICT
                            )
            
            # Validar datos del serializer
            serializer = self.get_serializer(data=request.data)
            
            if not serializer.is_valid():
                # ⚠️ v2.60: Capturar error de unicidad en non_field_errors si viene del modelo
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
                
                # ⚠️ v2.60: Retornar errores de validación en formato estructurado para UIManager
                logger.error(f"[DevengoViewSet] Error de validación en create: {serializer.errors}")
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            # ⚠️ v2.60: Nómina Multitanda - Validar solapamiento de días laborados
            # Antes de crear, verificar que la suma de días laborados en el mes no exceda 31 días
            empleado_id = request.data.get('empleado')
            periodo_mes = request.data.get('periodo_mes')
            dias_laborados = request.data.get('dias_laborados')
            
            if empleado_id and periodo_mes and dias_laborados:
                empresa = Empresa.objects.only('id').first()
                if empresa:
                    try:
                        # ⚠️ v2.60: Usar service layer para validación de límite de días
                        validacion = validar_limite_dias_mes(
                            empleado_id=empleado_id,
                            periodo_mes=periodo_mes,
                            nuevos_dias=dias_laborados,
                            empresa_id=empresa.id,
                            devengo_id_excluir=None  # Es creación, no hay devengo previo
                        )
                        
                        logger.info(
                            f"[DevengoViewSet] Validación preventiva de días: Total={validacion['total_dias']}, "
                            f"Nuevos={validacion['nuevos_dias']}, Final={validacion['total_final']}"
                        )
                    except ValidationError as e:
                        # ⚠️ v2.60: Error Boundary Pattern - Retornar error estructurado para UIManager
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
                        # Continuar con la validación normal si hay error inesperado
            
            # Ejecutar perform_create que calcula valores y guarda (creación nueva)
            self.perform_create(serializer)
            
            # ⚠️ Paso 4: Retornar respuesta con was_updated para listeners JS
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
            # ⚠️ v2.60: Error Boundary Pattern - Retornar formato JSON estructurado para UIManager
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
            # ⚠️ v2.60: Error Boundary Pattern - Capturar error de unicidad específico
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
        ⚠️ v2.60: Permite actualización solo a través de lógica de Upsert en create().
        Método directo bloqueado para mantener inmutabilidad explícita.
        """
        return Response(
            {"detail": "Para actualizar una nómina, use el endpoint de creación. El sistema detectará automáticamente si existe una nómina para el mismo periodo y la actualizará."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )
    
    def partial_update(self, request, *args, **kwargs):
        """
        ⚠️ v2.60: Permite actualización solo a través de lógica de Upsert en create().
        Método directo bloqueado para mantener inmutabilidad explícita.
        """
        return Response(
            {"detail": "Para actualizar una nómina, use el endpoint de creación. El sistema detectará automáticamente si existe una nómina para el mismo periodo y la actualizará."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )
    
    def destroy(self, request, *args, **kwargs):
        """
        ⚠️ v2.60: Eliminación de nómina (Hard Delete).
        Valida Zero Trust y registra en log de auditoría.
        """
        from decimal import Decimal
        
        instance = self.get_object()
        empresa = Empresa.objects.only('id').first()
        
        if not empresa:
            return Response(
                {"error": "No se encontró configuración de Empresa para este tenant."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # ⚠️ v2.60: Zero Trust - Validar que la nómina pertenezca al tenant
        if instance.empresa_id != empresa.id:
            return Response(
                {"error": "La nómina no pertenece a este tenant."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # ⚠️ v2.60: Validar que la nómina no esté anulada (opcional - puede eliminarse igual)
        # Si está anulada, solo registrar en log
        
        devengo_id = instance.id
        empleado_id = instance.empleado_id
        periodo_mes = instance.periodo_mes
        
        try:
            # ⚠️ v2.60: Si la nómina tiene préstamos descontados, revertir en el contrato
            if instance.prestamos and instance.prestamos > 0:
                contrato = instance.contrato
                if contrato:
                    contrato.refresh_from_db()
                    prestamo_actual = Decimal(str(contrato.prestamos_empresa or 0))
                    nuevo_prestamo = prestamo_actual + Decimal(str(instance.prestamos))
                    contrato.prestamos_empresa = nuevo_prestamo
                    contrato.save(update_fields=['prestamos_empresa'])
                    logger.info(
                        f"[DevengoViewSet] Préstamo revertido al eliminar nómina {devengo_id}: "
                        f"${instance.prestamos:,.2f} agregado al contrato {contrato.id}. "
                        f"Nuevo saldo: ${nuevo_prestamo:,.2f}"
                    )
            
            # Eliminar la nómina
            instance.delete()
            
            # ⚠️ v2.60: Registrar en log de auditoría
            logger.info(
                f"[DevengoViewSet] Nómina eliminada: ID={devengo_id}, "
                f"Empleado={empleado_id}, Periodo={periodo_mes}, "
                f"Empresa={empresa.id}, Usuario={request.user.id if request.user.is_authenticated else 'Anónimo'}"
            )
            
            return Response(
                {"detail": "Nómina eliminada correctamente", "id": devengo_id},
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            logger.error(
                f"[DevengoViewSet] Error al eliminar nómina {devengo_id}: {str(e)}",
                exc_info=True
            )
            return Response(
                {"error": "Ocurrió un error inesperado al eliminar la nómina.", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def perform_update(self, serializer):
        """
        ⚠️ v2.60: Método para actualizar nómina existente (usado en lógica de Upsert).
        Recalcula todos los valores usando la Capa de Servicio antes de guardar (Zero Trust).
        """
        from apps.tenant.empleados.services import calcular_liquidacion_nomina
        from decimal import Decimal
        from django.db import transaction
        from rest_framework.exceptions import ValidationError
        
        # Obtener datos del serializer
        validated_data = serializer.validated_data
        instance = serializer.instance
        contrato = validated_data.get('contrato', instance.contrato)
        empleado = validated_data.get('empleado', instance.empleado)
        
        # ⚠️ v2.60: Máquina de Estados - Backend Guard: Rechazar si contrato no está ACTIVO
        empresa = Empresa.objects.only('id').first()
        if not empresa:
            raise ValidationError({'empresa': 'No se encontró configuración de Empresa para este tenant.'})
        
        if contrato.empresa_id != empresa.id:
            raise ValidationError({'contrato': 'El contrato no pertenece a este tenant.'})
        
        if contrato.estado != 'ACTIVO':
            raise ValidationError({
                'contrato': f'No se puede actualizar nómina: El contrato no está activo (estado actual: {contrato.estado}).'
            })
        
        if not contrato.activo:
            raise ValidationError({'contrato': 'No se puede actualizar nómina: El contrato no está activo.'})
        
        # ⚠️ v2.60: Validar que la nómina no esté anulada
        if instance.anulado:
            raise ValidationError({
                'anulado': 'No se puede actualizar una nómina anulada. Debe crear una nueva.'
            })
        
        dias_laborados = validated_data.get('dias_laborados', instance.dias_laborados)
        horas_trabajadas = validated_data.get('horas_trabajadas', None)
        otros_devengos = validated_data.get('otros_devengos', instance.otros_devengos or Decimal('0'))
        prestamos = validated_data.get('prestamos', instance.prestamos or Decimal('0'))
        descuentos_operativos = validated_data.get('descuentos_operativos', instance.descuentos_operativos or Decimal('0'))
        
        # ⚠️ v2.60: Calcular préstamo anterior para ajuste correcto
        prestamo_anterior = instance.prestamos or Decimal('0')
        diferencia_prestamos = prestamos - prestamo_anterior
        
        # ⚠️ v2.60: Validar que el préstamo a descontar no sea mayor al disponible en el contrato
        if prestamos > 0:
            prestamo_disponible = Decimal(str(contrato.prestamos_empresa or 0))
            # Si se está aumentando el préstamo, validar disponibilidad
            if diferencia_prestamos > 0 and diferencia_prestamos > prestamo_disponible:
                raise ValidationError({
                    'prestamos': f'El monto adicional a descontar (${diferencia_prestamos:,.2f}) no puede ser mayor al préstamo disponible en el contrato (${prestamo_disponible:,.2f})'
                })
        
        # ⚠️ v2.60: Recalcular usando calcular_liquidacion_nomina (SSoT - Normativa Colombiana)
        calculo = calcular_liquidacion_nomina(
            contrato=contrato,
            dias_laborados=dias_laborados,
            horas_trabajadas=horas_trabajadas,
            otros_devengos=otros_devengos,
            prestamos=prestamos,
            descuentos_operativos=descuentos_operativos,
            empresa_id=empresa.id
        )
        
        # Actualizar valores en el serializer con los calculados por el service layer
        serializer.validated_data['salario_base'] = Decimal(calculo['salario_base'])
        serializer.validated_data['auxilio_transporte'] = Decimal(calculo['auxilio_transporte'])
        serializer.validated_data['salud_empleado'] = Decimal(calculo['salud_empleado'])
        serializer.validated_data['pension_empleado'] = Decimal(calculo['pension_empleado'])
        # neto_pagar se calcula en el modelo.save() como SSoT final
        
        # ⚠️ v2.60: Actualizar préstamo del contrato con la diferencia
        with transaction.atomic():
            # Guardar el devengo usando el serializer
            devengo = serializer.save()
            
            # Si hay diferencia en préstamos, actualizar el contrato
            if diferencia_prestamos != 0:
                contrato.refresh_from_db()
                prestamo_actual = Decimal(str(contrato.prestamos_empresa or 0))
                nuevo_prestamo = prestamo_actual - diferencia_prestamos
                
                # No permitir valores negativos
                contrato.prestamos_empresa = max(Decimal('0'), nuevo_prestamo)
                contrato.save(update_fields=['prestamos_empresa'])
                
                logger.info(
                    f'[DevengoViewSet] Préstamo actualizado: diferencia=${diferencia_prestamos:,.2f}. '
                    f'Saldo anterior: ${prestamo_actual:,.2f}. Nuevo saldo: ${contrato.prestamos_empresa:,.2f}'
                )

    def perform_create(self, serializer):
        """
        ⚠️ v2.40: Usa el service layer para calcular valores proporcionales antes de guardar.
        El frontend envía valores calculados desde previsualizar, pero este método
        asegura que los valores sean correctos usando el service layer como validación.
        
        También actualiza el préstamo del contrato restando el monto descontado.
        
        ⚠️ Máquina de Estados: Bloquea nómina si el contrato no está ACTIVO (Backend Guard).
        ⚠️ v2.95: Usa registrar_devengo_nomina_service para mantener consistencia con service layer.
        """
        from apps.tenant.empleados.services import calcular_liquidacion_nomina
        from decimal import Decimal
        from django.db import transaction
        from rest_framework.exceptions import ValidationError
        
        # Obtener datos del serializer
        validated_data = serializer.validated_data
        contrato = validated_data.get('contrato')
        empleado = validated_data.get('empleado')
        
        # ⚠️ v2.60: Máquina de Estados - Backend Guard: Rechazar si contrato no está ACTIVO
        # Validar que el contrato pertenezca al tenant actual (Zero Trust)
        empresa = Empresa.objects.only('id').first()
        if not empresa:
            raise ValidationError({'empresa': 'No se encontró configuración de Empresa para este tenant.'})
        
        if contrato.empresa_id != empresa.id:
            raise ValidationError({
                'contrato': 'El contrato no pertenece a este tenant.'
            })
        
        if contrato.estado != 'ACTIVO':
            raise ValidationError({
                'contrato': f'No se puede registrar nómina: El contrato no está activo (estado actual: {contrato.estado}).'
            })
        
        # Validación adicional: campo activo legacy
        if not contrato.activo:
            raise ValidationError({
                'contrato': 'No se puede registrar nómina: El contrato no está activo.'
            })
        
        dias_laborados = validated_data.get('dias_laborados', 30)
        horas_trabajadas = validated_data.get('horas_trabajadas', None)  # ⚠️ v2.60: Soporte para cálculo por horas
        otros_devengos = validated_data.get('otros_devengos', Decimal('0'))
        prestamos = validated_data.get('prestamos', Decimal('0'))
        descuentos_operativos = validated_data.get('descuentos_operativos', Decimal('0'))
        periodo_mes = validated_data.get('periodo_mes')
        
        # ⚠️ v2.60: Nómina Multitanda - Validar solapamiento de días laborados usando service layer
        # Verificar que la suma de días laborados en el mes no exceda 31 días (Zero Trust)
        if periodo_mes and dias_laborados:
            try:
                devengo_id_excluir = serializer.instance.pk if serializer.instance else None
                validacion = validar_limite_dias_mes(
                    empleado_id=empleado.id,
                    periodo_mes=periodo_mes,
                    nuevos_dias=dias_laborados,
                    empresa_id=empresa.id,
                    devengo_id_excluir=devengo_id_excluir
                )
                
                logger.info(
                    f"[DevengoViewSet] Validación de días: Total={validacion['total_dias']}, "
                    f"Nuevos={validacion['nuevos_dias']}, Final={validacion['total_final']}"
                )
            except ValidationError as e:
                # Re-lanzar como ValidationError del serializer
                raise ValidationError({
                    'dias_laborados': str(e.detail) if hasattr(e, 'detail') else str(e)
                })
            except Exception as e:
                logger.warning(f"[DevengoViewSet] Error al validar solapamiento de días: {str(e)}")
                # Continuar con la validación normal si hay error inesperado
        
        # ⚠️ v2.60: Validar que el préstamo a descontar no sea mayor al disponible en el contrato
        if prestamos > 0:
            prestamo_disponible = Decimal(str(contrato.prestamos_empresa or 0))
            if prestamos > prestamo_disponible:
                raise ValidationError({
                    'prestamos': f'El monto a descontar (${prestamos:,.2f}) no puede ser mayor al préstamo disponible en el contrato (${prestamo_disponible:,.2f})'
                })
        
        # ⚠️ v2.60: Calcular usando calcular_liquidacion_nomina (SSoT - Normativa Colombiana)
        # ⚠️ Zero Trust: Pasar empresa_id para validación estricta
        calculo = calcular_liquidacion_nomina(
            contrato=contrato,
            dias_laborados=dias_laborados,
            horas_trabajadas=horas_trabajadas,
            otros_devengos=otros_devengos,
            prestamos=prestamos,
            descuentos_operativos=descuentos_operativos,
            empresa_id=empresa.id  # ⚠️ Zero Trust: Validar que el contrato pertenezca a esta empresa
        )
        
        # Actualizar valores en el serializer con los calculados por el service layer
        serializer.validated_data['salario_base'] = Decimal(calculo['salario_base'])
        serializer.validated_data['auxilio_transporte'] = Decimal(calculo['auxilio_transporte'])
        serializer.validated_data['salud_empleado'] = Decimal(calculo['salud_empleado'])
        serializer.validated_data['pension_empleado'] = Decimal(calculo['pension_empleado'])
        # neto_pagar se calcula en el modelo.save() como SSoT final
        
        # ⚠️ v2.40: Actualizar préstamo del contrato restando el monto descontado
        with transaction.atomic():
            # Guardar el devengo usando el serializer (mantiene validaciones del modelo)
            devengo = serializer.save()
            
            # Si se descontó un préstamo, actualizar el contrato
            if prestamos > 0:
                # Refrescar el contrato desde la BD para obtener el valor actualizado
                contrato.refresh_from_db()
                prestamo_actual = Decimal(str(contrato.prestamos_empresa or 0))
                nuevo_prestamo = prestamo_actual - prestamos
                
                # No permitir valores negativos
                contrato.prestamos_empresa = max(Decimal('0'), nuevo_prestamo)
                contrato.save(update_fields=['prestamos_empresa'])
                
                logger.info(
                    f'[DevengoViewSet] Préstamo descontado: ${prestamos:,.2f}. '
                    f'Saldo anterior: ${prestamo_actual:,.2f}. Nuevo saldo: ${contrato.prestamos_empresa:,.2f}'
                )

    @action(detail=True, methods=["post"], url_path="anular")
    def anular(self, request, pk=None):
        empresa = Empresa.objects.only('id').first()
        if not empresa:
            return Response({"error": "sin_empresa"}, status=status.HTTP_404_NOT_FOUND)
        devengo = anular_devengo_service(pk, empresa.id)
        return Response({"status": "Anulado correctamente", "id": devengo.id})
    
    @action(detail=False, methods=["post"], renderer_classes=[TemplateHTMLRenderer, JSONRenderer], url_path="preview-calculo", permission_classes=[IsTenantMember])
    def preview_calculo(self, request):
        """
        ⚠️ v2.60: Endpoint para previsualizar cálculo de nómina en tiempo real (HTMX Partial).
        Devuelve un partial HTML con los valores calculados actualizados.
        Usa calcular_nomina_colombia() como única fuente de verdad (SSoT).
        Aplica Error Boundary Pattern con UIManager para manejar valores negativos.
        
        Recibe (POST):
        - contrato: ID del contrato (requerido)
        - dias_laborados: Días trabajados (0.5-30, requerido)
        - periodo_mes: Periodo en formato YYYY-MM (opcional, para validación)
        - fecha_pago: Fecha de pago (opcional, para validación)
        - horas_trabajadas: Horas trabajadas (opcional)
        - otros_devengos: Otros devengos en COP (opcional, default: 0)
        - prestamos: Préstamos a descontar en COP (opcional, default: 0)
        - descuentos_operativos: Descuentos operativos en COP (opcional, default: 0)
        
        Retorna:
        - Partial HTML con los campos actualizados (salario_base, auxilio_transporte, 
          salud_empleado, pension_empleado, neto_pagar)
        - Si hay error, retorna mensaje de error en el contenedor de feedback
        """
        from decimal import Decimal, InvalidOperation
        
        # ⚠️ Paso 4: Zero Trust - La empresa se extrae del usuario autenticado
        empresa = getattr(request.user, 'empresa', None)
        
        if not empresa:
            # Fallback: obtener la empresa del esquema (tenant) actual de forma segura
            from apps.tenant.empresa.models import Empresa
            empresa = Empresa.objects.only('id').first()
            
        if not empresa:
            return Response(
                {"error": "No se encontró configuración de Empresa para este tenant (Sin tenant)."}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        empresa_id = empresa.id
        
        try:
            # ⚠️ v2.60: Extraer datos del request.POST (HTMX envía datos como form-data)
            # Soporta tanto request.data (DRF) como request.POST (HTMX form-data)
            contrato_id = request.data.get('contrato') or request.POST.get('contrato')
            dias_laborados = request.data.get('dias_laborados') or request.POST.get('dias_laborados')
            periodo_mes = request.data.get('periodo_mes') or request.POST.get('periodo_mes')
            fecha_pago = request.data.get('fecha_pago') or request.POST.get('fecha_pago')
            horas_trabajadas = request.data.get('horas_trabajadas') or request.POST.get('horas_trabajadas')
            
            # ⚠️ v2.60: Validar datos requeridos
            if not contrato_id:
                return Response({
                    "error": "El campo 'contrato' es obligatorio. Asegúrese de que el empleado tenga un contrato activo."
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if not dias_laborados:
                return Response({
                    "error": "El campo 'dias_laborados' es obligatorio."
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # ⚠️ v2.60: Zero Trust - Obtener contrato ACTIVO validando empresa_id
            try:
                contrato = Contrato.objects.get(id=contrato_id, estado='ACTIVO', empresa_id=empresa_id)
            except Contrato.DoesNotExist:
                return Response({
                    "error": "Contrato no encontrado o no está activo. Verifique que el contrato pertenezca a este tenant y esté en estado ACTIVO."
                }, status=status.HTTP_404_NOT_FOUND)
            
            # ⚠️ v2.60: Validar días laborados (permite decimales 0.5-30)
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
            
            # ⚠️ v2.60: Validar horas trabajadas si se proporciona
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
            # ⚠️ v2.60: Normalización de decimales usando Decimal para precisión
            try:
                otros_devengos = Decimal(str(request.data.get('otros_devengos', 0) or request.POST.get('otros_devengos', 0) or 0))
                prestamos = Decimal(str(request.data.get('prestamos', 0) or request.POST.get('prestamos', 0) or 0))
                descuentos_operativos = Decimal(str(request.data.get('descuentos_operativos', 0) or request.POST.get('descuentos_operativos', 0) or 0))
            except (ValueError, InvalidOperation, TypeError) as e:
                return Response({
                    "error": f"Error en formato de datos numéricos: {str(e)}"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # ⚠️ v2.60: Validar que el préstamo a descontar no sea mayor al disponible en el contrato
            if prestamos > 0:
                prestamo_disponible = Decimal(str(contrato.prestamos_empresa or 0))
                if prestamos > prestamo_disponible:
                    return Response({
                        "error": f"El monto a descontar (${prestamos:,.2f}) no puede ser mayor al préstamo disponible en el contrato (${prestamo_disponible:,.2f})"
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            # ⚠️ v2.60: Calcular usando calcular_nomina_colombia (SSoT - Normativa Colombiana)
            # ⚠️ Zero Trust: Pasar empresa_id para validación
            calculo = calcular_nomina_colombia(
                contrato=contrato,
                dias_laborados=dias_laborados,
                horas_trabajadas=horas_trabajadas_decimal,
                otros_devengos=otros_devengos,
                prestamos=prestamos,
                descuentos_operativos=descuentos_operativos,
                empresa_id=empresa_id
            )
            
            # ⚠️ Error Boundary Pattern: Validar que el neto no sea negativo
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
            
            return Response(context, template_name='tenant/core/partials/empleados/devengo_calculo_partial.html')
            
        except ValueError as e:
            return Response({
                "error": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except (InvalidOperation, TypeError) as e:
            return Response({
                "error": f"Error en formato de datos numéricos: {str(e)}"
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"[DevengoViewSet] Error en preview_calculo: {str(e)}", exc_info=True)
            return Response({
                "error": "Ocurrió un error inesperado al calcular la nómina.",
                "detail": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=["post"], url_path="previsualizar")
    def previsualizar(self, request):
        """
        ⚠️ v2.60: Endpoint para previsualizar cálculo de nómina sin guardar.
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
        from apps.tenant.empleados.services import calcular_liquidacion_nomina
        from apps.tenant.empleados.models import Contrato
        from decimal import Decimal, InvalidOperation
        
        empresa = Empresa.objects.only('id').first()
        if not empresa:
            return Response({"error": "sin_empresa"}, status=status.HTTP_404_NOT_FOUND)
        
        empresa_id = empresa.id
        
        try:
            # Validar y obtener datos requeridos
            contrato_id = request.data.get('contrato')
            dias_laborados = request.data.get('dias_laborados', 30)
            horas_trabajadas = request.data.get('horas_trabajadas', None)  # ⚠️ v2.60: Soporte para cálculo por horas
            
            if not contrato_id:
                return Response({
                    "error": "El campo 'contrato' es obligatorio"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # ⚠️ v2.60: Máquina de Estados - Obtener contrato ACTIVO con Zero Trust
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
            
            # ⚠️ v2.60: Validar días laborados (permite decimales 0.5-30)
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
            
            # ⚠️ v2.60: Validar horas trabajadas si se proporciona
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
            
            # ⚠️ v2.60: Validar que el préstamo a descontar no sea mayor al disponible en el contrato
            if prestamos > 0:
                prestamo_disponible = Decimal(str(contrato.prestamos_empresa or 0))
                if prestamos > prestamo_disponible:
                    return Response({
                        "error": f"El monto a descontar (${prestamos:,.2f}) no puede ser mayor al préstamo disponible en el contrato (${prestamo_disponible:,.2f})"
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            # ⚠️ v2.60: Calcular usando calcular_liquidacion_nomina (SSoT - Normativa Colombiana)
            calculo = calcular_liquidacion_nomina(
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