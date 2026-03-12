"""
ViewSets para Core API v2.61.2.

⚠️ POLÍTICA:
- Endpoints de composición/orquestación para presentación
- NO reemplazan CRUD de las apps individuales
- Mantienen tenant-awareness y branding dinámico

⚠️ CRUD MODULARIZADO POR FUNCIÓN:
Cada ViewSet documenta claramente las funciones CRUD disponibles:
- READ (GET): list, retrieve
- CREATE (POST): create, @action personalizadas
- UPDATE (PUT/PATCH): update, partial_update
- DELETE (DELETE): destroy

⚠️ ESTRUCTURA MODULARIZADA:
┌─────────────────────────────────────────────────────────────────┐
│ CoreLinksViewSet                                                │
│ ─────────────────────────────────────────────────────────────── │
│ READ:                                                           │
│   - list() → GET /api/v1/core/links/                            │
│     Retorna registro centralizado de rutas API/UI               │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ DashboardSectionsViewSet                                        │
│ ─────────────────────────────────────────────────────────────── │
│ READ:                                                           │
│   - list() → GET /api/v1/core/dashboard/sections/               │
│     Retorna secciones del dashboard (empresas → facturas → ...) │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ CoreAuthViewSet                                                 │
│ ─────────────────────────────────────────────────────────────── │
│ CREATE:                                                         │
│   - login() → POST /api/v1/core/auth/login/                     │
│     Autentica usuario (valida TenantMembership)                 │
│   - logout() → POST /api/v1/core/auth/logout/                   │
│     Cierra sesión del usuario actual                            │
└─────────────────────────────────────────────────────────────────┘
"""
import logging
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.db import connection
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from rest_framework.authentication import SessionAuthentication
from apps.tenant.dashboard.api.permissions import IsUserOrHigher
from apps.tenant.core.services.empresa import get_empresas_snapshot
from apps.tenant.core.services.facturas import get_facturas_snapshot
from apps.tenant.core.services.contabilidad import get_contabilidad_snapshot
from apps.tenant.core.services.perfil import get_perfil_snapshot
from apps.tenant.core.services.landing import get_landing_snapshot
from apps.public.tenants.models import TenantMembership
# ⚠️ v2.61: Comentado - serializers_sections no existe
# from apps.tenant.core.api.serializers_sections import DashboardSectionsSerializer

logger = logging.getLogger(__name__)
User = get_user_model()


