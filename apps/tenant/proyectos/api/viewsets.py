"""
ViewSet para Proyectos v3.5 - Alineado con Tabulator Factory y FSD

WARNING: SINTEL v3.5: API-First & Zero-Coupling
- DSV Pattern: Inyeccion de servicios via ProyectoServiceMixin
- Zero Trust: Aislamiento estricto por empresa_id
- Performance: Queries optimizadas (Zero Waste) via Selectors
"""
import logging

from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import APIException, NotFound, ValidationError
from rest_framework.renderers import TemplateHTMLRenderer
from rest_framework.response import Response

from apps.config.api.pagination import StandardResultsSetPagination
from apps.tenant.api.permissions import IsTenantAdminOrReadOnly, IsTenantMember
from apps.tenant.api.base import BaseTenantViewSet
from apps.tenant.core.services.organizational_context import OrganizationalContextMixin
from apps.tenant.empresa.models import Empresa
from .serializers import ProyectoDetailSerializer, ProyectoListSerializer, ItemPresupuestoSerializer, TareaDiariaSerializer, TareaCortaSerializer
from .mixins import ProyectoServiceMixin
from ..models import Proyecto, ItemPresupuestoProyecto, TareaDiariaProyecto, TareaCorta
from ..services import (
    PresupuestoBusinessService, PRESUPUESTO_ITEM_FIELDS,
    TareasDiariasBusinessService, TareasDiariasSelector, TAREA_FIELDS,
    TareasCortasBusinessService, TareaCortaSelector, TAREA_CORTA_FIELDS,
    TareaCortaServiceMixin,
)

try:
    from apps.tenant.inventario.models import HistorialServicio as _HistorialServicio
except ImportError:
    _HistorialServicio = None

try:
    from apps.tenant.clientes.models import Cliente as _ClienteProyecto
except ImportError:
    _ClienteProyecto = None

try:
    from apps.tenant.empleados.services.selectors import EmpleadoSelector as _EmpleadoSelector
except ImportError:
    _EmpleadoSelector = None

try:
    from apps.tenant.proveedores.models import Proveedor as _ProveedorProyecto
except ImportError:
    _ProveedorProyecto = None

try:
    from apps.tenant.facturas.services.business_service import FacturaInterAppAPI as _FacturaInterAppAPI
except ImportError:
    _FacturaInterAppAPI = None

try:
    from apps.tenant.cotizaciones.models import Cotizacion as _CotizacionProyecto
except ImportError:
    _CotizacionProyecto = None

logger = logging.getLogger(__name__)

