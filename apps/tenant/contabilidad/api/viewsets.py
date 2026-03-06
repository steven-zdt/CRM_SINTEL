"""
ViewSets para la app contabilidad.

⚠️ v2.40: ENFORCED MODE implementado.
POST/PATCH/PUT/DELETE solo para STAFF/ADMIN; no-staff recibe 405.
⚠️ v2.37: Alineado con Service Layer Pattern.
⚠️ IMPORTANTE: 
- django-tenants maneja automáticamente el aislamiento por esquema
- NO es necesario filtrar manualmente por tenant_id

Referencia: https://www.django-rest-framework.org/api-guide/viewsets/
"""
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.authentication import SessionAuthentication
from rest_framework.parsers import JSONParser, FormParser
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from rest_framework.exceptions import ValidationError
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Q
import logging
from apps.tenant.api.base import BaseTenantViewSet
from apps.tenant.api.permissions import IsTenantAdminOrReadOnly
from apps.tenant.contabilidad.models import CuentaContable, AsientoContable, MovimientoContable, PeriodoContable
from apps.tenant.contabilidad.services import (
    qs_cuenta_list, qs_cuenta_detail,
    qs_asiento_list, qs_asiento_detail,
    get_balance_prueba, verificar_periodo_cerrado
)
from apps.tenant.contabilidad.services.asientos_service import (
    aprobar_asiento,
    create_asiento,
    update_asiento,
    delete_asiento,
    listar_documentos_sin_asiento,
    crear_asientos_desde_documentos
)
from apps.tenant.contabilidad.services.cuentas_service import (
    create_cuenta,
    update_cuenta,
    delete_cuenta
)
from apps.tenant.contabilidad.api.serializers import (
    CuentaContableListSerializer,
    CuentaContableDetailSerializer,
    AsientoContableDetailSerializer,
    AsientoContableListSerializer,
    MovimientoContableListSerializer,
    MovimientoContableDetailSerializer,
)
from apps.config.api.pagination import StandardResultsSetPagination


