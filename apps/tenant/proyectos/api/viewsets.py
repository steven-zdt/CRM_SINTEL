"""
ViewSet para Proyectos v3.5 - Alineado con Tabulator Factory y FSD

WARNING: SINTEL v3.5: API-First & Zero-Coupling
- DSV Pattern: Inyección de servicios vía ProyectoServiceMixin
- Zero Trust: Aislamiento estricto por empresa_id
- Performance: Queries optimizadas (Zero Waste) vía Selectors
"""
from django.shortcuts import get_object_or_404
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import APIException, NotFound, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.renderers import TemplateHTMLRenderer
from rest_framework.response import Response

from apps.tenant.api.permissions import IsTenantAdminOrReadOnly, IsTenantMember
from apps.tenant.api.base import BaseTenantViewSet
from apps.tenant.empresa.models import Empresa
from .serializers import ProyectoDetailSerializer, ProyectoListSerializer, ItemPresupuestoSerializer, TareaDiariaSerializer
from .mixins import ProyectoServiceMixin
from ..models import Proyecto, ItemPresupuestoProyecto, TareaDiariaProyecto
from ..services import PresupuestoBusinessService, PRESUPUESTO_ITEM_FIELDS, TareasDiariasBusinessService, TareasDiariasSelector, TAREA_FIELDS

