"""
ViewSet para Proyectos v3.3 - Alineado con Tabulator Factory y SSoT (v2.40)

⚠️ API-First: Endpoints RESTful para consumo desde Tabulator (Vanilla JS)
⚠️ SSoT Strict: La empresa se inyecta automáticamente desde el middleware/tenant.
⚠️ Zero Trust: Las validaciones y la lógica de negocio se delegan a services.py.
"""
from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, APIException, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.renderers import TemplateHTMLRenderer
from django.shortcuts import get_object_or_404

from apps.tenant.empresa.models import Empresa
from apps.tenant.proyectos.models import Proyecto
from apps.tenant.proyectos.services import (
    qs_list, qs_detail, crear_proyecto, actualizar_proyecto, eliminar_proyecto,
    cambiar_fase_proyecto, calcular_indicadores_financieros
)
from apps.tenant.proyectos.api.serializers import (
    ProyectoListSerializer, ProyectoDetailSerializer
)


class StandardResultsSetPagination(PageNumberPagination):
    """
    ⚠️ v2.40: Paginación estándar para Tabulator Factory.
    Tabulator espera la estructura: {count, next, previous, results: [...]}
    """
    page_size = 10  # Estándar SaaS
    page_size_query_param = 'page_size'
    max_page_size = 100


class ProyectoViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet
):
    """
    ⚠️ v3.3: ViewSet para Proyectos con soporte estricto Tabulator v2.40.
    
    Endpoints:
    - GET /api/v1/proyectos/ - Lista paginada (Tabulator Factory)
    - GET /api/v1/proyectos/{id}/ - Detalle completo
    - POST /api/v1/proyectos/ - Crear
    - PUT /api/v1/proyectos/{id}/ - Actualizar completo
    - PATCH /api/v1/proyectos/{id}/ - Actualizar parcial
    - DELETE /api/v1/proyectos/{id}/ - Eliminar
    """
    # ⚠️ CRÍTICO: DRF necesita un queryset definido para generar las rutas del router
    queryset = Proyecto.objects.none()
    pagination_class = StandardResultsSetPagination
    
    def get_serializer_class(self):
        """
        Norma de Mínima Exposición de Datos: 
        Usa ListSerializer para GET list (ligero), DetailSerializer para el resto (pesado).
        """
        if self.action == 'list':
            return ProyectoListSerializer
        return ProyectoDetailSerializer
    
    def get_empresa(self):
        """
        ⚠️ SSoT: Obtiene la empresa del tenant actual.
        Aplica patrón Singleton: Solo debe existir una empresa por tenant.
        Optimizado con .only('id') para evitar extracciones innecesarias.
        """
        empresa = Empresa.objects.only('id').first()
        if not empresa:
            raise APIException(detail='No se encontró la empresa (SSoT) configurada para este tenant.')
        return empresa
    
    def get_queryset(self):
        """
        ⚠️ v2.60: QuerySet optimizado con Zero Trust explícito y soporte ?search= para Tabulator.
        
        ⚠️ Zero Trust: Filtra explícitamente por empresa del tenant actual.
        ⚠️ PERFORMANCE BIBLE: Usa .only() para optimizar queries.
        ⚠️ Delegado enteramente a services.py
        """
        empresa = self.get_empresa()
        search = self.request.query_params.get('search', None)
        # ⚠️ Zero Trust: El queryset ya filtra por empresa_id en services.py
        return qs_list(empresa_id=empresa.id, search=search)
    
    def get_object(self):
        """
        ⚠️ SSoT: Obtiene un proyecto específico garantizando el aislamiento por empresa.
        Delegado enteramente a services.py
        """
        empresa = self.get_empresa()
        obj = qs_detail(empresa_id=empresa.id, pk=self.kwargs['pk'])
        if not obj:
            raise NotFound("Proyecto no encontrado o no pertenece a este tenant.")
        return obj
    
    def list(self, request, *args, **kwargs):
        """
        GET /api/v1/proyectos/
        ⚠️ v2.40: SIEMPRE retorna formato paginado para consistencia con Tabulator Factory.
        """
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        # Fallback de seguridad para Tabulator Factory si la paginación global falla
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'count': queryset.count(),
            'results': serializer.data,
            'next': None,
            'previous': None
        }, status=status.HTTP_200_OK)
    
    def create(self, request, *args, **kwargs):
        """
        POST /api/v1/proyectos/
        ⚠️ Validación de DRF transfiere a services.py para materializar.
        """
        empresa = self.get_empresa()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Delegar lógica de negocio al Service Layer
        proyecto = crear_proyecto(empresa, serializer.validated_data)
        
        # Retornar el detalle completo con el DetailSerializer
        response_serializer = ProyectoDetailSerializer(proyecto)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    def update(self, request, *args, **kwargs):
        """
        PUT /api/v1/proyectos/{id}/
        """
        proyecto = self.get_object()
        serializer = self.get_serializer(proyecto, data=request.data)
        serializer.is_valid(raise_exception=True)
        
        proyecto = actualizar_proyecto(proyecto, serializer.validated_data)
        
        response_serializer = ProyectoDetailSerializer(proyecto)
        return Response(response_serializer.data)
    
    def partial_update(self, request, *args, **kwargs):
        """
        PATCH /api/v1/proyectos/{id}/
        """
        proyecto = self.get_object()
        serializer = self.get_serializer(proyecto, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        
        proyecto = actualizar_proyecto(proyecto, serializer.validated_data)
        
        response_serializer = ProyectoDetailSerializer(proyecto)
        return Response(response_serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        """
        DELETE /api/v1/proyectos/{id}/
        ⚠️ Delega la eliminación al Service Layer para aplicar validaciones del modelo anémico.
        """
        proyecto = self.get_object()
        
        # Se usa el service layer para manejar la eliminación (física o lógica si se adapta el modelo luego)
        eliminar_proyecto(proyecto)
        
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=True, methods=['post'], url_path='avanzar-fase')
    def avanzar_fase(self, request, pk=None):
        """
        POST /api/v1/proyectos/{id}/avanzar-fase/
        ⚠️ Cambia la fase del proyecto y actualiza el responsable correspondiente.
        """
        proyecto = self.get_object()
        nueva_fase = request.data.get('fase')
        responsable_id = request.data.get('responsable_id', None)
        responsable_nombre = request.data.get('responsable_nombre', None)
        
        if not nueva_fase:
            return Response(
                {'detail': 'El campo "fase" es requerido.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Cambiar fase usando el service layer
            cambiar_fase_proyecto(proyecto, nueva_fase, responsable_id, responsable_nombre)
            
            # Guardar cambios
            proyecto.save()
            
            # Recalcular indicadores financieros
            calcular_indicadores_financieros(proyecto)
            
            response_serializer = ProyectoDetailSerializer(proyecto)
            return Response(response_serializer.data)
            
        except ValidationError as e:
            return Response(
                {'detail': str(e.detail) if hasattr(e, 'detail') else str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='gestor-offcanvas')
    def gestor_offcanvas(self, request):
        """
        ⚠️ v2.60: Devuelve el HTML del formulario de proyecto para HTMX Offcanvas.
        
        Endpoint: GET /api/v1/proyectos/gestor-offcanvas/
        
        Query params:
        - id: ID del proyecto (opcional - si no se proporciona, es modo creación)
        
        Returns:
            Template HTML renderizado con contexto del proyecto y catálogos necesarios
        """
        # ⚠️ Zero Trust: Obtener empresa del tenant actual
        empresa = self.get_empresa()
        
        proyecto = None
        id_instancia = request.query_params.get('id')
        
        if id_instancia:
            # ⚠️ Zero Trust: Validar que el proyecto pertenezca al tenant
            proyecto = get_object_or_404(
                self.get_queryset(),
                id=id_instancia
            )
        
        # ⚠️ Catálogos: Cargar lista de clientes para el select (si el módulo existe)
        clientes = []
        try:
            from apps.tenant.clientes.models import Cliente
            clientes = Cliente.objects.filter(empresa_id=empresa.id, activo=True).only(
                'id', 'razon_social', 'numero_documento'
            ).order_by('razon_social')[:100]  # Limitar a 100 para no sobrecargar
        except ImportError:
            # Módulo de clientes no disponible, continuar sin catálogo
            pass
        
        context = {
            'proyecto': proyecto,
            'clientes': clientes,
            'tipos_servicio': Proyecto.TIPO_SERVICIO,
            'fases': Proyecto.FASES,
            'estados_tarea': Proyecto.ESTADO_TAREA,
        }
        
        return Response(context, template_name='tenant/core/partials/proyectos/offcanvas_form.html')