class CuentaContableViewSet(BaseTenantViewSet):
    """
    ViewSet para CuentaContable.
    
    ⚠️ v2.40: ENFORCED MODE - POST/PATCH/PUT/DELETE solo para STAFF/ADMIN.
    ⚠️ v2.37: Usa qs_cuenta_list() y qs_cuenta_detail() del service.
    ⚠️ OPTIMIZACIÓN: NO usa .all(), usa only() para reducir SELECT.
    """
    authentication_classes = [SessionAuthentication]  # ✅ Compatible con dashboard (cookies de sesión)
    permission_classes = [permissions.IsAuthenticated, IsTenantAdminOrReadOnly]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['tipo', 'activa', 'cuenta_padre']
    search_fields = ['codigo', 'nombre', 'descripcion']
    ordering_fields = ['codigo', 'nombre', 'tipo']
    ordering = ['codigo']
    
    def get_serializer_class(self):
        """Selecciona el serializer según la acción."""
        if self.action == "retrieve":
            return CuentaContableDetailSerializer
        return CuentaContableListSerializer
    
    def get_queryset(self):
        """
        QuerySet optimizado usando qs_cuenta_list() y qs_cuenta_detail() del service.
        
        ⚠️ v2.37: Alineado con Service Layer Pattern.
        """
        if self.action == "list":
            return qs_cuenta_list().order_by('codigo')
        elif self.action == "retrieve":
            return qs_cuenta_detail()
        else:
            # Para create/update/delete necesitamos todos los campos
            return CuentaContable.objects.all()
    
    def _check_enforced_mode(self, request):
        """
        Verifica si el usuario tiene permisos para mutaciones (ENFORCED MODE).
        
        ⚠️ ENFORCED: Solo STAFF/ADMIN pueden crear/editar/eliminar.
        No-staff recibe 405 Method Not Allowed.
        
        Returns:
            tuple: (ok: bool, reason: str | None)
        """
        from rest_framework.permissions import SAFE_METHODS
        from apps.tenant.empresa.permissions import IsTenantAdmin
        
        user = request.user
        if not (user and user.is_authenticated):
            return False, "Usuario no autenticado."
        
        if request.method in SAFE_METHODS:
            return True, None  # Lectura siempre permitida
        
        # Para mutaciones (POST, PUT, PATCH, DELETE)
        if IsTenantAdmin().has_permission(request, self):
            return True, None  # ADMIN/STAFF tienen permiso
        
        return False, "Solo usuarios ADMIN/STAFF del tenant pueden crear/editar/eliminar cuentas contables."
    
    def create(self, request, *args, **kwargs):
        """
        Crea una nueva cuenta contable. ⚠️ ENFORCED: Solo STAFF/ADMIN.
        
        ⚠️ v2.60: Service Layer Pattern - Delegación completa a create_cuenta()
        """
        ok, reason = self._check_enforced_mode(request)
        if not ok:
            return Response({"detail": reason}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
        
        try:
            data = request.data.copy()
            resultado = create_cuenta(data)
            
            # Obtener la cuenta completa para serialización
            cuenta = CuentaContable.objects.get(id=resultado['id'])
            serializer = CuentaContableDetailSerializer(cuenta, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            # Errores de validación estructurados del servicio
            return Response(e.detail, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Error al crear cuenta: {str(e)}", exc_info=True)
            return Response(
                {
                    "error": "internal_error",
                    "message": "Error inesperado al crear la cuenta contable.",
                    "missing_fields": []
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def update(self, request, *args, **kwargs):
        """
        Actualiza una cuenta contable. ⚠️ ENFORCED: Solo STAFF/ADMIN.
        
        ⚠️ v2.60: Service Layer Pattern - Delegación completa a update_cuenta()
        """
        ok, reason = self._check_enforced_mode(request)
        if not ok:
            return Response({"detail": reason}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
        
        try:
            cuenta_id = kwargs.get('pk')
            data = request.data.copy()
            resultado = update_cuenta(cuenta_id, data)
            
            # Obtener la cuenta completa para serialización
            cuenta = CuentaContable.objects.get(id=resultado['id'])
            serializer = CuentaContableDetailSerializer(cuenta, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ValidationError as e:
            # Errores de validación estructurados del servicio
            return Response(e.detail, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        except CuentaContable.DoesNotExist:
            return Response(
                {"detail": "Cuenta contable no encontrada."},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Error al actualizar cuenta: {str(e)}", exc_info=True)
            return Response(
                {
                    "error": "internal_error",
                    "message": "Error inesperado al actualizar la cuenta contable.",
                    "missing_fields": []
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def partial_update(self, request, *args, **kwargs):
        """
        Actualiza parcialmente una cuenta contable. ⚠️ ENFORCED: Solo STAFF/ADMIN.
        
        ⚠️ v2.60: Service Layer Pattern - Delegación completa a update_cuenta()
        """
        ok, reason = self._check_enforced_mode(request)
        if not ok:
            return Response({"detail": reason}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
        
        # partial_update usa la misma lógica que update
        return self.update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        """
        Elimina una cuenta contable. ⚠️ ENFORCED: Solo STAFF/ADMIN.
        
        ⚠️ v2.60: Service Layer Pattern - Delegación completa a delete_cuenta()
        """
        ok, reason = self._check_enforced_mode(request)
        if not ok:
            return Response({"detail": reason}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
        
        try:
            cuenta_id = kwargs.get('pk')
            delete_cuenta(cuenta_id)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ValidationError as e:
            # Errores de validación estructurados del servicio
            return Response(e.detail, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        except CuentaContable.DoesNotExist:
            return Response(
                {"detail": "Cuenta contable no encontrada."},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Error al eliminar cuenta: {str(e)}", exc_info=True)
            return Response(
                {
                    "error": "internal_error",
                    "message": "Error inesperado al eliminar la cuenta contable.",
                    "missing_fields": []
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=["post"], url_path="dt/cuentas-contables")
    def datatables(self, request):
        """
        Endpoint DataTables server-side (POST obligatorio v2.40).
        
        ⚠️ v2.40: POST obligatorio según arquitectura, acepta JSON y form-urlencoded.
        ⚠️ OPTIMIZACIÓN: Usa qs_cuenta_list() que ya aplica only() con CUENTA_LIST_FIELDS.
        ✅ Solo carga campos necesarios para la tabla
        ✅ Usa CuentaContableListSerializer para serializar datos
        ✅ Maneja length=-1 cuando paginación está deshabilitada
        """
        # ⚠️ MANEJO ROBUSTO: request.data puede ser QueryDict (FormParser) o dict (JSONParser)
        if hasattr(request, 'data'):
            if hasattr(request.data, 'dict'):  # QueryDict (FormParser)
                params = request.data.dict()
            elif isinstance(request.data, dict):  # dict (JSONParser)
                params = request.data
            else:
                params = dict(request.data) if request.data else {}
        else:
            params = request.POST.dict() if hasattr(request.POST, 'dict') else dict(request.POST)
        
        try:
            draw = int(params.get("draw", "1"))
        except (ValueError, TypeError):
            draw = 1
        
        try:
            start = int(params.get("start", "0"))
            length = int(params.get("length", "10"))
        except (ValueError, TypeError):
            start, length = 0, 10
        
        # Manejar search (puede venir como dict o como string)
        search_value = ""
        if isinstance(params.get("search"), dict):
            search_value = params.get("search", {}).get("value", "") or ""
        elif "search[value]" in params:
            search_value = params.get("search[value]", "") or ""
        elif "search.value" in params:
            search_value = params.get("search.value", "") or ""
        search_value = search_value.strip()
        
        # Base queryset (usa qs_cuenta_list() del service - CUENTA_LIST_FIELDS)
        qs = qs_cuenta_list()
        records_total = qs.count()
        
        # Búsqueda simple
        if search_value:
            qs = qs.filter(
                Q(codigo__icontains=search_value) |
                Q(nombre__icontains=search_value) |
                Q(descripcion__icontains=search_value)
            )
        
        records_filtered = qs.count()
        
        # Orden (mapea columnas 0..n a campos del CUENTA_LIST_FIELDS)
        col_map = {
            "0": "id",
            "1": "codigo",
            "2": "nombre",
            "3": "tipo",
            "4": "activa",
        }
        
        # ⚠️ MANEJO ROBUSTO: order puede venir como lista (JSONParser) o como dict anidado (FormParser)
        if isinstance(params.get("order"), list) and len(params.get("order", [])) > 0:
            order_col = str(params.get("order", [{}])[0].get("column", "1"))
            order_dir = params.get("order", [{}])[0].get("dir", "asc")
        elif "order[0][column]" in params:
            order_col = str(params.get("order[0][column]", "1"))
            order_dir = params.get("order[0][dir]", "asc")
        elif "order.0.column" in params:
            order_col = str(params.get("order.0.column", "1"))
            order_dir = params.get("order.0.dir", "asc")
        else:
            order_col = "1"
            order_dir = "asc"
        
        order_field = col_map.get(str(order_col), "codigo")
        
        if order_dir == "desc":
            order_field = f"-{order_field}"
        
        qs = qs.order_by(order_field)
        
        # Paginación (slice estilo DataTables)
        # ⚠️ CORRECCIÓN: Si length es -1, DataTables quiere todos los registros (paginación deshabilitada)
        if length == -1:
            data_list = list(qs[start:])
        else:
            data_list = list(qs[start:start + length])
        
        # Serializar datos
        serializer = CuentaContableListSerializer(data_list, many=True, context={'request': request})
        
        return Response({
            "draw": draw,
            "recordsTotal": records_total,
            "recordsFiltered": records_filtered,
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='render-offcanvas/crear')
    def render_offcanvas_crear(self, request):
        """
        Endpoint HTMX RESTful para cargar offcanvas de creación de cuentas contables.
        
        ⚠️ v2.60: Feature-Sliced Architecture - Template dedicado para creación
        - GET /api/v1/contabilidad/cuentas-contables/render-offcanvas/crear/ → Modo creación
        
        Returns:
            Template HTML: tenant/contabilidad/partials/cuenta_offcanvas_form.html
        """
        context = {'cuenta': None}
        return Response(context, template_name='tenant/contabilidad/partials/cuenta_offcanvas_form.html')
    
    @action(detail=True, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='render-offcanvas/editar')
    def render_offcanvas_editar(self, request, pk=None):
        """
        Endpoint HTMX RESTful para cargar offcanvas de edición de cuentas contables.
        
        ⚠️ v2.60: Feature-Sliced Architecture - Template dedicado para edición
        - GET /api/v1/contabilidad/cuentas-contables/{id}/render-offcanvas/editar/ → Modo edición
        
        Returns:
            Template HTML: tenant/contabilidad/partials/cuenta_offcanvas_form.html
        """
        cuenta = self.get_object()
        serializer = self.get_serializer(cuenta)
        context = {'cuenta': serializer.data}
        return Response(context, template_name='tenant/contabilidad/partials/cuenta_offcanvas_form.html')
    
    @action(detail=True, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='render-offcanvas/detalle')
    def render_offcanvas_detalle(self, request, pk=None):
        """
        Endpoint HTMX RESTful para cargar offcanvas de detalle de cuentas contables (read-only).
        
        ⚠️ v2.60: Feature-Sliced Architecture - Template dedicado para detalle
        - GET /api/v1/contabilidad/cuentas-contables/{id}/render-offcanvas/detalle/ → Modo lectura
        
        Returns:
            Template HTML: tenant/contabilidad/partials/cuenta_offcanvas_detalle.html
        """
        cuenta = self.get_object()
        serializer = self.get_serializer(cuenta)
        context = {'cuenta': serializer.data}
        return Response(context, template_name='tenant/contabilidad/partials/cuenta_offcanvas_detalle.html')


class AsientoContableViewSet(BaseTenantViewSet):
    """
    ViewSet para AsientoContable.
    
    ⚠️ v2.40: ENFORCED MODE - POST/PATCH/PUT/DELETE solo para STAFF/ADMIN.
    ⚠️ v2.37: Usa qs_asiento_list() y qs_asiento_detail() del service.
    ⚠️ OPTIMIZACIÓN: NO usa .all(), usa only() para reducir SELECT.
    """
    authentication_classes = [SessionAuthentication]  # ✅ Compatible con dashboard (cookies de sesión)
    permission_classes = [permissions.IsAuthenticated, IsTenantAdminOrReadOnly]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['estado', 'fecha']
    search_fields = ['numero', 'descripcion']
    ordering_fields = ['fecha', 'numero', 'total_debe', 'total_haber', 'created_at']
    ordering = ['-fecha', '-numero']
    
    def get_serializer_class(self):
        """Selecciona el serializer según la acción."""
        if self.action == "retrieve":
            return AsientoContableDetailSerializer
        return AsientoContableListSerializer
    
    def get_queryset(self):
        """
        QuerySet optimizado usando qs_asiento_list() y qs_asiento_detail() del service.
        
        ⚠️ v2.37: Alineado con Service Layer Pattern.
        """
        if self.action == "list":
            return qs_asiento_list().order_by('-fecha', '-numero')
        elif self.action == "retrieve":
            return qs_asiento_detail()
        else:
            # Para create/update/delete necesitamos todos los campos
            return AsientoContable.objects.all()
    
    def _check_enforced_mode(self, request):
        """
        Verifica si el usuario tiene permisos para mutaciones (ENFORCED MODE).
        
        ⚠️ ENFORCED: Solo STAFF/ADMIN pueden crear/editar/eliminar.
        No-staff recibe 405 Method Not Allowed.
        
        Returns:
            tuple: (ok: bool, reason: str | None)
        """
        from rest_framework.permissions import SAFE_METHODS
        from apps.tenant.empresa.permissions import IsTenantAdmin
        
        user = request.user
        if not (user and user.is_authenticated):
            return False, "Usuario no autenticado."
        
        if request.method in SAFE_METHODS:
            return True, None  # Lectura siempre permitida
        
        # Para mutaciones (POST, PUT, PATCH, DELETE)
        if IsTenantAdmin().has_permission(request, self):
            return True, None  # ADMIN/STAFF tienen permiso
        
        return False, "Solo usuarios ADMIN/STAFF del tenant pueden crear/editar/eliminar asientos contables."
    
    def create(self, request, *args, **kwargs):
        """
        Crea un nuevo asiento contable. ⚠️ ENFORCED: Solo STAFF/ADMIN.
        
        ⚠️ v2.60: Service Layer Pattern - Delegación completa a create_asiento()
        ⚠️ El servicio valida cuadratura, periodos cerrados y movimientos
        """
        ok, reason = self._check_enforced_mode(request)
        if not ok:
            return Response({"detail": reason}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
        
        try:
            # ⚠️ v2.60: Delegar creación al servicio
            data = request.data.copy()
            resultado = create_asiento(data)
            
            # ⚠️ v2.60: Obtener el asiento completo con movimientos para serialización
            asiento = AsientoContable.objects.prefetch_related('movimientos__cuenta').get(id=resultado['id'])
            serializer = AsientoContableDetailSerializer(asiento, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            # Errores de validación estructurados del servicio
            return Response(e.detail, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        except Exception as e:
            # Errores inesperados
            logger = logging.getLogger(__name__)
            logger.error(f"Error al crear asiento: {str(e)}", exc_info=True)
            return Response(
                {
                    "error": "internal_error",
                    "message": "Error inesperado al crear el asiento contable.",
                    "missing_fields": []
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def update(self, request, *args, **kwargs):
        """
        Actualiza un asiento contable. ⚠️ ENFORCED: Solo STAFF/ADMIN.
        
        ⚠️ v2.60: Service Layer Pattern - Delegación completa a update_asiento()
        """
        ok, reason = self._check_enforced_mode(request)
        if not ok:
            return Response({"detail": reason}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
        
        try:
            asiento_id = kwargs.get('pk')
            data = request.data.copy()
            resultado = update_asiento(asiento_id, data)
            
            # ⚠️ v2.60: Obtener el asiento completo con movimientos para serialización
            asiento = AsientoContable.objects.prefetch_related('movimientos__cuenta').get(id=resultado['id'])
            serializer = AsientoContableDetailSerializer(asiento, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ValidationError as e:
            # Errores de validación estructurados del servicio
            return Response(e.detail, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        except AsientoContable.DoesNotExist:
            return Response(
                {"detail": "Asiento contable no encontrado."},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Error al actualizar asiento: {str(e)}", exc_info=True)
            return Response(
                {
                    "error": "internal_error",
                    "message": "Error inesperado al actualizar el asiento contable.",
                    "missing_fields": []
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def partial_update(self, request, *args, **kwargs):
        """
        Actualiza parcialmente un asiento contable. ⚠️ ENFORCED: Solo STAFF/ADMIN.
        
        ⚠️ v2.60: Service Layer Pattern - Delegación completa a update_asiento()
        """
        ok, reason = self._check_enforced_mode(request)
        if not ok:
            return Response({"detail": reason}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
        
        # partial_update usa la misma lógica que update
        return self.update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        """
        Elimina un asiento contable. ⚠️ ENFORCED: Solo STAFF/ADMIN.
        
        ⚠️ v2.60: Service Layer Pattern - Delegación completa a delete_asiento()
        ⚠️ VALIDACIÓN: El servicio valida inmutabilidad (no se puede eliminar asientos APROBADOS o CERRADOS)
        """
        ok, reason = self._check_enforced_mode(request)
        if not ok:
            return Response({"detail": reason}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
        
        try:
            asiento_id = kwargs.get('pk')
            delete_asiento(asiento_id)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ValidationError as e:
            # Errores de validación estructurados del servicio
            return Response(e.detail, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        except AsientoContable.DoesNotExist:
            return Response(
                {"detail": "Asiento contable no encontrado."},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Error al eliminar asiento: {str(e)}", exc_info=True)
            return Response(
                {
                    "error": "internal_error",
                    "message": "Error inesperado al eliminar el asiento contable.",
                    "missing_fields": []
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=["post"], url_path="dt/asientos-contables")
    def datatables(self, request):
        """
        Endpoint DataTables server-side (POST obligatorio v2.40).
        
        ⚠️ v2.40: POST obligatorio según arquitectura, acepta JSON y form-urlencoded.
        ⚠️ OPTIMIZACIÓN: Usa qs_asiento_list() que ya aplica only() con ASIENTO_LIST_FIELDS.
        ✅ Solo carga campos necesarios para la tabla
        ✅ Usa AsientoContableListSerializer para serializar datos
        ✅ Maneja length=-1 cuando paginación está deshabilitada
        """
        # ⚠️ MANEJO ROBUSTO: request.data puede ser QueryDict (FormParser) o dict (JSONParser)
        if hasattr(request, 'data'):
            if hasattr(request.data, 'dict'):  # QueryDict (FormParser)
                params = request.data.dict()
            elif isinstance(request.data, dict):  # dict (JSONParser)
                params = request.data
            else:
                params = dict(request.data) if request.data else {}
        else:
            params = request.POST.dict() if hasattr(request.POST, 'dict') else dict(request.POST)
        
        try:
            draw = int(params.get("draw", "1"))
        except (ValueError, TypeError):
            draw = 1
        
        try:
            start = int(params.get("start", "0"))
            length = int(params.get("length", "10"))
        except (ValueError, TypeError):
            start, length = 0, 10
        
        # Manejar search (puede venir como dict o como string)
        search_value = ""
        if isinstance(params.get("search"), dict):
            search_value = params.get("search", {}).get("value", "") or ""
        elif "search[value]" in params:
            search_value = params.get("search[value]", "") or ""
        elif "search.value" in params:
            search_value = params.get("search.value", "") or ""
        search_value = search_value.strip()
        
        # Base queryset (usa qs_asiento_list() del service - ASIENTO_LIST_FIELDS)
        qs = qs_asiento_list()
        records_total = qs.count()
        
        # Búsqueda simple
        if search_value:
            qs = qs.filter(
                Q(numero__icontains=search_value) |
                Q(descripcion__icontains=search_value)
            )
        
        records_filtered = qs.count()
        
        # Orden (mapea columnas 0..n a campos del ASIENTO_LIST_FIELDS)
        col_map = {
            "0": "id",
            "1": "numero",
            "2": "fecha",
            "3": "estado",
            "4": "total_debe",
        }
        
        # ⚠️ MANEJO ROBUSTO: order puede venir como lista (JSONParser) o como dict anidado (FormParser)
        if isinstance(params.get("order"), list) and len(params.get("order", [])) > 0:
            order_col = str(params.get("order", [{}])[0].get("column", "2"))
            order_dir = params.get("order", [{}])[0].get("dir", "desc")
        elif "order[0][column]" in params:
            order_col = str(params.get("order[0][column]", "2"))
            order_dir = params.get("order[0][dir]", "desc")
        elif "order.0.column" in params:
            order_col = str(params.get("order.0.column", "2"))
            order_dir = params.get("order.0.dir", "desc")
        else:
            order_col = "2"
            order_dir = "desc"
        
        order_field = col_map.get(str(order_col), "fecha")
        
        if order_dir == "desc":
            order_field = f"-{order_field}"
        
        qs = qs.order_by(order_field)
        
        # Paginación (slice estilo DataTables)
        # ⚠️ CORRECCIÓN: Si length es -1, DataTables quiere todos los registros (paginación deshabilitada)
        if length == -1:
            data_list = list(qs[start:])
        else:
            data_list = list(qs[start:start + length])
        
        # Serializar datos
        serializer = AsientoContableListSerializer(data_list, many=True, context={'request': request})
        
        return Response({
            "draw": draw,
            "recordsTotal": records_total,
            "recordsFiltered": records_filtered,
            "data": serializer.data
        }, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'], url_path='aprobar')
    def aprobar(self, request, pk=None):
        """
        Aprobar un asiento contable.
        
        Endpoint: POST /api/v1/asientos-contables/{id}/aprobar/
        
        ⚠️ v2.60: Service Layer Pattern - Delegación completa a aprobar_asiento()
        ⚠️ v2.60 Fase 3: Error Injector Contable - Analiza movimientos para detectar qué cuenta falta o qué valor sobra.
        Retorna 422 con estructura detallada para error_injector.js si no cuadra.
        """
        asiento = self.get_object()
        
        try:
            resultado = aprobar_asiento(asiento.id)
            
            # ⚠️ v2.60: Si el servicio retorna un error, devolver 422
            if 'error' in resultado:
                return Response(
                    resultado,
                    status=status.HTTP_422_UNPROCESSABLE_ENTITY
                )
            
            # Si no hay error, retornar el asiento aprobado
            serializer = self.get_serializer(asiento)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except AsientoContable.DoesNotExist:
            return Response(
                {"detail": "Asiento contable no encontrado."},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Error inesperado al aprobar asiento {asiento.id}: {str(e)}", exc_info=True)
            return Response(
                {
                    "error": "internal_error",
                    "message": "Error inesperado al aprobar el asiento contable.",
                    "detalles": str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='balance-prueba')
    def balance_prueba(self, request):
        """
        Genera Balance de Prueba agrupado por CuentaContable.codigo.
        
        ⚠️ v2.60 Fase 3: Estándar SSoT para Reportes
        ⚠️ Endpoint: GET /api/v1/contabilidad/asientos-contables/balance-prueba/
        
        Query params:
        - fecha_desde: Fecha inicio (YYYY-MM-DD) - Opcional
        - fecha_hasta: Fecha fin (YYYY-MM-DD) - Opcional
        - empresa_id: ID de la empresa - Opcional
        
        Returns:
            JSON con balance agrupado por cuenta
        """
        empresa_id = request.query_params.get('empresa_id')
        if empresa_id:
            try:
                empresa_id = int(empresa_id)
            except (ValueError, TypeError):
                empresa_id = None
        
        fecha_desde = request.query_params.get('fecha_desde')
        fecha_hasta = request.query_params.get('fecha_hasta')
        
        balance = get_balance_prueba(
            empresa_id=empresa_id,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta
        )
        
        return Response(balance, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='render-offcanvas/crear')
    def render_offcanvas_crear(self, request):
        """
        Endpoint HTMX RESTful para cargar offcanvas de creación de asientos contables.
        
        ⚠️ v2.60: Feature-Sliced Architecture - Template dedicado para creación
        - GET /api/v1/contabilidad/asientos-contables/render-offcanvas/crear/ → Modo creación
        
        Returns:
            Template HTML: tenant/contabilidad/partials/asiento_offcanvas_form.html
        """
        context = {'asiento': None}
        return Response(context, template_name='tenant/contabilidad/partials/asiento_offcanvas_form.html')
    
    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='render-offcanvas/cargar-desde-documentos')
    def render_offcanvas_cargar_desde_documentos(self, request):
        """
        Endpoint HTMX RESTful para cargar offcanvas de selección de documentos.
        
        ⚠️ v2.60 Fase 3: Asistente de Selección - Lista Facturas y Gastos sin asiento
        
        Returns:
            Template HTML: tenant/contabilidad/partials/asiento_offcanvas_cargar_desde_docs.html
        """
        context = {}
        return Response(context, template_name='tenant/contabilidad/partials/asiento_offcanvas_cargar_desde_docs.html')
    
    @action(detail=True, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='render-offcanvas/editar')
    def render_offcanvas_editar(self, request, pk=None):
        """
        Endpoint HTMX RESTful para cargar offcanvas de edición de asientos contables.
        
        ⚠️ v2.60: Feature-Sliced Architecture - Template dedicado para edición
        - GET /api/v1/contabilidad/asientos-contables/{id}/render-offcanvas/editar/ → Modo edición
        
        Returns:
            Template HTML: tenant/contabilidad/partials/asiento_offcanvas_form.html
        """
        asiento = self.get_object()
        serializer = AsientoContableDetailSerializer(asiento, context={'request': request})
        context = {'asiento': serializer.data}
        return Response(context, template_name='tenant/contabilidad/partials/asiento_offcanvas_form.html')
    
    @action(detail=False, methods=['get'], url_path='documentos-sin-asiento')
    def documentos_sin_asiento(self, request):
        """
        Lista documentos (Facturas y Gastos) que no tienen asiento contable asociado.
        
        ⚠️ v2.60: Service Layer Pattern - Delegación completa a listar_documentos_sin_asiento()
        ⚠️ Endpoint: GET /api/v1/contabilidad/asientos-contables/documentos-sin-asiento/
        
        Query params:
        - tipo: 'facturas' o 'gastos' (opcional, si no se especifica retorna ambos)
        
        Returns:
            JSON con listas de facturas y gastos sin asiento
        """
        tipo = request.query_params.get('tipo', '').lower()
        resultado = listar_documentos_sin_asiento(tipo)
        return Response(resultado, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['post'], url_path='crear-desde-documentos')
    def crear_desde_documentos(self, request):
        """
        Crea asientos contables desde documentos seleccionados.
        
        ⚠️ v2.60: Service Layer Pattern - Delegación completa a crear_asientos_desde_documentos()
        ⚠️ v2.60 Fase 3: Materialización masiva desde documentos
        
        Body:
        {
            "facturas": [1, 2, 3],  # IDs de facturas
            "gastos": [4, 5, 6]     # IDs de gastos
        }
        
        Returns:
            JSON con resultado de creación
        """
        ok, reason = self._check_enforced_mode(request)
        if not ok:
            return Response({"detail": reason}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
        
        facturas_ids = request.data.get('facturas', [])
        gastos_ids = request.data.get('gastos', [])
        
        if not facturas_ids and not gastos_ids:
            return Response(
                {
                    "error": "validation_error",
                    "message": "Debe proporcionar al menos un ID de factura o gasto.",
                    "missing_fields": ["facturas", "gastos"]
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )
        
        resultado = crear_asientos_desde_documentos(facturas_ids, gastos_ids)
        return Response(resultado, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='render-offcanvas/detalle')
    def render_offcanvas_detalle(self, request):
        """
        Endpoint HTMX RESTful para cargar offcanvas de detalle de asientos contables.
        
        ⚠️ v2.60: Feature-Sliced Architecture - Template dedicado para detalle
        - GET /api/v1/contabilidad/asientos-contables/render-offcanvas/detalle/?id=123 → Modo detalle
        
        Query params:
        - id: ID del asiento (requerido)
        
        Returns:
            Template HTML: tenant/contabilidad/partials/asiento_offcanvas_detalle.html
        """
        asiento_id = request.query_params.get('id')
        context = {}
        
        if not asiento_id:
            context['error'] = "Se requiere el parámetro 'id' para el modo detalle."
            return Response(context, template_name='tenant/contabilidad/partials/asiento_offcanvas_detalle.html')
        
        try:
            asiento = self.get_queryset().get(id=asiento_id)
            # Usar el serializer de detalle para obtener movimientos
            serializer = AsientoContableDetailSerializer(asiento, context={'request': request})
            context['asiento'] = serializer.data
        except AsientoContable.DoesNotExist:
            context['error'] = f"Asiento contable con ID {asiento_id} no encontrado."
        except Exception as e:
            context['error'] = f"Error al cargar asiento: {str(e)}"
        
        return Response(context, template_name='tenant/contabilidad/partials/asiento_offcanvas_detalle.html')


class MovimientoContableViewSet(viewsets.ModelViewSet):
    """
    ViewSet para MovimientoContable.
    
    ⚠️ OPTIMIZACIÓN: NO usa .all(), usa only() para reducir SELECT.
    """
    authentication_classes = [SessionAuthentication]  # ✅ Compatible con dashboard (cookies de sesión)
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['asiento', 'cuenta']
    search_fields = ['descripcion', 'cuenta__nombre']
    ordering_fields = ['asiento', 'orden', 'debe', 'haber']
    ordering = ['asiento', 'orden']
    
    def get_serializer_class(self):
        """Selecciona el serializer según la acción."""
        if self.action == "retrieve":
            return MovimientoContableDetailSerializer
        return MovimientoContableListSerializer
    
    def get_queryset(self):
        """
        QuerySet optimizado con only() - NO usa .all().
        """
        # Campos mínimos para LIST
        list_fields = ('id', 'asiento', 'cuenta', 'orden', 'debe', 'haber', 'descripcion')
        # Campos para RETRIEVE (mismos campos, pero con select_related para cuenta)
        detail_fields = ('id', 'asiento', 'cuenta', 'orden', 'debe', 'haber', 'descripcion')
        
        if self.action == "list":
            qs = MovimientoContable.objects.only(*list_fields).select_related('cuenta')
        elif self.action == "retrieve":
            qs = MovimientoContable.objects.only(*detail_fields).select_related('cuenta')
        else:
            # Para create/update/delete necesitamos todos los campos
            qs = MovimientoContable.objects.all()
        
        return qs.order_by('asiento', 'orden')


# Lista de ViewSets para registro automático en el router
VIEWSETS = [
    (r'cuentas-contables', CuentaContableViewSet, 'cuenta-contable'),
    (r'asientos-contables', AsientoContableViewSet, 'asiento-contable'),
    (r'movimientos-contables', MovimientoContableViewSet, 'movimiento-contable'),
]
