"""
ViewSets para Core API.

⚠️ POLÍTICA:
- Endpoints de composición/orquestación para presentación
- NO reemplazan CRUD de las apps individuales
- Mantienen tenant-awareness y branding dinámico
"""
import logging
from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from rest_framework.authentication import SessionAuthentication
from apps.tenant.dashboard.api.permissions import IsUserOrHigher
from apps.tenant.core.services.empresa import get_empresas_snapshot
from apps.tenant.core.services.facturas import get_facturas_snapshot
from apps.tenant.core.services.contabilidad import get_contabilidad_snapshot
from apps.tenant.core.services.perfil import get_perfil_snapshot
from apps.tenant.core.services.landing import get_landing_snapshot
# ⚠️ v2.61: Comentado - serializers_sections no existe
# from apps.tenant.core.api.serializers_sections import DashboardSectionsSerializer

logger = logging.getLogger(__name__)


class CoreLinksViewSet(ViewSet):
    """
    Link Registry para Core API.
    
    Proporciona un registro centralizado de todas las rutas API y UI de TENANT_APPS.
    
    GET /api/v1/core/links/
    
    Retorna un JSON con rutas relativas (sin dominio) para cada módulo:
    {
      "empresa": {
        "api": "/api/v1/empresas/",
        "ui": "/dashboard/empresa/"
      },
      "facturas": {
        "api": "/api/v1/facturas/",
        "ui": "/dashboard/facturas/"
      },
      ...
    }
    
    ⚠️ POLÍTICA:
    - URLs siempre relativas (sin dominio)
    - No hardcodes de rutas en el frontend
    - Centralizado en Core API para fácil mantenimiento
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsUserOrHigher]
    
    def list(self, request):
        """
        Retorna el registro de links para todas las TENANT_APPS.
        
        GET /api/v1/core/links/
        """
        tenant = getattr(request, 'tenant', None)
        
        if not tenant:
            return Response(
                {"detail": "No se pudo determinar el tenant actual."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # ⚠️ POLÍTICA: URLs siempre relativas (sin dominio)
            # El frontend construye URLs absolutas usando window.location.origin si es necesario
            links = {
                "empresa": {
                    "api": "/api/v1/empresas/",
                    "ui": "/dashboard/empresa/",  # Placeholder para UI futura
                },
                "facturas": {
                    "api": "/api/v1/facturas/",
                    "ui": "/dashboard/facturas/",  # Placeholder para UI futura
                },
                "contabilidad": {
                    "api": "/api/v1/core/v1/contabilidad/asientos/",  # Endpoint principal de contabilidad (facade)
                    "ui": "/dashboard/contabilidad/",  # Placeholder para UI futura
                },
                "cuentas-contables": {
                    "api": "/api/v1/core/v1/contabilidad/cuentas/",  # Facade
                    "ui": "/dashboard/contabilidad/cuentas/",  # Placeholder para UI futura
                },
                "asientos-contables": {
                    "api": "/api/v1/core/v1/contabilidad/asientos/",  # Facade
                    "ui": "/dashboard/contabilidad/asientos/",  # Placeholder para UI futura
                },
                "catalogo-niif": {
                    "api": "/api/v1/core/v1/contabilidad/catalogo-niif/",  # Facade
                    "ui": "/dashboard/contabilidad/catalogo-niif/",  # Placeholder para UI futura
                },
                "perfil": {
                    "api": "/api/v1/perfil/perfiles/me/",
                    "ui": "/dashboard/perfil/",  # Placeholder para UI futura
                },
                "landing": {
                    "api": "/api/v1/landing/info/",
                    "ui": "/workspace/#landing",
                },
                "dashboard": {
                    "api": "/api/v1/core/dashboard/sections/",
                    "ui": "/dashboard/",
                },
                "core": {
                    "api": "/api/v1/core/dashboard/sections/",
                    "ui": "/dashboard/",
                },
            }
            
            return Response(links, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(
                "CoreLinksViewSet: error generando links para tenant=%s, error=%s",
                tenant.schema_name if tenant else 'none',
                str(e),
                exc_info=True
            )
            return Response(
                {"detail": "Error interno al generar el registro de links."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DashboardSectionsViewSet(ViewSet):
    """
    ViewSet para secciones del dashboard (Core API).
    
    GET /api/v1/core/dashboard/sections/
    
    Retorna las secciones en orden requerido:
    - empresas → facturas → contabilidad → perfil
    
    ⚠️ POLÍTICA:
    - Orquestación de datos de múltiples TENANT_APPS
    - NO duplica lógica de negocio (usa servicios de cada app)
    - Mantiene tenant-awareness (django-tenants maneja el aislamiento)
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsUserOrHigher]
    
    def list(self, request):
        """
        Retorna todas las secciones del dashboard en orden.
        
        GET /api/v1/core/dashboard/sections/
        
        Orden: empresas → facturas → contabilidad → perfil
        """
        tenant = getattr(request, 'tenant', None)
        user = request.user
        
        if not tenant:
            return Response(
                {"detail": "No se pudo determinar el tenant actual."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # ⚠️ ORDEN REQUERIDO: empresas → facturas → contabilidad → perfil
            # Obtener datos de cada servicio
            empresas_data = get_empresas_snapshot(tenant)
            facturas_data = get_facturas_snapshot(tenant, user)
            contabilidad_data = get_contabilidad_snapshot(tenant, user)
            perfil_data = get_perfil_snapshot(user)
            
            # Construir URLs absolutas para logos si es necesario
            # (Los servicios retornan URLs relativas, aquí las convertimos si hay request)
            if empresas_data and empresas_data[0].get('logo'):
                logo_url = empresas_data[0]['logo']
                if logo_url and not logo_url.startswith('http'):
                    # Construir URL absoluta usando el request
                    empresas_data[0]['logo'] = request.build_absolute_uri(logo_url)
            
            # ⚠️ POLÍTICA API-First: Incluir información de usuario, tenant y KPIs
            # para que el shell estático consuma EXCLUSIVAMENTE Core API
            from apps.tenant.dashboard.services import get_user_role_in_tenant
            from apps.tenant.core.branding import get_tenant_branding
            
            user_role = get_user_role_in_tenant(user, tenant)
            branding = get_tenant_branding(request)
            
            # Calcular KPIs básicos desde facturas_data
            kpis = {
                'total_facturas': facturas_data.get('total', 0),
                'facturas_pendientes': next(
                    (e['cantidad'] for e in facturas_data.get('por_estado', []) if e.get('estado') == 'PENDIENTE'),
                    0
                ),
                'total_clientes': 0,  # TODO: Agregar cuando haya modelo de clientes
                'ingresos_mes': facturas_data.get('mes_actual', {}).get('total', 0.0),
            }
            
            data = {
                # Información de usuario y tenant (para header/branding)
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "name": user.get_full_name() or user.email,
                    "role": user_role,
                },
                "tenant": {
                    "id": tenant.id,
                    "nombre": getattr(tenant, 'nombre', 'Tenant'),
                    "schema_name": getattr(tenant, 'schema_name', None),
                },
                "branding": branding,
                "kpis": kpis,
                
                # Secciones en orden requerido
                "empresas": {
                    "empresas": empresas_data
                },
                "facturas": facturas_data,
                "contabilidad": contabilidad_data,
                "perfil": {
                    "me": perfil_data
                },
            }
            
            # ⚠️ v2.61: Retornar datos directamente sin serializer (serializers_sections no existe)
            return Response(data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(
                "DashboardSectionsViewSet: error generando secciones para tenant=%s, user=%s, error=%s",
                tenant.schema_name if tenant else 'none',
                user.email if user.is_authenticated else 'anonymous',
                str(e),
                exc_info=True
            )
            return Response(
                {"detail": "Error interno al generar las secciones del dashboard."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