class StandardResultsSetPagination(PageNumberPagination):
    """
    Paginación estándar SaaS para Tabulator.
    """
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class ProyectoViewSet(
    ProyectoServiceMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet
):
    """
    ViewSet para Proyectos v3.5.
    Delegación absoluta al Service Layer modularizado.
    """
    queryset = Proyecto.objects.none()
    pagination_class = StandardResultsSetPagination
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
    lookup_field = 'uuid'
    lookup_value_regex = '[0-9a-f-]{36}'
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ProyectoListSerializer
        return ProyectoDetailSerializer
    
    def get_empresa(self):
        empresa = Empresa.objects.only('id').first()
        if not empresa:
            raise APIException(detail='No se encontró la empresa (SSoT) configurada en este tenant.')
        return empresa
    
    def get_queryset(self):
        """Usa el selector optimizado con Zero Trust."""
        empresa = self.get_empresa()
        search = self.request.query_params.get('search', None)
        return self.proyecto_selector(empresa_id=empresa.id, search=search)
    
    def get_object(self):
        """Usa el selector de detalle optimizado. Filtra por uuid (M-001 Roadmap M3)."""
        empresa = self.get_empresa()
        obj = self.proyecto_detail_selector(empresa_id=empresa.id, uuid=self.kwargs['uuid'])
        if not obj:
            raise NotFound("Proyecto no encontrado o no pertenece a este tenant.")
        return obj

    def get_serializer_context(self):
        """Agrega empresa_id al contexto para que ProyectoDetailSerializer.servicio_asociado lo use."""
        context = super().get_serializer_context()
        try:
            empresa = self.get_empresa()
            context['empresa_id'] = empresa.id
        except Exception:
            # Si no hay empresa, dejar context sin empresa_id (será manejado por __init__)
            pass
        return context

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'count': queryset.count(),
            'results': serializer.data,
            'next': None,
            'previous': None
        }, status=status.HTTP_200_OK)
    
    def create(self, request, *args, **kwargs):
        import logging
        logger = logging.getLogger(__name__)
        
        empresa = self.get_empresa()
        serializer = self.get_serializer(data=request.data)
        
        # ⚠️ Logging para debug de validación
        if not serializer.is_valid():
            logger.error(f"[ProyectoViewSet] Validación fallida: {serializer.errors}")
            logger.error(f"[ProyectoViewSet] Datos recibidos: {request.data}")
            return Response(
                {'detail': 'Datos inválidos', 'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Orquestación vía Business Service
        try:
            proyecto = self.proyecto_business_service.orchestrate_create_proyecto(
                empresa, 
                serializer.validated_data
            )
        except ValidationError as e:
            logger.error(f"[ProyectoViewSet] Error de negocio: {e.detail}")
            return Response(
                {'detail': 'Error de validación de negocio', 'errors': e.detail},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        response_serializer = ProyectoDetailSerializer(proyecto)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    def update(self, request, *args, **kwargs):
        proyecto = self.get_object()
        serializer = self.get_serializer(proyecto, data=request.data)
        serializer.is_valid(raise_exception=True)
        
        proyecto = self.proyecto_business_service.orchestrate_update_proyecto(
            proyecto, 
            serializer.validated_data
        )
        
        response_serializer = ProyectoDetailSerializer(proyecto)
        return Response(response_serializer.data)
    
    def partial_update(self, request, *args, **kwargs):
        proyecto = self.get_object()
        serializer = self.get_serializer(proyecto, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        
        proyecto = self.proyecto_business_service.orchestrate_update_proyecto(
            proyecto, 
            serializer.validated_data
        )
        
        response_serializer = ProyectoDetailSerializer(proyecto)
        return Response(response_serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        proyecto = self.get_object()
        self.proyecto_crud_service.delete_proyecto(proyecto)
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=True, methods=['post'], url_path='avanzar-fase')
    def avanzar_fase(self, request, uuid=None):
        """
        POST /api/v1/proyectos/{id}/avanzar-fase/
        """
        proyecto = self.get_object()
        nueva_fase = request.data.get('fase')
        responsable_id = request.data.get('responsable_id', None)
        responsable_nombre = request.data.get('responsable_nombre', None)
        
        if not nueva_fase:
            return Response({'detail': 'El campo "fase" es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            self.proyecto_business_service.cambiar_fase_proyecto(
                proyecto, nueva_fase, responsable_id, responsable_nombre
            )
            # calcular_indicadores_financieros guarda internamente via crud_service
            self.proyecto_business_service.calcular_indicadores_financieros(proyecto)
            
            response_serializer = ProyectoDetailSerializer(proyecto)
            return Response(response_serializer.data)
            
        except ValidationError as e:
            return Response({'detail': str(e.detail) if hasattr(e, 'detail') else str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='gestor-offcanvas')
    def gestor_offcanvas(self, request):
        """
        [FSD v3.5] Devuelve el HTML del formulario local de la app Proyectos.
        """
        empresa = self.get_empresa()
        proyecto = None
        id_instancia = request.query_params.get('uuid')

        if id_instancia:
            proyecto = get_object_or_404(self.get_queryset(), uuid=id_instancia)
        
        clientes = []
        try:
            from apps.tenant.clientes.models import Cliente
            clientes = Cliente.objects.filter(empresa_id=empresa.id, activo=True).only(
                'id', 'razon_social', 'numero_documento'
            ).order_by('razon_social')[:100]
        except ImportError:
            pass
        
        empleados = []
        try:
            from apps.tenant.empleados.services.selectors import EmpleadoSelector
            empleados = EmpleadoSelector.get_list(empresa_id=empresa.id).only(
                'id', 'primer_nombre', 'primer_apellido', 'segundo_nombre', 'segundo_apellido'
            )[:100]
        except ImportError:
            pass
            
        proveedores = []
        try:
            from apps.tenant.proveedores.models import Proveedor
            proveedores = Proveedor.objects.filter(empresa_id=empresa.id, activo=True).only(
                'id', 'razon_social', 'numero_documento'
            ).order_by('razon_social')[:100]
        except ImportError:
            pass
            
        facturas_raw = []
        try:
            from apps.tenant.facturas.services.business_service import FacturaInterAppAPI
            facturas_raw = list(
                FacturaInterAppAPI.list_all()
                .only('id', 'numero', 'receptor_razon_social', 'total', 'cotizacion_uuid', 'cotizacion_numero')
                .order_by('-fecha_emision')[:200]
            )
        except Exception:
            pass

        # Construir mapa cotizacion_uuid → datos enriquecidos (single IN query, Zero-Waste)
        cotizaciones_map = {}
        uuids_cot = [str(f.cotizacion_uuid) for f in facturas_raw if f.cotizacion_uuid]
        if uuids_cot:
            try:
                from apps.tenant.cotizaciones.models import Cotizacion
                cots = Cotizacion.objects.filter(
                    uuid__in=uuids_cot
                ).select_related('cliente').only(
                    'uuid', 'estado', 'total_con_impuestos',
                    'fecha_emision', 'fecha_vencimiento',
                    'cliente__razon_social'
                )
                cotizaciones_map = {
                    str(c.uuid): {
                        'estado': c.estado,
                        'total': float(c.total_con_impuestos or 0),
                        'cliente': c.cliente.razon_social if c.cliente else '',
                        'fecha_emision': c.fecha_emision.isoformat() if c.fecha_emision else '',
                        'fecha_vencimiento': c.fecha_vencimiento.isoformat() if c.fecha_vencimiento else '',
                    }
                    for c in cots
                }
            except Exception:
                pass

        # Enriquecer facturas como lista de dicts con datos de cotizacion embebidos
        facturas = []
        for f in facturas_raw:
            uuid_key = str(f.cotizacion_uuid) if f.cotizacion_uuid else ''
            cot = cotizaciones_map.get(uuid_key, {})
            facturas.append({
                'id': f.id,
                'numero': f.numero,
                'receptor_razon_social': getattr(f, 'receptor_razon_social', '') or '',
                'cotizacion_uuid': str(f.cotizacion_uuid) if f.cotizacion_uuid else '',
                'cotizacion_numero': f.cotizacion_numero or '',
                'cot_estado': cot.get('estado', ''),
                'cot_total': cot.get('total', ''),
                'cot_cliente': cot.get('cliente', ''),
                'cot_fecha_emision': cot.get('fecha_emision', ''),
                'cot_fecha_vencimiento': cot.get('fecha_vencimiento', ''),
            })

        context = {
            'proyecto': proyecto,
            'clientes': clientes,
            'empleados': empleados,
            'proveedores': proveedores,
            'facturas': facturas,
            'tipos_servicio': Proyecto.TIPO_SERVICIO,
            'fases': Proyecto.FASES,
            'estados_tarea': Proyecto.ESTADO_TAREA,
        }
        
        # [v3.5] Ruta local FSD
        return Response(context, template_name='tenant/proyectos/offcanvas_form.html')


class ItemPresupuestoViewSet(BaseTenantViewSet):
    """
    ViewSet para ítems de presupuesto planeado (v3.5.2).

    Endpoints:
    - GET    /api/v1/proyectos/items-presupuesto/?proyecto_uuid=<uuid>
    - POST   /api/v1/proyectos/items-presupuesto/
    - PATCH  /api/v1/proyectos/items-presupuesto/<id>/
    - DELETE /api/v1/proyectos/items-presupuesto/<id>/
    """
    serializer_class = ItemPresupuestoSerializer
    queryset = ItemPresupuestoProyecto.objects.none()
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
    lookup_field = 'id'
    lookup_url_kwarg = 'id'

    def get_queryset(self):
        """Filtrado por proyecto_uuid + empresa_id (DSV)."""
        empresa_id = self._get_empresa_id()
        qs = ItemPresupuestoProyecto.objects.filter(empresa_id=empresa_id)

        proyecto_uuid = self.request.query_params.get('proyecto_uuid')
        if proyecto_uuid:
            qs = qs.filter(proyecto__uuid=proyecto_uuid)

        return qs.only(*PRESUPUESTO_ITEM_FIELDS)

    def _get_empresa_id(self):
        """Obtiene empresa_id del contexto de request (multi-tenant)."""
        empresa = Empresa.objects.only('id').first()
        if not empresa:
            raise APIException(detail='No se encontró la empresa configurada en este tenant.')
        return empresa.id

    def _get_proyecto(self, proyecto_uuid):
        """Obtiene el proyecto correspondiente (DSV)."""
        empresa_id = self._get_empresa_id()
        proyecto = get_object_or_404(
            Proyecto,
            uuid=proyecto_uuid,
            empresa_id=empresa_id
        )
        return proyecto

    def perform_create(self, serializer):
        """
        Crea un nuevo ítem de presupuesto.
        Delegación al service para validación y cálculo.
        """
        empresa = Empresa.objects.only('id').first()
        proyecto_uuid = self.request.data.get('proyecto_uuid')
        proyecto = self._get_proyecto(proyecto_uuid)

        PresupuestoBusinessService.crear_item(
            empresa=empresa,
            proyecto=proyecto,
            data=serializer.validated_data
        )

    def perform_update(self, serializer):
        """
        Actualiza un ítem de presupuesto.
        Delegación al service para validación y cálculo.
        """
        PresupuestoBusinessService.actualizar_item(
            item=self.get_object(),
            data=serializer.validated_data
        )

    def perform_destroy(self, instance):
        """
        Elimina un ítem de presupuesto.
        Delegación al service para recálculo de proyecto padre.
        """
        PresupuestoBusinessService.eliminar_item(instance)


class TareaDiariaViewSet(BaseTenantViewSet):
    """
    ViewSet para tareas diarias (v3.5.3).

    Endpoints:
    - GET    /api/v1/proyectos/tareas-diarias/?proyecto_uuid=<uuid>
    - POST   /api/v1/proyectos/tareas-diarias/
    - PATCH  /api/v1/proyectos/tareas-diarias/<id>/
    - DELETE /api/v1/proyectos/tareas-diarias/<id>/
    - POST   /api/v1/proyectos/tareas-diarias/<id>/cambiar-estado/

    DSV: Filtrado automático por empresa_id vía BaseTenantViewSet.
    """
    serializer_class = TareaDiariaSerializer
    queryset = TareaDiariaProyecto.objects.none()
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
    lookup_field = 'id'
    lookup_url_kwarg = 'id'

    def get_queryset(self):
        """Filtrado por proyecto_uuid + empresa_id (DSV)."""
        empresa_id = self._get_empresa_id()
        qs = TareaDiariaProyecto.objects.filter(empresa_id=empresa_id)

        proyecto_uuid = self.request.query_params.get('proyecto_uuid')
        if proyecto_uuid:
            qs = qs.filter(proyecto__uuid=proyecto_uuid)

        fecha_inicio = self.request.query_params.get('fecha_inicio')
        if fecha_inicio:
            qs = qs.filter(fecha_inicio__gte=fecha_inicio)

        fecha_fin = self.request.query_params.get('fecha_fin')
        if fecha_fin:
            qs = qs.filter(fecha_fin__lte=fecha_fin)

        return qs.only(*TAREA_FIELDS)

    def _get_empresa_id(self):
        """Obtiene empresa_id del contexto de request (multi-tenant)."""
        empresa = Empresa.objects.only('id').first()
        if not empresa:
            raise APIException(detail='No se encontró la empresa configurada en este tenant.')
        return empresa.id

    def _get_proyecto(self, proyecto_uuid):
        """Obtiene el proyecto correspondiente (DSV)."""
        empresa_id = self._get_empresa_id()
        proyecto = get_object_or_404(
            Proyecto,
            uuid=proyecto_uuid,
            empresa_id=empresa_id
        )
        return proyecto

    def perform_create(self, serializer):
        """
        Crea una nueva tarea diaria.
        Delegación al service para validaciones y cálculos.
        """
        empresa = Empresa.objects.only('id').first()
        proyecto_uuid = self.request.data.get('proyecto_uuid')
        proyecto = self._get_proyecto(proyecto_uuid)

        TareasDiariasBusinessService.crear_tarea(
            empresa=empresa,
            proyecto=proyecto,
            fecha_inicio=serializer.validated_data['fecha_inicio'],
            fecha_fin=serializer.validated_data['fecha_fin'],
            titulo=serializer.validated_data['titulo'],
            descripcion=serializer.validated_data.get('descripcion', ''),
            prioridad=serializer.validated_data.get('prioridad', 'NORMAL'),
            asignado_a=serializer.validated_data.get('asignado_a', '')
        )

    def perform_update(self, serializer):
        """
        Actualiza una tarea diaria.
        Delegación al service para validaciones.
        """
        TareasDiariasBusinessService.actualizar_tarea(
            tarea=self.get_object(),
            data=serializer.validated_data
        )

    def perform_destroy(self, instance):
        """
        Elimina una tarea diaria.
        Delegación al service para validaciones.
        """
        TareasDiariasBusinessService.eliminar_tarea(instance)

    @action(detail=True, methods=['post'], url_path='cambiar-estado')
    def cambiar_estado(self, request, id=None):
        """
        POST /api/v1/proyectos/tareas-diarias/<id>/cambiar-estado/
        Cambia el estado de una tarea (PENDIENTE → EN_PROCESO → COMPLETADA, etc).

        Body: { "nuevo_estado": "EN_PROCESO" | "COMPLETADA" | "CANCELADA" }
        """
        tarea = self.get_object()
        nuevo_estado = request.data.get('nuevo_estado')

        if not nuevo_estado:
            return Response(
                {'detail': 'El campo "nuevo_estado" es requerido.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            TareasDiariasBusinessService.cambiar_estado_tarea(tarea, nuevo_estado)
            serializer = self.get_serializer(tarea)
            return Response(serializer.data)
        except ValidationError as e:
            return Response(
                {'detail': str(e.detail) if hasattr(e, 'detail') else str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
