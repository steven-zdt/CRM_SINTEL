"""
ViewSets para la app contabilidad.

⚠️ v2.60: ENFORCED MODE implementado.
POST/PATCH/PUT/DELETE solo para STAFF/ADMIN; no-staff recibe 405.
⚠️ v2.60: Alineado con Service Layer Pattern.
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
from django.utils.translation import gettext_lazy as _
import logging
import traceback
from apps.tenant.api.base import BaseTenantViewSet
from apps.tenant.api.permissions import IsTenantAdminOrReadOnly

logger = logging.getLogger(__name__)
from apps.tenant.contabilidad.models import (
    CuentaContable, 
    AsientoContable, 
    MovimientoContable, 
    PeriodoContable,
    CatalogoMaestroNIIF
)
from apps.tenant.contabilidad.services import (
    qs_cuenta_list, qs_cuenta_detail,
    qs_asiento_list, qs_asiento_detail,
    qs_periodo_list, qs_periodo_detail
)
# ⚠️ v2.61: NO importar verificar_periodo_cerrado y get_balance_prueba aquí
# Se importarán localmente dentro de las funciones que las necesiten para evitar circular import
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
    PeriodoContableListSerializer,
    PeriodoContableDetailSerializer,
    CatalogoMaestroNIIFListSerializer,
    CatalogoMaestroNIIFDetailSerializer,
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
        if self.action in ["retrieve", "render_offcanvas_editar", "render_offcanvas_detalle"]:
            return CuentaContableDetailSerializer
        return CuentaContableListSerializer
    
    def get_queryset(self):
        """
        QuerySet optimizado usando qs_cuenta_list() y qs_cuenta_detail() del service.
        
        ⚠️ v2.37: Alineado con Service Layer Pattern.
        """
        if self.action == "list":
            return qs_cuenta_list().order_by('codigo')
        elif self.action in ["retrieve", "render_offcanvas_detalle", "render_offcanvas_editar"]:
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
        
        # ⚠️ v2.61: BaseTenantViewSet usa lookup_field="uuid", pero el frontend envía IDs numéricos
        # El router de DRF pone el valor en kwargs['uuid'] cuando lookup_field="uuid"
        # Necesitamos detectar si es numérico (pk) o UUID válido
        cuenta_identifier = kwargs.get('uuid') or kwargs.get('pk')
        
        # ⚠️ v2.61: DEBUG - Log para diagnóstico
        logger = logging.getLogger(__name__)
        logger.info(f"CuentaContableViewSet.destroy llamado con kwargs: {kwargs}, identifier: {cuenta_identifier}")
        
        if not cuenta_identifier:
            logger.error(f"CuentaContableViewSet.destroy: ni uuid ni pk proporcionados. kwargs: {kwargs}, args: {args}")
            return Response(
                {"detail": ["ID de cuenta no proporcionado en la URL."]},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # ⚠️ v2.61: Detectar si el identificador es numérico (pk) o UUID
        # Si es numérico, buscar por pk directamente
        # Si es UUID, usar get_object() que usa lookup_field="uuid"
        cuenta_id = None
        try:
            # Intentar convertir a entero (es un ID numérico)
            cuenta_id = int(cuenta_identifier)
            logger.info(f"CuentaContableViewSet.destroy: Identificador numérico detectado, usando pk={cuenta_id}")
            # Verificar que la cuenta existe
            cuenta = CuentaContable.objects.get(id=cuenta_id)
        except (ValueError, TypeError):
            # No es numérico, intentar como UUID usando get_object()
            try:
                logger.info(f"CuentaContableViewSet.destroy: Intentando como UUID: {cuenta_identifier}")
                cuenta = self.get_object()  # Esto usa lookup_field="uuid" automáticamente
                cuenta_id = cuenta.id
            except (CuentaContable.DoesNotExist, ValueError) as e:
                logger.error(f"CuentaContableViewSet.destroy: Cuenta no encontrada con identificador: {cuenta_identifier}, error: {e}")
                return Response(
                    {"detail": ["Cuenta contable no encontrada."]},
                    status=status.HTTP_404_NOT_FOUND
                )
        except CuentaContable.DoesNotExist:
            logger.error(f"CuentaContableViewSet.destroy: Cuenta no encontrada con pk: {cuenta_identifier}")
            return Response(
                {"detail": ["Cuenta contable no encontrada."]},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
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

    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='render-offcanvas/crear')
    def render_offcanvas_crear(self, request):
        """
        Endpoint HTMX RESTful para cargar offcanvas de creación de cuentas contables.
        
        ⚠️ v2.60: Feature-Sliced Architecture - Template dedicado para creación
        - GET /api/v1/contabilidad/cuentas-contables/render-offcanvas/crear/ → Modo creación
        
        Returns:
            Template HTML: tenant/core/contabilidad/partials/cuenta_offcanvas_form.html
        """
        context = {'cuenta': None}
        return Response(context, template_name='tenant/core/contabilidad/partials/cuenta_offcanvas_form.html')
    
    @action(detail=True, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='render-offcanvas/editar')
    def render_offcanvas_editar(self, request, **kwargs):
        """
        Endpoint HTMX RESTful para cargar offcanvas de edición de cuentas contables.
        
        ⚠️ v2.60: Feature-Sliced Architecture - Template dedicado para edición
        ⚠️ v2.61: BaseTenantViewSet usa lookup_field="uuid", pero el frontend envía IDs numéricos
        - GET /api/v1/contabilidad/cuentas-contables/{id}/render-offcanvas/editar/ → Modo edición
        
        Returns:
            Template HTML: tenant/core/contabilidad/partials/cuenta_offcanvas_form.html
        """
        try:
            # ⚠️ v2.61: BaseTenantViewSet usa lookup_field="uuid", pero el frontend envía IDs numéricos
            # El router de DRF pone el valor en kwargs['uuid'] cuando lookup_field="uuid"
            cuenta_identifier = kwargs.get('uuid') or kwargs.get('pk')
            
            if not cuenta_identifier:
                from rest_framework.response import Response
                from rest_framework import status
                return Response(
                    {"detail": ["ID de cuenta no proporcionado en la URL."]},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # ⚠️ v2.61: Detectar si el identificador es numérico (pk) o UUID
            try:
                # Intentar convertir a entero (es un ID numérico)
                cuenta_id = int(cuenta_identifier)
                cuenta = CuentaContable.objects.get(id=cuenta_id)
            except (ValueError, TypeError):
                # No es numérico, intentar como UUID usando get_object()
                try:
                    cuenta = self.get_object()  # Esto usa lookup_field="uuid" automáticamente
                except CuentaContable.DoesNotExist:
                    from rest_framework.response import Response
                    from rest_framework import status
                    return Response(
                        {"detail": [f"Cuenta contable no encontrada con identificador: {cuenta_identifier}"]},
                        status=status.HTTP_404_NOT_FOUND
                    )
            except CuentaContable.DoesNotExist:
                from rest_framework.response import Response
                from rest_framework import status
                return Response(
                    {"detail": [f"Cuenta contable no encontrada con ID: {cuenta_identifier}"]},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            serializer = self.get_serializer(cuenta)
            context = {'cuenta': serializer.data}
            return Response(context, template_name='tenant/core/contabilidad/partials/cuenta_offcanvas_form.html')
        except Exception as e:
            import traceback
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error en render_offcanvas_editar: {e}")
            logger.error(traceback.format_exc())
            from rest_framework.response import Response
            from rest_framework import status
            return Response(
                {"detail": [f"Error al cargar cuenta: {str(e)}"]},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='render-offcanvas/detalle')
    def render_offcanvas_detalle(self, request, **kwargs):
        """
        Endpoint HTMX RESTful para cargar offcanvas de detalle de cuentas contables (read-only).
        
        ⚠️ v2.60: Feature-Sliced Architecture - Template dedicado para detalle
        ⚠️ v2.61: BaseTenantViewSet usa lookup_field="uuid", pero el frontend envía IDs numéricos
        - GET /api/v1/contabilidad/cuentas-contables/{id}/render-offcanvas/detalle/ → Modo lectura
        
        Returns:
            Template HTML: tenant/core/contabilidad/partials/cuenta_offcanvas_detalle.html
        """
        try:
            # ⚠️ v2.61: BaseTenantViewSet usa lookup_field="uuid", pero el frontend envía IDs numéricos
            # El router de DRF pone el valor en kwargs['uuid'] cuando lookup_field="uuid"
            cuenta_identifier = kwargs.get('uuid') or kwargs.get('pk')
            
            if not cuenta_identifier:
                context = {
                    'cuenta': None,
                    'error': 'ID de cuenta no proporcionado en la URL.'
                }
                return Response(context, template_name='tenant/core/contabilidad/partials/cuenta_offcanvas_detalle.html', status=400)
            
            # ⚠️ v2.61: Detectar si el identificador es numérico (pk) o UUID
            try:
                # Intentar convertir a entero (es un ID numérico)
                cuenta_id = int(cuenta_identifier)
                cuenta = CuentaContable.objects.get(id=cuenta_id)
            except (ValueError, TypeError):
                # No es numérico, intentar como UUID usando get_object()
                try:
                    cuenta = self.get_object()  # Esto usa lookup_field="uuid" automáticamente
                except CuentaContable.DoesNotExist:
                    context = {
                        'cuenta': None,
                        'error': f'Cuenta contable no encontrada con identificador: {cuenta_identifier}'
                    }
                    return Response(context, template_name='tenant/core/contabilidad/partials/cuenta_offcanvas_detalle.html', status=404)
            except CuentaContable.DoesNotExist:
                context = {
                    'cuenta': None,
                    'error': f'Cuenta contable no encontrada con ID: {cuenta_identifier}'
                }
                return Response(context, template_name='tenant/core/contabilidad/partials/cuenta_offcanvas_detalle.html', status=404)
            
            serializer = self.get_serializer(cuenta)
            context = {'cuenta': serializer.data}
            return Response(context, template_name='tenant/core/contabilidad/partials/cuenta_offcanvas_detalle.html')
        except Exception as e:
            # ⚠️ Manejar errores y retornar contexto con error para debugging
            import traceback
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error en render_offcanvas_detalle: {e}")
            logger.error(traceback.format_exc())
            context = {
                'cuenta': None,
                'error': f'Error al cargar cuenta: {str(e)}'
            }
            return Response(context, template_name='tenant/core/contabilidad/partials/cuenta_offcanvas_detalle.html', status=500)


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
    
    def retrieve(self, request, *args, **kwargs):
        """
        Sobrescribir retrieve para manejar tanto IDs numéricos como UUIDs.
        
        ⚠️ v2.61: BaseTenantViewSet usa lookup_field="uuid", pero el frontend envía IDs numéricos
        - GET /api/v1/contabilidad/asientos-contables/{id}/ → Retorna asiento por ID o UUID
        """
        try:
            # ⚠️ v2.61: BaseTenantViewSet usa lookup_field="uuid", pero el frontend envía IDs numéricos
            # El router de DRF pone el valor en kwargs['uuid'] cuando lookup_field="uuid"
            asiento_identifier = kwargs.get('uuid') or kwargs.get('pk')
            
            if not asiento_identifier:
                return Response(
                    {"detail": ["ID de asiento no proporcionado en la URL."]},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            asiento = None
            if asiento_identifier:
                try:
                    # Intentar convertir a entero (es un ID numérico)
                    asiento_id = int(asiento_identifier)
                    asiento = qs_asiento_detail().get(id=asiento_id)
                except (ValueError, TypeError):
                    # Si no es numérico, intentar como UUID usando get_object()
                    try:
                        asiento = self.get_object()  # Esto usa lookup_field="uuid" automáticamente
                    except AsientoContable.DoesNotExist:
                        return Response(
                            {"detail": [f"Asiento contable no encontrado con identificador: {asiento_identifier}"]},
                            status=status.HTTP_404_NOT_FOUND
                        )
                except AsientoContable.DoesNotExist:
                    return Response(
                        {"detail": [f"Asiento contable no encontrado con ID: {asiento_identifier}"]},
                        status=status.HTTP_404_NOT_FOUND
                    )
            
            if not asiento:
                return Response(
                    {"detail": [f"Asiento contable no encontrado con identificador: {asiento_identifier}"]},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            serializer = self.get_serializer(asiento)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error en retrieve: {e}")
            logger.error(traceback.format_exc())
            return Response(
                {"detail": [f"Error al obtener asiento: {str(e)}"]},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
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
        ⚠️ v2.61: BaseTenantViewSet usa lookup_field="uuid", pero el frontend envía IDs numéricos
        """
        ok, reason = self._check_enforced_mode(request)
        if not ok:
            return Response({"detail": reason}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
        
        try:
            # ⚠️ v2.61: BaseTenantViewSet usa lookup_field="uuid", pero el frontend envía IDs numéricos
            # El router de DRF pone el valor en kwargs['uuid'] cuando lookup_field="uuid"
            asiento_identifier = kwargs.get('uuid') or kwargs.get('pk')
            
            if not asiento_identifier:
                return Response(
                    {"detail": ["ID de asiento no proporcionado en la URL."]},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Convertir identificador a ID numérico para el servicio
            asiento_id = None
            if asiento_identifier:
                try:
                    # Intentar convertir a entero (es un ID numérico)
                    asiento_id = int(asiento_identifier)
                except (ValueError, TypeError):
                    # Si no es numérico, intentar como UUID y obtener el ID
                    try:
                        asiento = self.get_object()  # Esto usa lookup_field="uuid" automáticamente
                        asiento_id = asiento.id
                    except AsientoContable.DoesNotExist:
                        return Response(
                            {"detail": [f"Asiento contable no encontrado con identificador: {asiento_identifier}"]},
                            status=status.HTTP_404_NOT_FOUND
                        )
            
            if not asiento_id:
                return Response(
                    {"detail": [f"Asiento contable no encontrado con identificador: {asiento_identifier}"]},
                    status=status.HTTP_404_NOT_FOUND
                )
            
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
        # ⚠️ v2.61: Importación local para evitar circular import
        from apps.tenant.contabilidad.services import get_balance_prueba
        
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
            Template HTML: tenant/core/contabilidad/partials/asiento_offcanvas_form.html
        """
        context = {'asiento': None}
        return Response(context, template_name='tenant/core/contabilidad/partials/asiento_offcanvas_form.html')
    
    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='render-offcanvas/cargar-desde-documentos')
    def render_offcanvas_cargar_desde_documentos(self, request):
        """
        Endpoint HTMX RESTful para cargar offcanvas de selección de documentos.
        
        ⚠️ v2.60 Fase 3: Asistente de Selección - Lista Facturas y Gastos sin asiento
        
        Returns:
            Template HTML: tenant/core/contabilidad/partials/asiento_offcanvas_cargar_desde_docs.html
        """
        context = {}
        return Response(context, template_name='tenant/core/contabilidad/partials/asiento_offcanvas_cargar_desde_docs.html')
    
    @action(detail=True, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='render-offcanvas/editar')
    def render_offcanvas_editar(self, request, **kwargs):
        """
        Endpoint HTMX RESTful para cargar offcanvas de edición de asientos contables.
        
        ⚠️ v2.61: Feature-Sliced Architecture - Template dedicado EXCLUSIVAMENTE para edición
        ⚠️ v2.61: BaseTenantViewSet usa lookup_field="uuid", pero el frontend envía IDs numéricos
        - GET /api/v1/contabilidad/asientos-contables/{id}/render-offcanvas/editar/ → Modo edición
        
        Returns:
            Template HTML: tenant/core/contabilidad/partials/asiento_offcanvas_editar.html
        """
        try:
            # ⚠️ v2.61: BaseTenantViewSet usa lookup_field="uuid", pero el frontend envía IDs numéricos
            # El router de DRF pone el valor en kwargs['uuid'] cuando lookup_field="uuid"
            asiento_identifier = kwargs.get('uuid') or kwargs.get('pk')
            
            if not asiento_identifier:
                return Response(
                    {"detail": ["ID de asiento no proporcionado en la URL."]},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            asiento = None
            if asiento_identifier:
                try:
                    # Intentar convertir a entero (es un ID numérico)
                    asiento_id = int(asiento_identifier)
                    asiento = AsientoContable.objects.get(id=asiento_id)
                except (ValueError, TypeError):
                    # Si no es numérico, intentar como UUID usando get_object()
                    try:
                        asiento = self.get_object()  # Esto usa lookup_field="uuid" automáticamente
                    except AsientoContable.DoesNotExist:
                        return Response(
                            {"detail": [f"Asiento contable no encontrado con identificador: {asiento_identifier}"]},
                            status=status.HTTP_404_NOT_FOUND
                        )
                except AsientoContable.DoesNotExist:
                    return Response(
                        {"detail": [f"Asiento contable no encontrado con ID: {asiento_identifier}"]},
                        status=status.HTTP_404_NOT_FOUND
                    )
            
            if not asiento:
                return Response(
                    {"detail": [f"Asiento contable no encontrado con identificador: {asiento_identifier}"]},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            serializer = AsientoContableDetailSerializer(asiento, context={'request': request})
            context = {'asiento': serializer.data}
            return Response(context, template_name='tenant/core/contabilidad/partials/asiento_offcanvas_editar.html')
        except Exception as e:
            logger.error(f"Error en render_offcanvas_editar: {e}")
            logger.error(traceback.format_exc())
            return Response(
                {"detail": [f"Error al cargar asiento: {str(e)}"]},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
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
        - id: ID del asiento (requerido, puede ser numérico o UUID)
        
        Returns:
            Template HTML: tenant/core/contabilidad/partials/asiento_offcanvas_detalle.html
        """
        from apps.tenant.contabilidad.services import qs_asiento_detail
        
        asiento_id = request.query_params.get('id')
        context = {}
        
        if not asiento_id:
            context['error'] = "Se requiere el parámetro 'id' para el modo detalle."
            return Response(context, template_name='tenant/core/contabilidad/partials/asiento_offcanvas_detalle.html')
        
        try:
            # ⚠️ v2.61: Intentar obtener por ID numérico primero, luego por UUID
            asiento = None
            try:
                # Intentar como ID numérico
                asiento_id_int = int(asiento_id)
                asiento = qs_asiento_detail().get(id=asiento_id_int)
            except (ValueError, TypeError):
                # Si no es numérico, intentar como UUID
                try:
                    asiento = qs_asiento_detail().get(uuid=asiento_id)
                except (ValueError, TypeError):
                    # Si tampoco es UUID válido, intentar con get_object() que usa lookup_field
                    try:
                        # Temporalmente cambiar lookup_field para este caso
                        original_lookup = self.lookup_field
                        self.lookup_field = 'uuid'
                        self.kwargs['uuid'] = asiento_id
                        asiento = self.get_object()
                        self.lookup_field = original_lookup
                        if 'uuid' in self.kwargs:
                            del self.kwargs['uuid']
                    except Exception:
                        pass
            
            if not asiento:
                raise AsientoContable.DoesNotExist(f"Asiento contable con identificador '{asiento_id}' no encontrado.")
            
            # Usar el serializer de detalle para obtener movimientos
            serializer = AsientoContableDetailSerializer(asiento, context={'request': request})
            context['asiento'] = serializer.data
        except AsientoContable.DoesNotExist as e:
            context['error'] = str(e)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error en render_offcanvas_detalle: {e}", exc_info=True)
            context['error'] = f"Error al cargar asiento: {str(e)}"
        
        return Response(context, template_name='tenant/core/contabilidad/partials/asiento_offcanvas_detalle.html')


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


class CatalogoMaestroNIIFViewSet(BaseTenantViewSet):
    """
    ViewSet para CatalogoMaestroNIIF (Catálogo oficial NIIF Colombia).
    
    ⚠️ v2.61: Catálogo Maestro NIIF Colombia (SSoT).
    ⚠️ POLÍTICA: Solo lectura para usuarios normales. Solo ADMIN puede crear/editar.
    ⚠️ AUTO-SETEO: Al crear, solo se requiere el campo 'codigo'. Los demás campos se auto-completan.
    
    Endpoints:
    - GET /api/v1/core/v1/contabilidad/catalogo-niif/ - Listado del catálogo
    - GET /api/v1/core/v1/contabilidad/catalogo-niif/{id}/ - Detalle de cuenta del catálogo
    - POST /api/v1/core/v1/contabilidad/catalogo-niif/ - Crear cuenta (solo ADMIN)
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsTenantAdminOrReadOnly]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['nivel', 'naturaleza', 'activa']
    search_fields = ['codigo', 'nombre']
    ordering_fields = ['codigo', 'nombre', 'nivel']
    ordering = ['codigo']
    
    def get_serializer_class(self):
        """Selecciona el serializer según la acción."""
        if self.action == "retrieve":
            return CatalogoMaestroNIIFDetailSerializer
        return CatalogoMaestroNIIFListSerializer
    
    def get_queryset(self):
        """
        QuerySet optimizado para el catálogo NIIF.
        
        ⚠️ v2.61: El catálogo es compartido por todos los tenants (cada tenant tiene su copia).
        """
        if self.action == "list" or self.action == "buscar_por_tipo":
            # Campos mínimos para LIST y buscar_por_tipo
            return CatalogoMaestroNIIF.objects.only(
                'id', 'codigo', 'nombre', 'nivel', 'naturaleza', 'activa'
            ).order_by('codigo')
        elif self.action == "retrieve":
            # Campos completos para RETRIEVE con prefetch de cuentas vinculadas
            return CatalogoMaestroNIIF.objects.prefetch_related('cuentas_vinculadas')
        else:
            # Para create/update/delete necesitamos todos los campos
            return CatalogoMaestroNIIF.objects.all()
    
    def create(self, request, *args, **kwargs):
        """
        Crea una nueva cuenta en el catálogo NIIF.
        
        ⚠️ AUTO-SETEO: Solo se requiere el campo 'codigo'.
        Los campos nombre, nivel y naturaleza se auto-completan desde CATALOGO_NIIF_COLOMBIA.
        
        Body:
        {
            "codigo": "1110"  // Solo se requiere el código
        }
        
        Response:
        {
            "id": 1,
            "codigo": "1110",
            "nombre": "BANCOS",  // Auto-seteado
            "nivel": 4,  // Auto-seteado
            "naturaleza": "D",  // Auto-seteado
            "tipo_cuenta": "ACTIVO",
            "activa": true
        }
        """
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            # El método save() del modelo se encarga del auto-seteo
            self.perform_create(serializer)
            
            headers = self.get_success_headers(serializer.data)
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED,
                headers=headers
            )
        except ValueError as e:
            # Error de validación del catálogo (código no existe en CATALOGO_NIIF_COLOMBIA)
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'], url_path='por-nivel/(?P<nivel>[0-9]+)')
    def por_nivel(self, request, nivel=None):
        """
        Filtra cuentas del catálogo por nivel.
        
        GET /api/v1/core/v1/contabilidad/catalogo-niif/por-nivel/1/  - Nivel 1 (Clases)
        GET /api/v1/core/v1/contabilidad/catalogo-niif/por-nivel/2/  - Nivel 2 (Grupos)
        GET /api/v1/core/v1/contabilidad/catalogo-niif/por-nivel/4/  - Nivel 4 (Cuentas)
        GET /api/v1/core/v1/contabilidad/catalogo-niif/por-nivel/6/  - Nivel 6 (Subcuentas)
        """
        queryset = self.get_queryset().filter(nivel=int(nivel))
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='buscar-por-tipo')
    def buscar_por_tipo(self, request):
        """
        Busca cuentas del catálogo NIIF filtradas por tipo de cuenta.
        
        ⚠️ v2.61: Búsqueda directa en CATALOGO_NIIF_COLOMBIA (choices.py)
        No busca en la base de datos, busca directamente en el catálogo estático.
        
        Query params:
        - tipo: ACTIVO, PASIVO, PATRIMONIO, INGRESO, GASTO, COSTO
        - search: Búsqueda por código (número) o nombre (letras) - opcional
        - nivel: Filtro por nivel (opcional)
        
        GET /api/v1/contabilidad/catalogo-niif/buscar-por-tipo/?tipo=ACTIVO
        GET /api/v1/contabilidad/catalogo-niif/buscar-por-tipo/?tipo=ACTIVO&search=banco
        GET /api/v1/contabilidad/catalogo-niif/buscar-por-tipo/?tipo=ACTIVO&nivel=4
        """
        from apps.tenant.contabilidad.choices.choices import CATALOGO_NIIF_COLOMBIA
        
        tipo = request.query_params.get('tipo', None)
        search = request.query_params.get('search', '').strip()
        nivel = request.query_params.get('nivel', None)
        
        if not tipo:
            return Response(
                {'error': 'El parámetro "tipo" es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Mapeo de tipo a primer dígito del código
        tipo_map = {
            'ACTIVO': '1',
            'PASIVO': '2',
            'PATRIMONIO': '3',
            'INGRESO': '4',
            'GASTO': '5',
            'COSTO': '6',
        }
        
        primer_digito = tipo_map.get(tipo.upper())
        if not primer_digito:
            return Response(
                {'error': f'Tipo inválido: {tipo}. Valores permitidos: ACTIVO, PASIVO, PATRIMONIO, INGRESO, GASTO, COSTO'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # ⚠️ v2.61: Buscar directamente en CATALOGO_NIIF_COLOMBIA (choices.py)
        # Estructura: (codigo, nombre, nivel, naturaleza)
        resultados = []
        
        for codigo, nombre, nivel_cuenta, naturaleza in CATALOGO_NIIF_COLOMBIA:
            # Filtrar por primer dígito del código (tipo)
            if not codigo.startswith(primer_digito):
                continue
            
            # Filtrar por nivel si se proporciona
            if nivel and nivel_cuenta != int(nivel):
                continue
            
            # ⚠️ v2.61: Búsqueda por código (número) o nombre (letras)
            if search:
                search_lower = search.lower()
                codigo_match = search_lower in codigo.lower()
                nombre_match = search_lower in nombre.lower()
                if not (codigo_match or nombre_match):
                    continue
            
            # Agregar resultado
            resultados.append({
                'id': None,  # No tiene ID en el catálogo estático
                'codigo': codigo,
                'nombre': nombre,
                'nivel': nivel_cuenta,
                'naturaleza': naturaleza,
                'activa': True,  # Todas las cuentas del catálogo están activas
                'tipo_cuenta': tipo.upper()  # Tipo calculado
            })
        
        # Ordenar por código
        resultados.sort(key=lambda x: x['codigo'])
        
        # ⚠️ DEBUG: Log para depuración
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f'[Catálogo NIIF] Búsqueda en choices.py: tipo={tipo}, search={search}, nivel={nivel}, total={len(resultados)}')
        
        # Paginar resultados manualmente
        try:
            page_size = int(request.query_params.get('page_size', 20))
        except (ValueError, TypeError):
            page_size = 20
        
        try:
            page = int(request.query_params.get('page', 1))
        except (ValueError, TypeError):
            page = 1
        
        # Calcular paginación
        total = len(resultados)
        start = (page - 1) * page_size
        end = start + page_size
        resultados_paginados = resultados[start:end]
        
        # Construir URLs de paginación
        base_url = request.build_absolute_uri().split('?')[0]  # URL sin query params
        query_params = request.query_params.copy()
        
        next_url = None
        if end < total:
            query_params['page'] = page + 1
            next_url = f"{base_url}?{query_params.urlencode()}"
        
        previous_url = None
        if page > 1:
            query_params['page'] = page - 1
            previous_url = f"{base_url}?{query_params.urlencode()}"
        
        # Retornar respuesta paginada (formato DRF estándar)
        return Response({
            'count': total,
            'next': next_url,
            'previous': previous_url,
            'results': resultados_paginados
        }, status=status.HTTP_200_OK)


class PeriodoContableViewSet(BaseTenantViewSet):
    """
    ViewSet para PeriodoContable.
    
    ⚠️ v2.40: ENFORCED MODE - POST/PATCH/PUT/DELETE solo para STAFF/ADMIN.
    ⚠️ v2.61: Usa qs_periodo_list() y qs_periodo_detail() del service.
    ⚠️ OPTIMIZACIÓN: NO usa .all(), usa only() para reducir SELECT.
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsTenantAdminOrReadOnly]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['estado', 'periodo']
    search_fields = ['periodo', 'observaciones']
    ordering_fields = ['periodo', 'fecha_inicio', 'fecha_fin', 'created_at']
    ordering = ['-periodo']
    
    def get_serializer_class(self):
        """Selecciona el serializer según la acción."""
        if self.action in ["retrieve", "render_offcanvas_editar", "render_offcanvas_detalle"]:
            return PeriodoContableDetailSerializer
        return PeriodoContableListSerializer
    
    def get_queryset(self):
        """
        QuerySet optimizado usando qs_periodo_list() y qs_periodo_detail() del service.
        
        ⚠️ v2.61: Alineado con Service Layer Pattern.
        """
        if self.action == "list":
            return qs_periodo_list().order_by('-periodo')
        elif self.action == "retrieve":
            return qs_periodo_detail()
        else:
            return PeriodoContable.objects.all()
    
    @action(detail=False, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='render-offcanvas/crear')
    def render_offcanvas_crear(self, request):
        """
        Endpoint HTMX RESTful para cargar offcanvas de creación de periodos contables.
        
        ⚠️ v2.61: Feature-Sliced Architecture - Template dedicado para creación
        - GET /api/v1/contabilidad/periodos-contables/render-offcanvas/crear/ → Modo creación
        
        Returns:
            Template HTML: tenant/core/contabilidad/partials/periodo_offcanvas_form.html
        """
        context = {}
        return Response(context, template_name='tenant/core/contabilidad/partials/periodo_offcanvas_form.html')
    
    @action(detail=True, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='render-offcanvas/editar')
    def render_offcanvas_editar(self, request, **kwargs):
        """
        Endpoint HTMX RESTful para cargar offcanvas de edición de periodos contables.
        
        ⚠️ v2.61: Feature-Sliced Architecture - Template dedicado para edición
        - GET /api/v1/contabilidad/periodos-contables/{id}/render-offcanvas/editar/ → Modo edición
        
        Returns:
            Template HTML: tenant/core/contabilidad/partials/periodo_offcanvas_form.html
        """
        try:
            periodo_identifier = kwargs.get('uuid') or kwargs.get('pk')
            periodo = None
            if periodo_identifier:
                try:
                    periodo_id = int(periodo_identifier)
                    periodo = PeriodoContable.objects.get(id=periodo_id)
                except (ValueError, TypeError):
                    try:
                        periodo = self.get_object()
                    except PeriodoContable.DoesNotExist:
                        pass
            
            if not periodo:
                raise PeriodoContable.DoesNotExist(f"Periodo contable con identificador '{periodo_identifier}' no encontrado.")
            
            serializer = self.get_serializer(periodo)
            context = {'periodo': serializer.data}
            return Response(context, template_name='tenant/core/contabilidad/partials/periodo_offcanvas_form.html')
        except PeriodoContable.DoesNotExist as e:
            logger.error(f"Error en render_offcanvas_editar: {e}")
            context = {
                'error': str(e),
                'message': _('El periodo contable solicitado no existe o no está disponible.'),
                'periodo': None
            }
            return Response(context, template_name='tenant/core/contabilidad/partials/periodo_offcanvas_form.html', status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error inesperado en render_offcanvas_editar: {e}", exc_info=True)
            context = {
                'error': str(e),
                'message': _('Ocurrió un error inesperado al cargar el formulario de edición.'),
                'periodo': None
            }
            return Response(context, template_name='tenant/core/contabilidad/partials/periodo_offcanvas_form.html', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'], renderer_classes=[TemplateHTMLRenderer], url_path='render-offcanvas/detalle')
    def render_offcanvas_detalle(self, request, **kwargs):
        """
        Endpoint HTMX RESTful para cargar offcanvas de detalle de periodos contables (read-only).
        
        ⚠️ v2.61: Feature-Sliced Architecture - Template dedicado para detalle
        - GET /api/v1/contabilidad/periodos-contables/{id}/render-offcanvas/detalle/ → Modo lectura
        
        Returns:
            Template HTML: tenant/core/contabilidad/partials/periodo_offcanvas_detalle.html
        """
        try:
            periodo_identifier = kwargs.get('uuid') or kwargs.get('pk')
            periodo = None
            if periodo_identifier:
                try:
                    periodo_id = int(periodo_identifier)
                    periodo = PeriodoContable.objects.get(id=periodo_id)
                except (ValueError, TypeError):
                    try:
                        periodo = self.get_object()
                    except PeriodoContable.DoesNotExist:
                        pass
            
            if not periodo:
                raise PeriodoContable.DoesNotExist(f"Periodo contable con identificador '{periodo_identifier}' no encontrado.")
            
            serializer = self.get_serializer(periodo)
            context = {'periodo': serializer.data}
            return Response(context, template_name='tenant/core/contabilidad/partials/periodo_offcanvas_detalle.html')
        except PeriodoContable.DoesNotExist as e:
            logger.error(f"Error en render_offcanvas_detalle: {e}")
            context = {
                'error': str(e),
                'message': _('El periodo contable solicitado no existe o no está disponible.'),
                'periodo': None
            }
            return Response(context, template_name='tenant/core/contabilidad/partials/periodo_offcanvas_detalle.html', status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error inesperado en render_offcanvas_detalle: {e}", exc_info=True)
            context = {
                'error': str(e),
                'message': _('Ocurrió un error inesperado al cargar el detalle del periodo contable.'),
                'periodo': None
            }
            return Response(context, template_name='tenant/core/contabilidad/partials/periodo_offcanvas_detalle.html', status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Lista de ViewSets para registro automático en el router
VIEWSETS = [
    (r'cuentas-contables', CuentaContableViewSet, 'cuenta-contable'),
    (r'asientos-contables', AsientoContableViewSet, 'asiento-contable'),
    (r'movimientos-contables', MovimientoContableViewSet, 'movimiento-contable'),
    (r'periodos-contables', PeriodoContableViewSet, 'periodo-contable'),  # ⚠️ v2.61
    (r'catalogo-niif', CatalogoMaestroNIIFViewSet, 'catalogo-niif'),
]