class ProyectoViewSet(
    OrganizationalContextMixin,
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
    Delegacion absoluta al Service Layer modularizado.

    Fase 9 (OCF): OrganizationalContextMixin adoptado de forma aditiva.
    get_queryset()/get_empresa() no migrados - usan el singleton
    Empresa.objects.only('id').first() sin exigir TenantProfile, mismo
    patron de riesgo ya documentado en empresa (Fase 9 app 1/14).
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
            raise APIException(detail='No se encontro la empresa (SSoT) configurada en este tenant.')
        return empresa
    
    def get_queryset(self):
        """Usa el selector optimizado con Zero Trust."""
        empresa = self.get_empresa()
        search = self.request.query_params.get('search', None)

        # [OSF Fase F7] mismo criterio de degradacion que facturas/
        # cotizaciones/gastos/inventario/compras.
        from apps.tenant.core.services.organizational_scope import (
            OrganizationalScope,
            OrganizationalScopeError,
        )
        try:
            sede_ids = OrganizationalScope.resolve(self.request).sede_ids
        except OrganizationalScopeError:
            sede_ids = None

        return self.proyecto_selector(empresa_id=empresa.id, search=search, sede_ids=sede_ids)
    
    def get_object(self):
        """Usa el selector de detalle optimizado. Filtra por uuid (M-001 Roadmap M3).

        [OSF Fase F13] mismo criterio de degradacion que get_queryset() (F7):
        antes de esta fase, get_object() (retrieve/update/partial_update/
        destroy) solo filtraba por empresa_id.
        """
        empresa = self.get_empresa()

        from apps.tenant.core.services.organizational_scope import (
            OrganizationalScope,
            OrganizationalScopeError,
        )
        try:
            sede_ids = OrganizationalScope.resolve(self.request).sede_ids
        except OrganizationalScopeError:
            sede_ids = None

        obj = self.proyecto_detail_selector(empresa_id=empresa.id, uuid=self.kwargs['uuid'], sede_ids=sede_ids)
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
            # Si no hay empresa, dejar context sin empresa_id (sera manejado por __init__)
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
        empresa = self.get_empresa()
        serializer = self.get_serializer(data=request.data)
        
        # WARNING: Logging para debug de validacion
        if not serializer.is_valid():
            logger.error(f"[ProyectoViewSet] Validacion fallida: {serializer.errors}")
            # WARNING: [SEC-M6] Solo se loguean los nombres de campo, no los valores
            # (pueden incluir datos de cliente/presupuesto/PII).
            _campos = list(request.data.keys()) if hasattr(request.data, 'keys') else type(request.data).__name__
            logger.error(f"[ProyectoViewSet] Campos recibidos: {_campos}")
            return Response(
                {'detail': 'Datos invalidos', 'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Orquestacion via Business Service
        try:
            proyecto = self.proyecto_business_service.orchestrate_create_proyecto(
                empresa, 
                serializer.validated_data
            )
        except ValidationError as e:
            logger.error(f"[ProyectoViewSet] Error de negocio: {e.detail}")
            return Response(
                {'detail': 'Error de validacion de negocio', 'errors': e.detail},
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

        historial_prefill = None
        historial_uuid = request.query_params.get('historial_uuid')
        if historial_uuid and not proyecto:
            try:
                if _HistorialServicio is None:
                    raise ImportError
                historial_prefill = _HistorialServicio.objects.select_related('servicio').get(
                    uuid=historial_uuid,
                    empresa_id=empresa.id
                )
            except Exception:
                pass

        clientes = []
        try:
            if _ClienteProyecto is None:
                raise ImportError
            clientes = _ClienteProyecto.objects.filter(empresa_id=empresa.id, activo=True).only(
                'id', 'razon_social', 'numero_documento'
            ).order_by('razon_social')[:100]
        except ImportError:
            pass

        empleados = []
        try:
            if _EmpleadoSelector is None:
                raise ImportError
            empleados = _EmpleadoSelector.get_empleados_activos(empresa_id=empresa.id)[:100]
        except ImportError:
            pass

        proveedores = []
        try:
            if _ProveedorProyecto is None:
                raise ImportError
            proveedores = _ProveedorProyecto.objects.filter(empresa_id=empresa.id, activo=True).only(
                'id', 'razon_social', 'numero_documento'
            ).order_by('razon_social')[:100]
        except ImportError:
            pass

        facturas_raw = []
        try:
            if _FacturaInterAppAPI is None:
                raise ImportError
            facturas_raw = list(
                _FacturaInterAppAPI.list_all()
                # .only('id', 'numero', 'receptor_razon_social', 'total', 'cotizacion_uuid', 'cotizacion_numero')
                .order_by('-fecha_emision')[:200]
            )
        except Exception:
            pass

        # Construir mapa cotizacion_uuid -> datos enriquecidos (single IN query, Zero-Waste)
        cotizaciones_map = {}
        uuids_cot = [str(f.cotizacion_uuid) for f in facturas_raw if f.cotizacion_uuid]
        if uuids_cot:
            try:
                if _CotizacionProyecto is None:
                    raise ImportError
                cots = _CotizacionProyecto.objects.filter(
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
            'historial_prefill': historial_prefill,
        }
        
        # [v3.5] Ruta local FSD
        return Response(context, template_name='tenant/proyectos/offcanvas_form.html')

    @action(detail=False, methods=['post'], url_path='vincular-proyecto')
    def vincular_proyecto(self, request):
        """
        [v3.9.7] Vincula un proyecto recien creado con un registro de HistorialServicio.
        Body: { "proyecto_uuid": "...", "historial_uuid": "..." }
        """
        empresa = self.get_empresa()
        proyecto_uuid = request.data.get('proyecto_uuid')
        historial_uuid = request.data.get('historial_uuid')

        if not proyecto_uuid or not historial_uuid:
            return Response(
                {'detail': 'Los campos "proyecto_uuid" y "historial_uuid" son obligatorios.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Buscar proyecto para validar que exista y pertenezca al tenant (DSV)
        # [OSF Fase F13] antes de esta fase solo filtraba por empresa_id - un
        # perfil alcance=SEDE podia vincular un HistorialServicio a un
        # Proyecto de otra sede.
        from apps.tenant.core.services.organizational_scope import (
            OrganizationalScope,
            OrganizationalScopeError,
        )
        try:
            sede_ids = OrganizationalScope.resolve(request).sede_ids
        except OrganizationalScopeError:
            sede_ids = None
        proyecto = self.proyecto_detail_selector(empresa_id=empresa.id, uuid=proyecto_uuid, sede_ids=sede_ids)
        if not proyecto:
            raise NotFound("Proyecto no encontrado o no pertenece a este tenant.")

        # Buscar HistorialServicio en inventario
        historial = get_object_or_404(_HistorialServicio, uuid=historial_uuid, empresa_id=empresa.id)

        # Establecer la referencia suave
        historial.proyecto_uuid = proyecto.uuid
        historial.proyecto_nombre = proyecto.nombre
        historial.save()

        return Response({'status': 'vinculado_exitosamente'})


class ItemPresupuestoViewSet(OrganizationalContextMixin, BaseTenantViewSet):
    """
    ViewSet para items de presupuesto planeado (v3.5.2).

    Endpoints:
    - GET    /api/v1/proyectos/items-presupuesto/?proyecto_uuid=<uuid>
    - POST   /api/v1/proyectos/items-presupuesto/
    - PATCH  /api/v1/proyectos/items-presupuesto/<uuid>/
    - DELETE /api/v1/proyectos/items-presupuesto/<uuid>/
    """
    serializer_class = ItemPresupuestoSerializer
    queryset = ItemPresupuestoProyecto.objects.none()
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
    # WARNING: [ARQ-A1] lookup_field='uuid' se hereda de BaseTenantViewSet — no
    # redeclarar con 'id' (exponia la PK entera en la URL, AGENTS.md §25.1).

    def get_queryset(self):
        """Filtrado por proyecto_uuid + empresa_id (DSV).

        [OSF Fase F13] Antes de esta fase no filtraba por el alcance
        organizacional del Proyecto padre - un perfil alcance=SEDE podia
        listar/editar items de presupuesto de un Proyecto de otra sede via
        `?proyecto_uuid=`. Se filtra por `proyecto__sede_id` (join), NULL-safe
        igual que el resto de F7/F13.
        """
        empresa_id = self._get_empresa_id()
        qs = ItemPresupuestoProyecto.objects.filter(empresa_id=empresa_id)

        sede_ids = self._get_sede_ids()
        if sede_ids is not None:
            qs = qs.filter(Q(proyecto__sede_id__isnull=True) | Q(proyecto__sede_id__in=sede_ids))

        proyecto_uuid = self.request.query_params.get('proyecto_uuid')
        if proyecto_uuid:
            qs = qs.filter(proyecto__uuid=proyecto_uuid)

        return qs.only(*PRESUPUESTO_ITEM_FIELDS)

    def _get_empresa_id(self):
        """Obtiene empresa_id del contexto de request (multi-tenant)."""
        empresa = Empresa.objects.only('id').first()
        if not empresa:
            raise APIException(detail='No se encontro la empresa configurada en este tenant.')
        return empresa.id

    def _get_sede_ids(self):
        """[OSF Fase F13] mismo criterio de degradacion NULL-safe de F7/F11."""
        from apps.tenant.core.services.organizational_scope import (
            OrganizationalScope,
            OrganizationalScopeError,
        )
        try:
            return OrganizationalScope.resolve(self.request).sede_ids
        except OrganizationalScopeError:
            return None

    def _get_proyecto(self, proyecto_uuid):
        """Obtiene el proyecto correspondiente (DSV).

        [OSF Fase F13] antes de esta fase solo filtraba por empresa_id.
        """
        empresa_id = self._get_empresa_id()
        qs = Proyecto.objects.filter(uuid=proyecto_uuid, empresa_id=empresa_id)
        sede_ids = self._get_sede_ids()
        if sede_ids is not None:
            qs = qs.filter(Q(sede_id__isnull=True) | Q(sede_id__in=sede_ids))
        return get_object_or_404(qs)

    def perform_create(self, serializer):
        """
        Crea un nuevo item de presupuesto.
        Delegacion al service para validacion y calculo.
        """
        empresa = Empresa.objects.only('id').first()
        proyecto_uuid = self.request.data.get('proyecto_uuid')
        proyecto = self._get_proyecto(proyecto_uuid)

        serializer.instance = PresupuestoBusinessService.crear_item(
            empresa=empresa,
            proyecto=proyecto,
            data=serializer.validated_data
        )

    def perform_update(self, serializer):
        """
        Actualiza un item de presupuesto.
        Delegacion al service para validacion y calculo.
        """
        PresupuestoBusinessService.actualizar_item(
            item=self.get_object(),
            data=serializer.validated_data
        )

    def perform_destroy(self, instance):
        """
        Elimina un item de presupuesto.
        Delegacion al service para recalculo de proyecto padre.
        """
        PresupuestoBusinessService.eliminar_item(instance)


class TareaDiariaViewSet(OrganizationalContextMixin, BaseTenantViewSet):
    """
    ViewSet para tareas diarias (v3.5.3).

    Endpoints:
    - GET    /api/v1/proyectos/tareas-diarias/?proyecto_uuid=<uuid>
    - POST   /api/v1/proyectos/tareas-diarias/
    - PATCH  /api/v1/proyectos/tareas-diarias/<uuid>/
    - DELETE /api/v1/proyectos/tareas-diarias/<uuid>/
    - POST   /api/v1/proyectos/tareas-diarias/<uuid>/cambiar-estado/

    DSV: Filtrado automatico por empresa_id via BaseTenantViewSet.
    """
    serializer_class = TareaDiariaSerializer
    queryset = TareaDiariaProyecto.objects.none()
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
    # WARNING: [ARQ-A1] lookup_field='uuid' se hereda de BaseTenantViewSet — no
    # redeclarar con 'id' (exponia la PK entera en la URL, AGENTS.md §25.1).

    def get_queryset(self):
        """Filtrado por proyecto_uuid + empresa_id (DSV).

        [OSF Fase F13] mismo criterio que ItemPresupuestoViewSet - antes de
        esta fase no filtraba por el alcance organizacional del Proyecto
        padre. NULL-safe via join `proyecto__sede_id`.
        """
        empresa_id = self._get_empresa_id()
        qs = TareaDiariaProyecto.objects.filter(empresa_id=empresa_id)

        from apps.tenant.core.services.organizational_scope import (
            OrganizationalScope,
            OrganizationalScopeError,
        )
        try:
            sede_ids = OrganizationalScope.resolve(self.request).sede_ids
        except OrganizationalScopeError:
            sede_ids = None
        if sede_ids is not None:
            qs = qs.filter(Q(proyecto__sede_id__isnull=True) | Q(proyecto__sede_id__in=sede_ids))

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
            raise APIException(detail='No se encontro la empresa configurada en este tenant.')
        return empresa.id

    def _get_proyecto(self, proyecto_uuid):
        """Obtiene el proyecto correspondiente (DSV).

        [OSF Fase F13] antes de esta fase solo filtraba por empresa_id -
        mismo gap que ItemPresupuestoViewSet._get_proyecto().
        """
        from apps.tenant.core.services.organizational_scope import (
            OrganizationalScope,
            OrganizationalScopeError,
        )
        empresa_id = self._get_empresa_id()
        qs = Proyecto.objects.filter(uuid=proyecto_uuid, empresa_id=empresa_id)
        try:
            sede_ids = OrganizationalScope.resolve(self.request).sede_ids
        except OrganizationalScopeError:
            sede_ids = None
        if sede_ids is not None:
            qs = qs.filter(Q(sede_id__isnull=True) | Q(sede_id__in=sede_ids))
        return get_object_or_404(qs)

    def perform_create(self, serializer):
        """
        Crea una nueva tarea diaria.
        Delegacion al service para validaciones y calculos.
        """
        empresa = Empresa.objects.only('id').first()
        proyecto_uuid = self.request.data.get('proyecto_uuid')
        proyecto = self._get_proyecto(proyecto_uuid)

        serializer.instance = TareasDiariasBusinessService.crear_tarea(
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
        Delegacion al service para validaciones.
        """
        TareasDiariasBusinessService.actualizar_tarea(
            tarea=self.get_object(),
            data=serializer.validated_data
        )

    def perform_destroy(self, instance):
        """
        Elimina una tarea diaria.
        Delegacion al service para validaciones.
        """
        TareasDiariasBusinessService.eliminar_tarea(instance)

    @action(detail=True, methods=['post'], url_path='cambiar-estado')
    def cambiar_estado(self, request, uuid=None):
        """
        POST /api/v1/proyectos/tareas-diarias/<uuid>/cambiar-estado/
        Cambia el estado de una tarea (PENDIENTE -> EN_PROCESO -> COMPLETADA, etc).

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


class TareaCortaViewSet(OrganizationalContextMixin, TareaCortaServiceMixin, BaseTenantViewSet):
    """
    ViewSet para Tareas Cortas v3.10.0.

    Endpoints:
    - GET    /api/v1/proyectos/tareas-cortas/?empleado_uuid=<uuid>
    - GET    /api/v1/proyectos/tareas-cortas/<uuid>/
    - POST   /api/v1/proyectos/tareas-cortas/
    - PATCH  /api/v1/proyectos/tareas-cortas/<uuid>/
    - DELETE /api/v1/proyectos/tareas-cortas/<uuid>/
    - POST   /api/v1/proyectos/tareas-cortas/<uuid>/cambiar-estado/

    DSV: Filtrado automatico por empresa_id via TareaCortaServiceMixin.
    """
    serializer_class = TareaCortaSerializer
    queryset = TareaCorta.objects.none()
    permission_classes = [IsTenantMember, IsTenantAdminOrReadOnly]
    lookup_field = 'uuid'
    lookup_url_kwarg = 'uuid'
    lookup_value_regex = '[0-9a-f-]{36}'

    def _get_empresa(self):
        empresa = Empresa.objects.only('id').first()
        if not empresa:
            raise APIException(detail='No se encontro la empresa configurada en este tenant.')
        return empresa

    def get_empresa_id(self):
        return self._get_empresa().id

    def get_queryset(self):
        return self.get_qs_list()

    def get_object(self):
        empresa_id = self.get_empresa_id()
        uuid = self.kwargs.get('uuid')
        obj = TareaCortaSelector.get_tarea_corta(empresa_id, uuid)
        if not obj:
            raise NotFound('Tarea corta no encontrada o no pertenece a este tenant.')
        return obj

    def perform_create(self, serializer):
        empresa = self._get_empresa()
        cliente = serializer.validated_data.pop('cliente', None)
        empleado = serializer.validated_data.pop('empleado', None)
        serializer.instance = TareasCortasBusinessService.crear_tarea_corta(
            empresa=empresa,
            cliente=cliente,
            empleado=empleado,
            fecha_inicio=serializer.validated_data['fecha_inicio'],
            fecha_fin=serializer.validated_data['fecha_fin'],
            titulo=serializer.validated_data['titulo'],
            descripcion=serializer.validated_data.get('descripcion', ''),
            prioridad=serializer.validated_data.get('prioridad', 'NORMAL'),
            notas_progreso=serializer.validated_data.get('notas_progreso', '')
        )

    def perform_update(self, serializer):
        TareasCortasBusinessService.actualizar_tarea_corta(
            tarea_corta=self.get_object(),
            data=serializer.validated_data
        )

    def perform_destroy(self, instance):
        TareasCortasBusinessService.eliminar_tarea_corta(instance)

    @action(detail=True, methods=['post'], url_path='cambiar-estado')
    def cambiar_estado(self, request, uuid=None):
        """
        POST /api/v1/proyectos/tareas-cortas/<uuid>/cambiar-estado/
        Cambia el estado de una tarea corta.

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
            TareasCortasBusinessService.cambiar_estado_tarea_corta(tarea, nuevo_estado)
            serializer = self.get_serializer(tarea)
            return Response(serializer.data)
        except ValidationError as e:
            return Response(
                {'detail': str(e.detail) if hasattr(e, 'detail') else str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

