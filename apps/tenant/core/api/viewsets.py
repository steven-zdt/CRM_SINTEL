"""
ViewSets para Core API v2.61.2.

# WARNING: POLÍTICA:
- Endpoints de composición/orquestación para presentación
- NO reemplazan CRUD de las apps individuales
- Mantienen tenant-awareness y branding dinámico

# WARNING: CRUD MODULARIZADO POR FUNCIÓN:
Cada ViewSet documenta claramente las funciones CRUD disponibles:
- READ (GET): list, retrieve
- CREATE (POST): create, @action personalizadas
- UPDATE (PUT/PATCH): update, partial_update
- DELETE (DELETE): destroy

# WARNING: ESTRUCTURA MODULARIZADA:
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

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.db import connection
from rest_framework import permissions, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

# --- TenantInfoView: Landing público del tenant ---
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet

from apps.public.tenants.models import TenantMembership
from apps.tenant.core.services.contabilidad import get_contabilidad_snapshot
from apps.tenant.core.services.empresa import get_empresas_snapshot
from apps.tenant.core.services.facturas import get_facturas_snapshot
from apps.tenant.core.services.perfil import get_perfil_snapshot
from apps.tenant.dashboard.api.permissions import IsUserOrHigher

from apps.tenant.core.services.activation_service import (
    AlreadyActivatedError,
    InvalidTokenError,
    TenantMismatchError,
    UserNotFoundError,
    process_activation,
    verify_activation_token,
)


class TenantInfoView(APIView):
    """
    Endpoint público para exponer información básica del tenant (branding, estado, nombre).
    GET /api/v1/core/landing/info/
    """
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({"detail": "No se pudo determinar el tenant actual."}, status=status.HTTP_400_BAD_REQUEST)

        # Branding dinámico (si existe)
        try:
            from apps.tenant.core.branding import get_tenant_branding
            branding = get_tenant_branding(request)
        except Exception:
            branding = {}

        data = {
            "tenant": {
                "id": tenant.id,
                "nombre": getattr(tenant, 'nombre', 'Tenant'),
                "schema_name": getattr(tenant, 'schema_name', None),
                "is_active": getattr(tenant, 'is_active', True),
            },
            "branding": branding,
            "status": "ok"
        }
        return Response(data, status=status.HTTP_200_OK)

logger = logging.getLogger(__name__)
User = get_user_model()


class CoreLinksViewSet(ViewSet):
    """
    Link Registry para Core API v2.61.2.
    
    # WARNING: CRUD MODULARIZADO:
    - READ: list() - GET /api/v1/core/links/
    
    # WARNING: FUNCIONES DISPONIBLES:
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
                "api": "/api/v1/core/v1/facturas/facturas/",  # # WARNING: v2.61.2: Facade
                "ui": "/workspace/#facturas",  # # WARNING: v2.61.2: Workspace tab
            },
            "facturas-items": {
                "api": "/api/v1/core/v1/facturas/items-factura/",  # # WARNING: v2.61.2: Facade
                "ui": "/workspace/#facturas",
            },
            "facturas-notas-credito": {
                "api": "/api/v1/core/v1/facturas/notas-credito/",  # # WARNING: v2.61.2: Facade
                "ui": "/workspace/#facturas",
            },
      ...
    }
    
    # WARNING: POLÍTICA:
    - URLs siempre relativas (sin dominio)
    - No hardcodes de rutas en el frontend
    - Centralizado en Core API para fácil mantenimiento
    """
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
            # # WARNING: POLÍTICA: URLs siempre relativas (sin dominio)
            # El frontend construye URLs absolutas usando window.location.origin si es necesario
            links = {
                "empresa": {
                    "api": "/api/v1/empresas/",
                    "ui": "/dashboard/empresa/",  # Placeholder para UI futura
                },
                "facturas": {
                    "api": "/api/v1/core/v1/facturas/facturas/",  # # WARNING: v2.61.1: Facade
                    "ui": "/workspace/#facturas",  # # WARNING: v2.61.1: Workspace tab
                },
                "facturas-items": {
                    "api": "/api/v1/core/v1/facturas/items-factura/",  # # WARNING: v2.61.1: Facade
                    "ui": "/workspace/#facturas",
                },
                "facturas-notas-credito": {
                    "api": "/api/v1/core/v1/facturas/notas-credito/",  # # WARNING: v2.61.1: Facade
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
                    "api": "/api/v1/core/v1/contabilidad/periodos-contables/",  # Facade # WARNING: v2.61
                    "ui": "/dashboard/contabilidad/periodos/",  # Placeholder para UI futura
                },
                "catalogo-niif": {
                    "api": "/api/v1/core/v1/contabilidad/catalogo-niif/",  # Facade
                    "ui": "/dashboard/contabilidad/catalogo-niif/",  # Placeholder para UI futura
                },
                "cotizaciones": {
                    "api": "/api/v1/core/v1/cotizaciones/cotizaciones/",  # Endpoint principal de cotizaciones (facade) # WARNING: v2.61
                    "ui": "/workspace/#cotizaciones",  # UI en workspace
                },
                "cotizaciones-items": {
                    "api": "/api/v1/core/v1/cotizaciones/items/",  # Facade # WARNING: v2.61
                    "ui": "/workspace/#cotizaciones",  # UI en workspace
                },
                "cotizaciones-configuracion": {
                    "api": "/api/v1/core/v1/cotizaciones/configuracion/",  # Facade # WARNING: v2.61
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
                    "api": "/api/v1/core/v1/inventario/categorias/",  # # WARNING: v2.61.3: Facade
                    "ui": "/workspace/#inventario",
                },
                "inventario-productos": {
                    "api": "/api/v1/core/v1/inventario/productos/",  # # WARNING: v2.61.3: Facade
                    "ui": "/workspace/#inventario",
                },
                "inventario-servicios": {
                    "api": "/api/v1/core/v1/inventario/servicios/",  # # WARNING: v2.61.3: Facade
                    "ui": "/workspace/#inventario",
                },
                "inventario-activos": {
                    "api": "/api/v1/core/v1/inventario/activos/",  # # WARNING: v2.61.3: Facade
                    "ui": "/workspace/#inventario",
                },
                "inventario-movimientos": {
                    "api": "/api/v1/core/v1/inventario/movimientos/",  # # WARNING: v2.61.3: Facade
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
    
    # WARNING: CRUD MODULARIZADO:
    - READ: list() - GET /api/v1/core/dashboard/sections/
    
    # WARNING: FUNCIONES DISPONIBLES:
    - list(): Retorna todas las secciones del dashboard en orden (empresas → facturas → contabilidad → perfil)
    
    GET /api/v1/core/dashboard/sections/
    
    Retorna las secciones en orden requerido:
    - empresas → facturas → contabilidad → perfil
    
    # WARNING: POLÍTICA:
    - Orquestación de datos de múltiples TENANT_APPS
    - NO duplica lógica de negocio (usa servicios de cada app)
    - Mantiene tenant-awareness (django-tenants maneja el aislamiento)
    """
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
            # # WARNING: ORDEN REQUERIDO: empresas → facturas → contabilidad → perfil
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
            
            # # WARNING: POLÍTICA API-First: Incluir información de usuario, tenant y KPIs
            # para que el shell estático consuma EXCLUSIVAMENTE Core API
            from apps.tenant.core.branding import get_tenant_branding
            from apps.tenant.dashboard.services import get_user_role_in_tenant
            
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
            
            # # WARNING: v2.61: Retornar datos directamente sin serializer (serializers_sections no existe)
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
    
    # WARNING: CRUD MODULARIZADO:
    - CREATE: login() - POST /api/v1/core/auth/login/
    - CREATE: logout() - POST /api/v1/core/auth/logout/
    
    # WARNING: FUNCIONES DISPONIBLES:
    - login(): Autentica un usuario en el tenant actual (valida TenantMembership)
    - logout(): Cierra la sesión del usuario actual
    
    # WARNING: POLÍTICA:
    - Centraliza todos los endpoints de auth para tenants privados
    - Valida TenantMembership antes de permitir login
    - Usa SessionAuthentication para mantener compatibilidad con frontend
    - Endpoints públicos (AllowAny) para login/logout
    
    Endpoints:
    - POST /api/v1/core/auth/login/ - Autenticar usuario
    - POST /api/v1/core/auth/logout/ - Cerrar sesión
    - GET /api/v1/core/auth/from-session/ - Obtener JWT desde sesión
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [permissions.AllowAny] # login/logout son públicos, from-session verifica auth internamente
    
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
            
            # Garantizar TenantProfile existe (SSoT v2.61.8)
            # Los permisos basados en TenantProfile.rol requieren que el perfil
            # exista al momento de evaluar has_permission.
            try:
                from apps.tenant.empresa.models import Empresa
                from apps.tenant.perfil.services.business_service import PerfilBusinessService
                empresa = Empresa.objects.only('id').first()
                if empresa:
                    PerfilBusinessService().get_or_initialize_profile(user, empresa)
            except Exception as exc:
                logger.warning(
                    "CoreAuthViewSet.login: auto-create TenantProfile fallo: "
                    "user=%s, tenant=%s, error=%s",
                    user.email, tenant.schema_name, str(exc),
                )
            
            # Construir redirect_url (API-First)
            # [DEBUG] En desarrollo, incluimos el puerto si es necesario
            app_port = getattr(settings, "APP_PORT", "8000")
            if settings.DEBUG and app_port and str(app_port) not in ("80", "443"):
                host = request.get_host().split(":")[0]
                redirect_url = f"http://{host}:{app_port}/dashboard/"
            else:
                redirect_url = "/dashboard/"
            
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

    @action(detail=False, methods=['get'], url_path='from-session', url_name='from-session')
    def from_session(self, request):
        """
        GET /api/v1/core/auth/from-session/
        
        Genera token JWT desde la sesión activa del usuario.
        Útil para auto-login en el workspace.
        """
        if not request.user.is_authenticated:
            return Response(
                {"detail": "No autenticado"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        try:
            refresh = RefreshToken.for_user(request.user)
            return Response({
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(
                "CoreAuthViewSet.from_session: Error generando token para usuario=%s, error=%s",
                request.user.email, str(e),
                exc_info=True
            )
            return Response(
                {"detail": f"Error al generar token: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'], url_path='consume-ott', url_name='consume-ott')
    def consume_ott(self, request):
        """
        POST /api/v1/core/auth/consume-ott/
        
        Consume el One-Time Token (OTT) generado durante el onboarding, invoca la
        función que lo valida desde Redis, y loguea automáticamente al administrador
        en el tenant privado recién creado.
        """
        ott = request.data.get('ott', '').strip()
        if not ott:
            return Response({"detail": "Token OTT requerido."}, status=status.HTTP_400_BAD_REQUEST)
        
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({"detail": "No se pudo determinar el tenant."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            from apps.public.tenants.services.onboarding import consume_onboarding_ott
            payload = consume_onboarding_ott(ott)
            
            if not payload:
                return Response({"detail": "Token inválido o expirado."}, status=status.HTTP_400_BAD_REQUEST)
            
            # Verificar que el token pertenece a este tenant
            if payload.get("schema_name") != tenant.schema_name:
                return Response({"detail": "El token no pertenece a este tenant."}, status=status.HTTP_400_BAD_REQUEST)
            
            user_id = payload.get("user_id")
            
            # Obtener usuario asegurando el esquema correcto
            current_schema = connection.schema_name
            try:
                connection.set_schema_to_public()
                user = User.objects.get(id=user_id, is_active=True)
            except User.DoesNotExist:
                user = None
            finally:
                connection.set_schema(current_schema)
                
            if not user:
                return Response({"detail": "Usuario inválido o inactivo."}, status=status.HTTP_401_UNAUTHORIZED)
                
            # Loguear automáticamente mediante sesión (Django requiere user.backend cuando user se obtiene via get)
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            login(request, user)
            
            logger.info("CoreAuthViewSet.consume_ott: Autenticación exitosa vía OTT: user=%s, tenant=%s", user.email, tenant.schema_name)
            
            # El test original también espera respuesta exitosa vacía o con tokens.
            # Como usamos session auth (HTTP cookies) a nivel vista, esto es suficiente.
            return Response({"success": True}, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(
                "CoreAuthViewSet.consume_ott: Error inesperado: error=%s",
                str(e),
                exc_info=True
            )
            return Response(
                {"detail": "Error interno al procesar el consumo del token."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


    @action(detail=False, methods=['post'], url_path='password-reset/request', url_name='password-reset-request')
    def password_reset_request(self, request):
        """POST /api/v1/core/auth/password-reset/request/"""
        email_or_username = request.data.get('email_or_username', '').strip()
        if not email_or_username:
            return Response(
                {"detail": "Email o username requerido."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response(
                {"detail": "No se pudo determinar el tenant."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from apps.tenant.core.services.auth_service import (
                password_reset_request as service_password_reset_request,
            )
            result = service_password_reset_request(email_or_username, tenant)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error en password_reset_request: {str(e)}", exc_info=True)
            return Response(
                {"detail": "Si el email existe y tiene acceso a este tenant, recibirás un correo."},
                status=status.HTTP_200_OK
            )

    @action(detail=False, methods=['post'], url_path='password-reset/validate', url_name='password-reset-validate')
    def password_reset_validate(self, request):
        """POST /api/v1/core/auth/password-reset/validate/"""
        uid = request.data.get('uid', '').strip()
        token = request.data.get('token', '').strip()
        
        if not uid or not token:
            return Response(
                {"detail": "UID y token requeridos."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response(
                {"detail": "No se pudo determinar el tenant."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from apps.tenant.core.services.auth_service import (
                password_reset_validate as service_password_reset_validate,
            )
            result = service_password_reset_validate(uid, token, tenant)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            logger.warning(f"Token inválido: {str(e)}")
            return Response(
                {"detail": "Token inválido o expirado."},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['post'], url_path='password-reset/confirm', url_name='password-reset-confirm')
    def password_reset_confirm(self, request):
        """POST /api/v1/core/auth/password-reset/confirm/"""
        uid = request.data.get('uid', '').strip()
        token = request.data.get('token', '').strip()
        new_password = request.data.get('new_password', '')
        
        if not uid or not token or not new_password:
            return Response(
                {"detail": "UID, token y nueva contraseña son requeridos."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response(
                {"detail": "No se pudo determinar el tenant."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from apps.tenant.core.services.auth_service import (
                password_reset_confirm as service_password_reset_confirm,
            )
            result = service_password_reset_confirm(uid, token, new_password, tenant)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error en password_reset_confirm: {str(e)}", exc_info=True)
            return Response(
                {"detail": "Error al restablecer contraseña. Intenta nuevamente."},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get', 'post'], url_path='activate', url_name='activate')
    def activate(self, request):
        """
        Endpoint de activación de owner (Core API v2.61).
        
        # WARNING: POLÍTICA v2.61:
        - Centralizado en Core para control total de identidad.
        - GET: Valida token y retorna info de usuario/tenant.
        - POST: Procesa activación (establece contraseña).
        """
        token = request.query_params.get('token')
        
        if not token:
            return Response(
                {"detail": "Token de activacion no proporcionado."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # GET: Verificar token y retornar informacion
        if request.method == 'GET':
            try:
                # ⚠️ POLÍTICA: Usar servicio de dominio migrado a Core
                result = verify_activation_token(request, token)
                return Response({
                    "user": result['user'],
                    "tenant": result['tenant'],
                    "token_valid": result['token_valid'],
                }, status=status.HTTP_200_OK)
            except InvalidTokenError as e:
                return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            except UserNotFoundError as e:
                return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)
            except TenantMismatchError as e:
                return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            except AlreadyActivatedError as e:
                return Response(
                    {
                        "detail": str(e),
                        "redirect_url": "/static/tenant/core/auth/login.html",
                        "login_api_url": "/api/v1/core/auth/login/",
                    },
                    status=status.HTTP_409_CONFLICT
                )
            except Exception as e:
                logger.error("CoreAuthViewSet.activate (GET): error inesperado: %s", str(e), exc_info=True)
                return Response(
                    {"detail": "Error interno al validar el token de activacion."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        # POST: Procesar activacion
        password1 = request.data.get('password1')
        password2 = request.data.get('password2')
        
        if not password1 or not password2:
            return Response(
                {"detail": "Ambas contrasenas son requeridas."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # ⚠️ POLÍTICA: Usar servicio de dominio migrado a Core
            result = process_activation(request, token, password1, password2)
            return Response(result, status=status.HTTP_200_OK)
        except InvalidTokenError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except UserNotFoundError as e:
            return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except TenantMismatchError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except AlreadyActivatedError as e:
            return Response(
                {
                    "detail": str(e),
                    "redirect_url": "/static/tenant/core/auth/login.html",
                    "login_api_url": "/api/v1/core/auth/login/",
                },
                status=status.HTTP_409_CONFLICT
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error("CoreAuthViewSet.activate (POST): error inesperado: %s", str(e), exc_info=True)
            return Response(
                {"detail": "Error interno al procesar la activacion."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
