"""
Vistas DRF para el dashboard de tenants (API-First).

WARNING: v2.30: Migración completa a API-first.
Todas las vistas que renderizan HTML han sido eliminadas.
"""
import logging

from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from apps.tenant.api.permissions import IsTenantMember
from apps.tenant.dashboard.services import (
    get_dashboard_context,
    get_dashboard_redirect_url,
    get_user_role_in_tenant,
)

from .permissions import IsUserOrHigher
from .serializers import (
    DashboardPayload,
    DashboardSummarySerializer,
    KPISerializer,
    QuickActionSerializer,
)

logger = logging.getLogger(__name__)


class DashboardThrottle(UserRateThrottle):
    """
    Throttling para endpoints del dashboard.
    
    Límite: 100 requests/minuto por usuario.
    """
    rate = '100/min'


class DashboardDataAPIView(APIView):
    """
    Endpoint principal para obtener datos del dashboard (contrato estandarizado).
    
    GET /api/v1/dashboard/data/
    
    Retorna un payload completo con header, KPIs, series y tabla.
    Proporciona valores por defecto seguros si no hay datos del dominio.
    
    Permisos: Requiere autenticación.
    Throttling: 100 requests/minuto por usuario.
    Autenticación: SessionAuthentication (usa cookies de sesión).
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsTenantMember]
    throttle_classes = [DashboardThrottle]
    
    def get(self, request):
        """
        Retorna datos del dashboard con valores por defecto seguros.
        
        WARNING: API-First: No asume acoplamiento con DB.
        Proporciona datos mínimos válidos incluso si no hay datos del tenant.
        """
        tenant = getattr(request, 'tenant', None)
        user = request.user
        
        # Valores por defecto seguros
        default_data = {
            "header": {
                "title": "Dashboard",
                "subtitle": "Resumen del tenant"
            },
            "kpis": [
                {"label": "Ventas (mes)", "value": 0.0, "delta": None},
                {"label": "Clientes activos", "value": 0.0, "delta": None},
                {"label": "Facturas pendientes", "value": 0.0, "delta": None},
            ],
            "series": [
                {
                    "name": "Ventas",
                    "points": [
                        {"x": "Sem1", "y": 0.0},
                        {"x": "Sem2", "y": 0.0}
                    ]
                }
            ],
            "table": {
                "columns": ["ID", "Nombre", "Monto", "Estado"],
                "rows": []
            }
        }
        
        # Intentar obtener datos reales del tenant si existe
        if tenant and user.is_authenticated:
            try:
                # Obtener contexto del dashboard (puede retornar datos reales o vacíos)
                dashboard_data = get_dashboard_context(user, tenant)
                
                # Mapear datos del servicio a el contrato estandarizado
                if dashboard_data:
                    # KPIs desde el servicio
                    kpis = []
                    if 'total_facturas' in dashboard_data:
                        kpis.append({
                            "label": "Total Facturas",
                            "value": float(dashboard_data.get('total_facturas', 0)),
                            "delta": None
                        })
                    if 'facturas_pendientes' in dashboard_data:
                        kpis.append({
                            "label": "Facturas Pendientes",
                            "value": float(dashboard_data.get('facturas_pendientes', 0)),
                            "delta": None
                        })
                    if 'total_clientes' in dashboard_data:
                        kpis.append({
                            "label": "Clientes Activos",
                            "value": float(dashboard_data.get('total_clientes', 0)),
                            "delta": None
                        })
                    if 'ingresos_mes' in dashboard_data:
                        ingresos = dashboard_data.get('ingresos_mes', 0)
                        kpis.append({
                            "label": "Ingresos (mes)",
                            "value": float(ingresos) if ingresos else 0.0,
                            "delta": None
                        })
                    
                    # Si hay KPIs reales, usarlos; si no, mantener defaults
                    if kpis:
                        default_data["kpis"] = kpis[:3]  # Máximo 3 KPIs
                
                # Header con información del tenant
                if hasattr(tenant, 'nombre'):
                    default_data["header"]["title"] = f"Dashboard - {tenant.nombre}"
                    default_data["header"]["subtitle"] = f"Resumen de {tenant.nombre}"
                
            except Exception as e:
                logger.warning(
                    "DashboardDataAPIView: Error obteniendo datos del tenant, usando defaults: %s",
                    str(e)
                )
                # Continuar con valores por defecto
        
        # Serializar y retornar
        serializer = DashboardPayload(default_data)
        return Response(serializer.data, status=status.HTTP_200_OK)


# Vistas legacy (mantener por compatibilidad)
class DashboardSummaryAPIView(APIView):
    """
    Endpoint para obtener el resumen completo del dashboard (legacy).
    
    GET /api/v1/dashboard/summary/
    
    WARNING: DEPRECADO: Usar DashboardDataAPIView en su lugar.
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsUserOrHigher]
    throttle_classes = [DashboardThrottle]
    
    def get(self, request, *args, **kwargs):
        tenant = getattr(request, 'tenant', None)
        user = request.user
        
        if not user.is_authenticated:
            return Response(
                {"detail": "Autenticación requerida. Por favor, inicia sesión."},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        if not tenant:
            return Response(
                {"detail": "No se pudo determinar el tenant actual."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user_role = get_user_role_in_tenant(user, tenant)
            dashboard_data = get_dashboard_context(user, tenant)
            redirect_url = get_dashboard_redirect_url(user, tenant, absolute=False)
            
            from apps.tenant.core.branding import get_tenant_branding
            branding = get_tenant_branding(request)
            
            data = {
                "tenant": {
                    "id": tenant.id,
                    "nombre": tenant.nombre if hasattr(tenant, 'nombre') else 'Tenant',
                    "schema_name": tenant.schema_name if hasattr(tenant, 'schema_name') else None,
                },
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "name": user.get_full_name() or user.email,
                },
                "user_role": user_role,
                "kpis": dashboard_data,
                "redirect_url": redirect_url or '/dashboard/',
                "branding": branding,
            }
            
            serializer = DashboardSummarySerializer(data)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(
                "DashboardSummaryAPIView: error cargando resumen: %s",
                str(e),
                exc_info=True
            )
            return Response(
                {"detail": "Error interno al cargar el resumen del dashboard."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DashboardKPIsAPIView(APIView):
    """
    Endpoint para obtener KPIs del dashboard (legacy).
    
    GET /api/v1/dashboard/kpis/
    
    WARNING: DEPRECADO: Usar DashboardDataAPIView en su lugar.
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsUserOrHigher]
    throttle_classes = [DashboardThrottle]
    
    def get(self, request, *args, **kwargs):
        tenant = getattr(request, 'tenant', None)
        user = request.user
        
        if not tenant:
            return Response(
                {"detail": "No se pudo determinar el tenant actual."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            dashboard_data = get_dashboard_context(user, tenant)
            serializer = KPISerializer(dashboard_data)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(
                "DashboardKPIsAPIView: error cargando KPIs: %s",
                str(e),
                exc_info=True
            )
            return Response(
                {"detail": "Error interno al cargar los KPIs del dashboard."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DashboardQuickActionsAPIView(APIView):
    """
    Endpoint para obtener acciones rápidas del dashboard según el rol (legacy).
    
    GET /api/v1/dashboard/quick-actions/
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsUserOrHigher]
    throttle_classes = [DashboardThrottle]
    
    def get(self, request, *args, **kwargs):
        tenant = getattr(request, 'tenant', None)
        user = request.user
        
        if not user.is_authenticated:
            return Response(
                {"detail": "Autenticación requerida. Por favor, inicia sesión."},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        if not tenant:
            return Response(
                {"detail": "No se pudo determinar el tenant actual."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user_role = get_user_role_in_tenant(user, tenant)
            
            actions = [
                {
                    "id": "view_empresas",
                    "label": "Ver Empresas",
                    "url": "/empresa/",
                    "icon": "fa-building",
                    "color": "indigo",
                    "required_role": "USER",
                },
                {
                    "id": "view_facturas",
                    "label": "Ver Facturas",
                    "url": "/api/v1/facturas/",
                    "icon": "fa-file-invoice",
                    "color": "blue",
                    "required_role": "USER",
                },
                {
                    "id": "view_contabilidad",
                    "label": "Ver Contabilidad",
                    "url": "/api/v1/contabilidad/",
                    "icon": "fa-book",
                    "color": "green",
                    "required_role": "USER",
                },
            ]
            
            if user_role in ('STAFF', 'ADMIN'):
                actions.append({
                    "id": "new_factura",
                    "label": "Nueva Factura",
                    "url": "/api/v1/facturas/",
                    "icon": "fa-plus-circle",
                    "color": "blue",
                    "required_role": "STAFF",
                })
            
            if user_role == 'ADMIN':
                actions.append({
                    "id": "config_empresa",
                    "label": "Configurar Empresa",
                    "url": "/empresa/",
                    "icon": "fa-cog",
                    "color": "purple",
                    "required_role": "ADMIN",
                })
            
            role_priority = {'ADMIN': 3, 'STAFF': 2, 'USER': 1}
            user_priority = role_priority.get(user_role, 0)
            
            filtered_actions = []
            for action in actions:
                required_role = action.get('required_role', 'USER')
                required_priority = role_priority.get(required_role, 0)
                if user_priority >= required_priority:
                    filtered_actions.append(action)
            
            serializer = QuickActionSerializer(filtered_actions, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(
                "DashboardQuickActionsAPIView: error cargando acciones: %s",
                str(e),
                exc_info=True
            )
            return Response(
                {"detail": "Error interno al cargar las acciones rápidas del dashboard."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