class CoreLinksViewSet(ViewSet):
    """
    Link Registry para Core API v2.61.2.
    
    ⚠️ CRUD MODULARIZADO:
    - READ: list() - GET /api/v1/core/links/
    
    ⚠️ FUNCIONES DISPONIBLES:
    - list(): Retorna registro centralizado de todas las rutas API y UI de TENANT_APPS
    
    Proporciona un registro centralizado de todas las rutas API y UI de TENANT_APPS.
    
    GET /api/v1/core/links/
    
    Retorna un JSON con rutas relativas (sin dominio) para cada módulo:
    {
      "empresa": {
        "api": "/api/v1/empresas/",
        "ui": "/dashboard/empresa/"
      },
            "facturas": {
                "api": "/api/v1/core/v1/facturas/facturas/",  # ⚠️ v2.61.2: Facade
                "ui": "/workspace/#facturas",  # ⚠️ v2.61.2: Workspace tab
            },
            "facturas-items": {
                "api": "/api/v1/core/v1/facturas/items-factura/",  # ⚠️ v2.61.2: Facade
                "ui": "/workspace/#facturas",
            },
            "facturas-notas-credito": {
                "api": "/api/v1/core/v1/facturas/notas-credito/",  # ⚠️ v2.61.2: Facade
                "ui": "/workspace/#facturas",
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
                    "api": "/api/v1/core/v1/facturas/facturas/",  # ⚠️ v2.61.1: Facade
                    "ui": "/workspace/#facturas",  # ⚠️ v2.61.1: Workspace tab
                },
                "facturas-items": {
                    "api": "/api/v1/core/v1/facturas/items-factura/",  # ⚠️ v2.61.1: Facade
                    "ui": "/workspace/#facturas",
                },
                "facturas-notas-credito": {
                    "api": "/api/v1/core/v1/facturas/notas-credito/",  # ⚠️ v2.61.1: Facade
                    "ui": "/workspace/#facturas",
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
                "periodos-contables": {
                    "api": "/api/v1/core/v1/contabilidad/periodos-contables/",  # Facade ⚠️ v2.61
                    "ui": "/dashboard/contabilidad/periodos/",  # Placeholder para UI futura
                },
                "catalogo-niif": {
                    "api": "/api/v1/core/v1/contabilidad/catalogo-niif/",  # Facade
                    "ui": "/dashboard/contabilidad/catalogo-niif/",  # Placeholder para UI futura
                },
                "cotizaciones": {
                    "api": "/api/v1/core/v1/cotizaciones/cotizaciones/",  # Endpoint principal de cotizaciones (facade) ⚠️ v2.61
                    "ui": "/workspace/#cotizaciones",  # UI en workspace
                },
                "cotizaciones-items": {
                    "api": "/api/v1/core/v1/cotizaciones/items/",  # Facade ⚠️ v2.61
                    "ui": "/workspace/#cotizaciones",  # UI en workspace
                },
                "cotizaciones-configuracion": {
                    "api": "/api/v1/core/v1/cotizaciones/configuracion/",  # Facade ⚠️ v2.61
                    "ui": "/workspace/#cotizaciones",  # UI en workspace
                },
                "perfil": {
                    "api": "/api/v1/perfil/perfiles/me/",
                    "ui": "/dashboard/perfil/",  # Placeholder para UI futura
                },
                "landing": {
                    "api": "/api/v1/landing/info/",
                    "ui": "/workspace/#landing",
                },
                "inventario-categorias": {
                    "api": "/api/v1/core/v1/inventario/categorias/",  # ⚠️ v2.61.3: Facade
                    "ui": "/workspace/#inventario",
                },
                "inventario-productos": {
                    "api": "/api/v1/core/v1/inventario/productos/",  # ⚠️ v2.61.3: Facade
                    "ui": "/workspace/#inventario",
                },
                "inventario-servicios": {
                    "api": "/api/v1/core/v1/inventario/servicios/",  # ⚠️ v2.61.3: Facade
                    "ui": "/workspace/#inventario",
                },
                "inventario-activos": {
                    "api": "/api/v1/core/v1/inventario/activos/",  # ⚠️ v2.61.3: Facade
                    "ui": "/workspace/#inventario",
                },
                "inventario-movimientos": {
                    "api": "/api/v1/core/v1/inventario/movimientos/",  # ⚠️ v2.61.3: Facade
                    "ui": "/workspace/#inventario",
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
    ViewSet para secciones del dashboard (Core API v2.61.2).
    
    ⚠️ CRUD MODULARIZADO:
    - READ: list() - GET /api/v1/core/dashboard/sections/
    
    ⚠️ FUNCIONES DISPONIBLES:
    - list(): Retorna todas las secciones del dashboard en orden (empresas → facturas → contabilidad → perfil)
    
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


class CoreAuthViewSet(ViewSet):
    """
    ViewSet centralizado para autenticación en Core API v2.61.2.
    
    ⚠️ CRUD MODULARIZADO:
    - CREATE: login() - POST /api/v1/core/auth/login/
    - CREATE: logout() - POST /api/v1/core/auth/logout/
    
    ⚠️ FUNCIONES DISPONIBLES:
    - login(): Autentica un usuario en el tenant actual (valida TenantMembership)
    - logout(): Cierra la sesión del usuario actual
    
    ⚠️ POLÍTICA:
    - Centraliza todos los endpoints de auth para tenants privados
    - Valida TenantMembership antes de permitir login
    - Usa SessionAuthentication para mantener compatibilidad con frontend
    - Endpoints públicos (AllowAny) para login/logout
    
    Endpoints:
    - POST /api/v1/core/auth/login/ - Autenticar usuario
    - POST /api/v1/core/auth/logout/ - Cerrar sesión
    """
    authentication_classes = []  # AllowAny - no requiere autenticación previa
    permission_classes = [permissions.AllowAny]
    
    @action(detail=False, methods=['post'], url_path='login', url_name='login')
    def login(self, request):
        """
        POST /api/v1/core/auth/login/
        
        Autentica un usuario en el tenant actual.
        
        Body:
        {
            "email": "usuario@ejemplo.com",
            "password": "contraseña"
        }
        
        Response (200 OK):
        {
            "success": true,
            "redirect_url": "/dashboard/",
            "user": {
                "id": 1,
                "email": "usuario@ejemplo.com",
                "first_name": "Nombre",
                "last_name": "Apellido"
            }
        }
        
        Response (400/401/403):
        {
            "detail": "Mensaje de error"
        }
        """
        email = request.data.get('email', '').strip().lower()
        password = request.data.get('password', '')
        
        # Validación básica
        if not email or not password:
            return Response(
                {"detail": "Email y contraseña son requeridos."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Obtener tenant del request (inyectado por middleware)
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            logger.error("CoreAuthViewSet.login: No se pudo determinar el tenant actual")
            return Response(
                {"detail": "No se pudo determinar el tenant actual."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Autenticar usuario (busca en esquema public)
            # Intentar autenticar directamente con email
            user = authenticate(request=request, username=email, password=password)
            
            # Si falla, intentar buscar usuario por email y autenticar con username
            if not user:
                current_schema = connection.schema_name
                try:
                    connection.set_schema_to_public()
                    try:
                        user_by_email = User.objects.get(email=email, is_active=True)
                        # Intentar autenticar con el username real del usuario
                        user = authenticate(request=request, username=user_by_email.username, password=password)
                    except User.DoesNotExist:
                        user = None
                finally:
                    connection.set_schema(current_schema)
            
            if not user:
                logger.warning(
                    "CoreAuthViewSet.login: Credenciales inválidas para email=%s, tenant=%s",
                    email, tenant.schema_name
                )
                return Response(
                    {"detail": "Credenciales inválidas."},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            if not user.is_active:
                logger.warning(
                    "CoreAuthViewSet.login: Usuario inactivo: email=%s, tenant=%s",
                    email, tenant.schema_name
                )
                return Response(
                    {"detail": "Usuario inactivo."},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Verificar membresía en el tenant actual (en esquema public)
            current_schema = connection.schema_name
            try:
                connection.set_schema_to_public()
                membership = TenantMembership.objects.filter(
                    client=tenant,
                    user=user,
                    is_active=True,
                ).first()
            finally:
                connection.set_schema(current_schema)
            
            if not membership:
                logger.warning(
                    "CoreAuthViewSet.login: Usuario sin membresía en tenant: user=%s, tenant=%s",
                    user.email, tenant.schema_name
                )
                return Response(
                    {"detail": "No tienes acceso a este tenant. Por favor, contacta al administrador."},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Realizar login de sesión
            login(request, user)
            
            # Construir redirect_url (puede venir de settings o ser fijo)
            redirect_url = "/dashboard/"  # TODO: Configurable desde settings
            
            logger.info(
                "CoreAuthViewSet.login: Login exitoso: user=%s, tenant=%s",
                user.email, tenant.schema_name
            )
            
            return Response({
                "success": True,
                "redirect_url": redirect_url,
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "first_name": user.first_name or "",
                    "last_name": user.last_name or "",
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(
                "CoreAuthViewSet.login: Error inesperado: email=%s, tenant=%s, error=%s",
                email, tenant.schema_name if tenant else 'none', str(e),
                exc_info=True
            )
            return Response(
                {"detail": "Error interno al procesar el login."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'], url_path='logout', url_name='logout')
    def logout(self, request):
        """
        POST /api/v1/core/auth/logout/
        
        Cierra la sesión del usuario actual.
        
        Response (200 OK):
        {
            "success": true,
            "message": "Sesión cerrada correctamente."
        }
        """
        try:
            user_email = request.user.email if request.user.is_authenticated else 'anonymous'
            tenant = getattr(request, 'tenant', None)
            
            logout(request)
            
            logger.info(
                "CoreAuthViewSet.logout: Logout exitoso: user=%s, tenant=%s",
                user_email, tenant.schema_name if tenant else 'none'
            )
            
            return Response({
                "success": True,
                "message": "Sesión cerrada correctamente."
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(
                "CoreAuthViewSet.logout: Error inesperado: error=%s",
                str(e),
                exc_info=True
            )
            return Response(
                {"detail": "Error interno al procesar el logout."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
