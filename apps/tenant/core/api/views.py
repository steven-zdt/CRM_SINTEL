"""
ViewSets para Core API.

⚠️ POLÍTICA:
- Endpoints de composición/orquestación para presentación
- NO reemplazan CRUD de las apps individuales
- Mantienen tenant-awareness y branding dinámico
- Auth centralizado: todos los flujos de autenticación están en Core
"""
import json
import logging
from django.contrib.auth import login
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authentication import SessionAuthentication
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser

from apps.tenant.core.api.serializers import (
    DashboardCompletoSerializer,
    MiEmpresaSerializer,
    MiPerfilSerializer,
    FacturasResumenSerializer,
    ContabilidadResumenSerializer,
    LandingResumenSerializer,
)
from apps.tenant.core.services.orchestration import (
    get_dashboard_completo,
    get_empresa_summary,
    get_facturas_resumen,
    get_contabilidad_resumen,
    get_perfil_resumen,
)
# ⚠️ IMPORT LAZY: Servicios de maildigester se importan dentro de los métodos (evita ciclos)
# from apps.tenant.core.services.facturas_maildigester_adapter import ...
from apps.tenant.core.services.landing import get_landing_resumen
from apps.tenant.core.services.landing_adapter import (
    get_public_info_from_landing,
    verify_activation_via_landing,
    process_activation_via_landing,
)
from apps.tenant.landing.api.serializers import TenantPublicInfoSerializer
from apps.tenant.landing.services.activation_service import (
    InvalidTokenError as LandingInvalidTokenError,
    UserNotFoundError as LandingUserNotFoundError,
    TenantMismatchError as LandingTenantMismatchError,
    AlreadyActivatedError as LandingAlreadyActivatedError,
)
from apps.tenant.core.services.auth_service import (
    login_user,
    logout_user,
    password_reset_request,
    password_reset_validate,
    password_reset_confirm,
    InvalidCredentialsError,
    NoMembershipError,
    TenantNotFoundError as AuthTenantNotFoundError,
)
from apps.tenant.landing.services.password_reset import (
    InvalidTokenError,
    UserNotFoundError,
    TenantNotFoundError,
)
from apps.tenant.core.services.empresa import get_mi_empresa  # Legacy (mantener por compatibilidad)
from apps.tenant.core.branding import get_tenant_branding
from apps.tenant.dashboard.api.permissions import IsUserOrHigher

logger = logging.getLogger(__name__)


class CoreRoutesView(APIView):
    """
    Endpoint centralizado para descubrimiento de rutas API.
    
    GET /api/v1/core/routes/
    
    ⚠️ POLÍTICA: Mapa canónico de rutas por módulo para eliminar URLs hardcodeadas en frontend.
    - Rutas relativas (sin dominio)
    - Nombre de claves canónicas por módulo
    - Soporta subclaves para módulos con múltiples recursos (contabilidad, inventario)
    - No resuelve permisos aquí (permiso IsAuthenticated basta)
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request, *args, **kwargs):
        """
        Retorna mapa canónico de rutas por módulo.
        
        Formato:
        {
            "clientes": {
                "collection": "/api/v1/clientes/",
                "detail": "/api/v1/clientes/{id}/",
                "datatable": "/api/v1/clientes/dt/clientes/"
            },
            "contabilidad": {
                "cuentas": {
                    "collection": "/api/v1/contabilidad/cuentas-contables/",
                    "detail": "/api/v1/contabilidad/cuentas-contables/{id}/",
                    "datatable": "/api/v1/contabilidad/dt/cuentas-contables/"
                },
                "asientos": { ... }
            },
            ...
        }
        """
        routes = {
            "clientes": {
                "collection": "/api/v1/clientes/",
                "detail": "/api/v1/clientes/{id}/",
                "datatable": "/api/v1/clientes/dt/clientes/"
            },
            "proveedores": {
                "collection": "/api/v1/proveedores/",
                "detail": "/api/v1/proveedores/{id}/",
                "datatable": "/api/v1/proveedores/dt/proveedores/"
            },
            "gastos": {
                "collection": "/api/v1/gastos/",
                "detail": "/api/v1/gastos/{id}/",
                "datatable": "/api/v1/gastos/dt/gastos/"
            },
            "empleados": {
                "collection": "/api/v1/empleados/empleados/",
                "detail": "/api/v1/empleados/empleados/{id}/",
                "datatable": "/api/v1/empleados/dt/empleados/"
            },
            "facturas": {
                "collection": "/api/v1/facturas/",
                "detail": "/api/v1/facturas/{id}/",
                "datatable": "/api/v1/facturas/dt/facturas/"
            },
            "contabilidad": {
                "cuentas": {
                    "collection": "/api/v1/contabilidad/cuentas-contables/",
                    "detail": "/api/v1/contabilidad/cuentas-contables/{id}/",
                    "datatable": "/api/v1/contabilidad/dt/cuentas-contables/"
                },
                "asientos": {
                    "collection": "/api/v1/contabilidad/asientos-contables/",
                    "detail": "/api/v1/contabilidad/asientos-contables/{id}/",
                    "datatable": "/api/v1/contabilidad/dt/asientos-contables/"
                }
            },
            "inventario": {
                "productos": {
                    "collection": "/api/v1/inventario/productos/",
                    "detail": "/api/v1/inventario/productos/{id}/",
                    "datatable": "/api/v1/inventario/productos/dt/"
                },
                "servicios": {
                    "collection": "/api/v1/inventario/servicios/",
                    "detail": "/api/v1/inventario/servicios/{id}/",
                    "datatable": "/api/v1/inventario/servicios/dt/"
                },
                "activos": {
                    "collection": "/api/v1/inventario/activos/",
                    "detail": "/api/v1/inventario/activos/{id}/",
                    "datatable": "/api/v1/inventario/activos/dt/"
                },
                "movimientos": {
                    "collection": "/api/v1/inventario/movimientos/",
                    "detail": "/api/v1/inventario/movimientos/{id}/",
                    "datatable": "/api/v1/inventario/movimientos/"
                }
            },
            "empresa": {
                "collection": "/api/v1/empresas/",
                "detail": "/api/v1/empresas/{id}/",
                "singleton": "/api/v1/core/empresa/"
            },
            "perfil": {
                "singleton": "/api/v1/perfil/perfiles/me/"
            }
        }
        
        return Response(routes, status=status.HTTP_200_OK)


class CoreDashboardView(APIView):
    """
    Endpoint para dashboard completo compuesto de múltiples apps.
    
    GET /api/v1/core/dashboard/
    
    ⚠️ POLÍTICA: Composición de datos de empresa, facturas, contabilidad, perfil.
    Incluye branding dinámico desde BD.
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsUserOrHigher]
    
    def get(self, request, *args, **kwargs):
        tenant = getattr(request, 'tenant', None)
        user = request.user
        
        if not tenant:
            return Response(
                {"detail": "No se pudo determinar el tenant actual."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            data = get_dashboard_completo(user, tenant)
            serializer = DashboardCompletoSerializer(data)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(
                "CoreDashboardView: error cargando dashboard para user=%s, tenant=%s, error=%s",
                user.email if user.is_authenticated else 'anonymous',
                tenant.schema_name if tenant else 'none',
                str(e),
                exc_info=True
            )
            return Response(
                {"detail": "Error interno al cargar el dashboard."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MiEmpresaView(APIView):
    """
    Endpoint para información de la empresa del tenant.
    
    ⚠️ v2.30: Core API como orquestador único de la UI privada.
    - GET /api/v1/core/empresa/ → Retorna DTO Core de Empresa (branding/datos fiscales)
    - PATCH /api/v1/core/empresa/ → Actualización parcial de Empresa
    
    ⚠️ POLÍTICA:
    - SessionAuthentication + CSRF (UI privada)
    - IsAuthenticated; la membresía por tenant ya la valida el TenantAwareBackend
    - JSON-only global (sin BrowsableAPIRenderer)
    - Usa Core Service Adapter (apps/tenant/core/services/empresa_adapter)
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    
    def get(self, request, *args, **kwargs):
        """
        GET /api/v1/core/empresa/
        
        Retorna DTO Core de Empresa (branding/datos fiscales).
        """
        try:
            from apps.tenant.core.services.empresa_adapter import core_empresa_get
            from apps.tenant.core.branding import get_tenant_branding
            
            empresa_dto = core_empresa_get()
            if not empresa_dto:
                # No existe empresa
                branding = get_tenant_branding(request)
                return Response(
                    {
                        'empresa': None,
                        'branding': branding,
                        'setup_required': True,
                    },
                    status=status.HTTP_200_OK
                )
            
            # Construir URL absoluta del logo si existe
            if empresa_dto.get('logo') and not empresa_dto.get('logo_url'):
                try:
                    from django.conf import settings
                    logo_path = empresa_dto['logo']
                    if hasattr(settings, 'MEDIA_URL'):
                        media_url = settings.MEDIA_URL.rstrip('/')
                        logo_path_clean = logo_path.lstrip('/')
                        empresa_dto['logo_url'] = request.build_absolute_uri(f"{media_url}/{logo_path_clean}")
                except Exception:
                    pass
            
            # Agregar branding
            branding = get_tenant_branding(request)
            empresa_dto['branding'] = branding
            empresa_dto['setup_required'] = False
            
            return Response(empresa_dto, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(
                "MiEmpresaView GET: error cargando empresa, error=%s",
                str(e),
                exc_info=True
            )
            return Response(
                {"detail": "Error interno al cargar la información de la empresa."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def patch(self, request, *args, **kwargs):
        """
        PATCH /api/v1/core/empresa/
        
        Actualización parcial de Empresa.
        Soporta application/json y multipart/form-data (para logo).
        """
        # ⚠️ v2.40: Validación temprana de payload para evitar ParseError 500
        # DRF puede lanzar ParseError si Content-Type es application/json pero el body no es JSON válido
        # Esto debe retornar 400, no 500
        if not isinstance(request.data, dict):
            return Response(
                {"error": "invalid_payload", "detail": "Cuerpo JSON requerido. El payload debe ser un objeto JSON válido."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validar que el payload no esté completamente vacío (al menos debe tener algún campo)
        if not request.data:
            return Response(
                {"error": "invalid_payload", "detail": "El payload no puede estar vacío. Proporcione al menos un campo para actualizar."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from apps.tenant.core.services.empresa_adapter import core_empresa_update
            from apps.tenant.core.branding import get_tenant_branding
            
            # Preparar datos para actualización
            data = {}
            files = None
            
            # Extraer campos editables del request.data (solo campos canónicos)
            campos_editables = [
                'razon_social', 'nit', 'dv', 'direccion', 'telefono', 'email_contacto',
                'regimen_tributario', 'website', 'moneda'
            ]
            for campo in campos_editables:
                if campo in request.data:
                    data[campo] = request.data[campo]
            
            # ⚠️ v2.40: Soporte para mail_inbox_config a través del orchestrator
            mail_inbox_config_data = None
            if 'mail_inbox_config' in request.data:
                mail_inbox_config_data = request.data['mail_inbox_config']
                if not isinstance(mail_inbox_config_data, dict):
                    return Response(
                        {"error": "mail_inbox_config debe ser un objeto JSON válido."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Extraer archivos si hay multipart
            if request.FILES and 'logo' in request.FILES:
                files = {'logo': request.FILES['logo']}
            elif 'logo' in request.data and request.data['logo'] == '':
                # Eliminar logo (cadena vacía)
                data['logo'] = None
            
            # ⚠️ UPSERT: Si no existe empresa, crear; si existe, actualizar
            from apps.tenant.empresa.models import Empresa
            empresa_existente = Empresa.objects.first()
            
            if not empresa_existente:
                # Crear nueva empresa usando get_or_create_empresa
                from apps.tenant.empresa.impl.empresa_service import get_or_create_empresa
                empresa_dto = get_or_create_empresa(defaults=data)
                status_code = status.HTTP_201_CREATED
            else:
                # Actualizar empresa existente
                empresa_dto = core_empresa_update(data, files=files)
                status_code = status.HTTP_200_OK
            
            # ⚠️ v2.40: Procesar mail_inbox_config si está presente
            if mail_inbox_config_data:
                from apps.tenant.core.services.empresa_adapter import (
                    core_mailbox_create,
                    core_mailbox_update
                )
                from apps.tenant.empresa.models import MailInboxConfig
                
                # Determinar si es creación o actualización
                config_id = mail_inbox_config_data.get('id')
                if config_id:
                    # Actualizar configuración existente
                    try:
                        # Remover 'id' del payload antes de actualizar
                        config_payload = {k: v for k, v in mail_inbox_config_data.items() if k != 'id'}
                        mailbox_dto = core_mailbox_update(config_id, config_payload)
                        empresa_dto['mail_inbox_config'] = mailbox_dto
                    except MailInboxConfig.DoesNotExist:
                        return Response(
                            {"error": f"Configuración de buzón con ID {config_id} no encontrada."},
                            status=status.HTTP_404_NOT_FOUND
                        )
                    except ValueError as ve:
                        return Response(
                            {"error": str(ve)},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                else:
                    # Crear nueva configuración
                    try:
                        mailbox_dto = core_mailbox_create(mail_inbox_config_data)
                        empresa_dto['mail_inbox_config'] = mailbox_dto
                    except ValueError as ve:
                        return Response(
                            {"error": str(ve)},
                            status=status.HTTP_400_BAD_REQUEST
                        )
            
            # Construir URL absoluta del logo si existe
            if empresa_dto.get('logo') and not empresa_dto.get('logo_url'):
                try:
                    from django.conf import settings
                    logo_path = empresa_dto['logo']
                    if hasattr(settings, 'MEDIA_URL'):
                        media_url = settings.MEDIA_URL.rstrip('/')
                        logo_path_clean = logo_path.lstrip('/')
                        empresa_dto['logo_url'] = request.build_absolute_uri(f"{media_url}/{logo_path_clean}")
                except Exception:
                    pass
            
            # Agregar branding
            branding = get_tenant_branding(request)
            empresa_dto['branding'] = branding
            empresa_dto['setup_required'] = False
            
            return Response(empresa_dto, status=status_code)
            
        except ValueError as e:
            # Errores de validación del Service Layer
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(
                "MiEmpresaView PATCH: error actualizando empresa, error=%s",
                str(e),
                exc_info=True
            )
            return Response(
                {"detail": "Error interno al actualizar la empresa."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MiPerfilView(APIView):
    """
    Endpoint para perfil del usuario en el tenant.
    
    ⚠️ v2.30: Core API como orquestador único de la UI privada.
    - GET /api/v1/core/mi-perfil/ → Retorna el perfil del usuario autenticado (DTO Core)
    - PATCH /api/v1/core/mi-perfil/ → Actualiza campos del perfil; soporta application/json y multipart/form-data para avatar
    
    ⚠️ POLÍTICA:
    - SessionAuthentication + CSRF (UI privada)
    - IsAuthenticated; la membresía por tenant ya la valida el TenantAwareBackend
    - JSON-only global (sin BrowsableAPIRenderer)
    - Usa Core Service Adapter (apps/tenant/core/services/perfil_adapter)
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    
    def get(self, request, *args, **kwargs):
        """
        GET /api/v1/core/mi-perfil/
        
        Retorna el perfil del usuario autenticado (DTO Core con campos del User global).
        """
        try:
            from apps.tenant.core.services.perfil_adapter import core_me_read
            
            dto = core_me_read(request.user)
            return Response(dto, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(
                "MiPerfilView GET: error cargando perfil para user=%s, error=%s",
                request.user.email if request.user.is_authenticated else 'anonymous',
                str(e),
                exc_info=True
            )
            return Response(
                {"detail": "Error interno al cargar el perfil."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def patch(self, request, *args, **kwargs):
        """
        PATCH /api/v1/core/mi-perfil/
        
        Actualiza campos del perfil del usuario autenticado.
        Soporta application/json y multipart/form-data (para avatar).
        
        Campos editables: cargo, departamento, telefono_corporativo, configuracion, avatar
        """
        try:
            from apps.tenant.core.services.perfil_adapter import core_me_update
            
            # Preparar datos para actualización
            data = {}
            files = None
            
            # Extraer campos editables del request.data
            campos_editables = ['cargo', 'departamento', 'telefono_corporativo', 'configuracion']
            for campo in campos_editables:
                if campo in request.data:
                    valor = request.data[campo]
                    # Si viene como string (multipart), parsearlo si es configuracion
                    if campo == 'configuracion' and isinstance(valor, str):
                        try:
                            import json
                            valor = json.loads(valor)
                        except (json.JSONDecodeError, TypeError):
                            valor = {}
                    data[campo] = valor
            
            # Extraer archivos si hay multipart
            if request.FILES and 'avatar' in request.FILES:
                files = {'avatar': request.FILES['avatar']}
            
            # Actualizar usando el Core Service Adapter
            dto = core_me_update(request.user, data, files=files)
            
            # Construir URL absoluta del avatar si existe
            if dto.get('avatar') and not dto.get('avatar_url'):
                try:
                    from django.conf import settings
                    avatar_path = dto['avatar']
                    if hasattr(settings, 'MEDIA_URL'):
                        media_url = settings.MEDIA_URL.rstrip('/')
                        avatar_path_clean = avatar_path.lstrip('/')
                        dto['avatar_url'] = request.build_absolute_uri(f"{media_url}/{avatar_path_clean}")
                except Exception:
                    pass
            
            return Response(dto, status=status.HTTP_200_OK)
            
        except ValueError as e:
            # Errores de validación del Service Layer
            logger.warning(
                "MiPerfilView PATCH: error de validación para user=%s, error=%s",
                request.user.email if request.user.is_authenticated else 'anonymous',
                str(e)
            )
            return Response(
                {"error": str(e), "detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(
                "MiPerfilView PATCH: error actualizando perfil para user=%s, error=%s",
                request.user.email if request.user.is_authenticated else 'anonymous',
                str(e),
                exc_info=True
            )
            return Response(
                {"detail": "Error interno al actualizar el perfil."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MiPerfilConfiguracionView(APIView):
    """
    Endpoint para actualizar la configuración de UI del perfil.
    
    ⚠️ v2.30: Core API como orquestador único de la UI privada.
    - PATCH /api/v1/core/mi-perfil/configuracion/ → Actualiza/mergea el JSON de configuracion
    
    ⚠️ POLÍTICA:
    - SessionAuthentication + CSRF (UI privada)
    - IsAuthenticated; la membresía por tenant ya la valida el TenantAwareBackend
    - JSON-only global (sin BrowsableAPIRenderer)
    - Usa Core Service Adapter (apps/tenant/core/services/perfil_adapter)
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    
    def patch(self, request, *args, **kwargs):
        """
        PATCH /api/v1/core/mi-perfil/configuracion/
        
        Actualiza/mergea el JSON de configuracion del perfil.
        
        Body: {"clave": "valor"} o {"configuracion": {"clave": "valor"}}
        Query param: ?merge=false para reemplazar toda la configuración (default: merge=true)
        """
        try:
            from apps.tenant.core.services.perfil_adapter import core_me_update_config
            
            # Obtener la configuración del request
            configuracion_data = request.data.get('configuracion', request.data)
            
            if not isinstance(configuracion_data, dict):
                return Response(
                    {'error': 'La configuración debe ser un objeto JSON válido.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Determinar si hacer merge (default: True)
            merge = request.query_params.get('merge', 'true').lower() == 'true'
            
            # Actualizar configuración usando el Core Service Adapter
            dto = core_me_update_config(request.user, configuracion_data, merge=merge)
            
            # Construir URL absoluta del avatar si existe
            if dto.get('avatar') and not dto.get('avatar_url'):
                try:
                    from django.conf import settings
                    avatar_path = dto['avatar']
                    if hasattr(settings, 'MEDIA_URL'):
                        media_url = settings.MEDIA_URL.rstrip('/')
                        avatar_path_clean = avatar_path.lstrip('/')
                        dto['avatar_url'] = request.build_absolute_uri(f"{media_url}/{avatar_path_clean}")
                except Exception:
                    pass
            
            return Response(dto, status=status.HTTP_200_OK)
            
        except ValueError as e:
            # Errores de validación del Service Layer
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(
                "MiPerfilConfiguracionView: error actualizando configuración para user=%s, error=%s",
                request.user.email if request.user.is_authenticated else 'anonymous',
                str(e),
                exc_info=True
            )
            return Response(
                {'detail': 'Error interno al actualizar la configuración.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class FacturasResumenView(APIView):
    """
    Endpoint para resumen de facturas.
    
    GET /api/v1/core/facturas/resumen/
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsUserOrHigher]
    
    def get(self, request, *args, **kwargs):
        tenant = getattr(request, 'tenant', None)
        user = request.user
        
        if not tenant:
            return Response(
                {"detail": "No se pudo determinar el tenant actual."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            data = get_facturas_resumen(tenant, user)
            serializer = FacturasResumenSerializer(data)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(
                "FacturasResumenView: error cargando resumen para tenant=%s, error=%s",
                tenant.schema_name if tenant else 'none',
                str(e),
                exc_info=True
            )
            return Response(
                {"detail": "Error interno al cargar el resumen de facturas."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ContabilidadResumenView(APIView):
    """
    Endpoint para resumen de contabilidad.
    
    GET /api/v1/core/contabilidad/resumen/
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsUserOrHigher]
    
    def get(self, request, *args, **kwargs):
        tenant = getattr(request, 'tenant', None)
        user = request.user
        
        if not tenant:
            return Response(
                {"detail": "No se pudo determinar el tenant actual."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            data = get_contabilidad_resumen(tenant, user)
            serializer = ContabilidadResumenSerializer(data)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(
                "ContabilidadResumenView: error cargando resumen para tenant=%s, error=%s",
                tenant.schema_name if tenant else 'none',
                str(e),
                exc_info=True
            )
            return Response(
                {"detail": "Error interno al cargar el resumen de contabilidad."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class LandingResumenView(APIView):
    """
    Endpoint para resumen de landing.
    
    GET /api/v1/core/landing/resumen/
    
    ⚠️ POLÍTICA: Información pública del tenant para landing page.
    ⚠️ PÚBLICO: AllowAny para que la landing page funcione sin autenticación.
    """
    permission_classes = [AllowAny]
    authentication_classes = []  # No requiere autenticación
    
    def get(self, request, *args, **kwargs):
        tenant = getattr(request, 'tenant', None)
        
        if not tenant:
            return Response(
                {"detail": "No se pudo determinar el tenant actual."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            data = get_landing_resumen(tenant)
            serializer = LandingResumenSerializer(data)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(
                "LandingResumenView: error cargando resumen para tenant=%s, error=%s",
                tenant.schema_name if tenant else 'none',
                str(e),
                exc_info=True
            )
            return Response(
                {"detail": "Error interno al cargar el resumen de landing."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CoreLandingInfoView(APIView):
    """
    Endpoint Core para información pública del tenant (Landing).
    
    GET /api/v1/core/landing/info/
    
    ⚠️ POLÍTICA v2.30: Fachada Core que consume landing_adapter
    Permite acceso anónimo para landing page.
    """
    permission_classes = [AllowAny]
    authentication_classes = []  # No requiere autenticación
    
    def get(self, request, *args, **kwargs):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response(
                {"detail": "No se pudo determinar el tenant actual."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            data = get_public_info_from_landing(request)
            serializer = TenantPublicInfoSerializer(data['tenant'], context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(
                "CoreLandingInfoView: error cargando info de landing para tenant=%s, error=%s",
                tenant.schema_name if tenant else 'none',
                str(e),
                exc_info=True
            )
            return Response(
                {"detail": "Error interno al cargar la información de landing."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CoreLandingActivateView(APIView):
    """
    Endpoint Core para activación de owner (Landing).
    
    GET|POST /api/v1/core/landing/auth/activate/?token=...
    
    ⚠️ POLÍTICA v2.30: Fachada Core que consume landing_adapter
    Permite acceso anónimo para activación.
    """
    permission_classes = [AllowAny]
    authentication_classes = []  # No requiere autenticación
    
    def get(self, request, *args, **kwargs):
        token = request.query_params.get('token')
        if not token:
            return Response(
                {"detail": "Token de activación no proporcionado."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            result = verify_activation_via_landing(request, token)
            return Response(result, status=status.HTTP_200_OK)
        except LandingInvalidTokenError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except LandingUserNotFoundError as e:
            return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except LandingTenantMismatchError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except LandingAlreadyActivatedError as e:
            return Response({
                "detail": str(e),
                "redirect_url": "/static/tenant/landing/login.html",
                "login_api_url": "/api/v1/core/auth/login/",
            }, status=status.HTTP_409_CONFLICT)
        except Exception as e:
            logger.error(
                "CoreLandingActivateView (GET): error verificando token para tenant=%s, error=%s",
                getattr(request, 'tenant', None).schema_name if getattr(request, 'tenant', None) else 'none',
                str(e),
                exc_info=True
            )
            return Response(
                {"detail": "Error interno al verificar el token de activación."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def post(self, request, *args, **kwargs):
        token = request.query_params.get('token')
        password_1 = request.data.get('password1')
        password_2 = request.data.get('password2')
        
        if not token:
            return Response(
                {"detail": "Token de activación no proporcionado."},
                status=status.HTTP_400_BAD_REQUEST
            )
        if not password_1 or not password_2:
            return Response(
                {"detail": "Ambas contraseñas son requeridas."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            result = process_activation_via_landing(request, token, password_1, password_2)
            return Response(result, status=status.HTTP_200_OK)
        except LandingInvalidTokenError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except LandingUserNotFoundError as e:
            return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except LandingTenantMismatchError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except LandingAlreadyActivatedError as e:
            return Response({
                "detail": str(e),
                "redirect_url": "/static/tenant/landing/login.html",
                "login_api_url": "/api/v1/core/auth/login/",
            }, status=status.HTTP_409_CONFLICT)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(
                "CoreLandingActivateView (POST): error procesando activación para tenant=%s, error=%s",
                getattr(request, 'tenant', None).schema_name if getattr(request, 'tenant', None) else 'none',
                str(e),
                exc_info=True
            )
            return Response(
                {"detail": "Error interno al procesar la activación."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CoreLoginView(APIView):
    """
    Endpoint Core para login.
    
    POST /api/v1/core/auth/login/
    
    ⚠️ POLÍTICA: Fachada Core que consume core.services.auth
    """
    permission_classes = [AllowAny]
    authentication_classes = []  # No requiere autenticación
    
    def post(self, request, *args, **kwargs):
        tenant = getattr(request, 'tenant', None)
        
        if not tenant:
            return Response(
                {"detail": "No se pudo determinar el tenant actual."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        identifier = request.data.get('email') or request.data.get('username')
        password = request.data.get('password')
        
        if not identifier or not password:
            return Response(
                {"detail": "Email/username y contraseña son requeridos."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            result = login_user(tenant, identifier, password)
            # Loguear usuario en la sesión
            login(request, result['user'])
            return Response({
                "detail": f"Bienvenido a {tenant.nombre}",
                "redirect_url": result['redirect_url'],
                "user": {
                    "id": result['user'].id,
                    "email": result['user'].email,
                    "name": result['user'].get_full_name() or result['user'].email,
                },
                "tenant": {
                    "id": tenant.id,
                    "nombre": tenant.nombre,
                    "schema_name": tenant.schema_name,
                },
            }, status=status.HTTP_200_OK)
        except InvalidCredentialsError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_401_UNAUTHORIZED
            )
        except NoMembershipError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        except AuthTenantNotFoundError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(
                "CoreLoginView: error inesperado: tenant=%s, error=%s",
                tenant.schema_name if tenant else 'none',
                str(e),
                exc_info=True
            )
            return Response(
                {"detail": "Error interno al procesar el login. Por favor, intenta nuevamente."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CoreLogoutView(APIView):
    """
    Endpoint Core para logout.
    
    POST /api/v1/core/auth/logout/ (preferido, con CSRF)
    GET  /api/v1/core/auth/logout/ (compatible, para enlaces directos)
    
    ⚠️ POLÍTICA: Fachada Core que consume core.services.auth
    ⚠️ v2.30: Soporta GET para compatibilidad con enlaces <a href> en templates.
    """
    permission_classes = [AllowAny]  # Permitir logout incluso sin autenticación (idempotente)
    authentication_classes = []
    
    def _process_logout(self, request):
        """
        Procesa el logout (lógica compartida entre GET y POST).
        
        Returns:
            Response: Respuesta con redirect_url o error
        """
        tenant = getattr(request, 'tenant', None)
        
        if not tenant:
            return Response(
                {"detail": "No se pudo determinar el tenant actual."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            result = logout_user(tenant, request)
            redirect_url = result['redirect_url']
            
            # Si es GET, redirigir directamente (mejor UX para enlaces)
            # Si es POST, retornar JSON (API-First)
            if request.method == 'GET':
                from django.shortcuts import redirect
                return redirect(redirect_url)
            
            return Response({
                "detail": "Sesión finalizada.",
                "redirect_url": redirect_url
            }, status=status.HTTP_200_OK)
        except AuthTenantNotFoundError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(
                "CoreLogoutView: error inesperado: tenant=%s, error=%s",
                tenant.schema_name if tenant else 'none',
                str(e),
                exc_info=True
            )
            return Response(
                {"detail": "Error interno al procesar el logout."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def get(self, request, *args, **kwargs):
        """
        GET /api/v1/core/auth/logout/
        
        ⚠️ v2.30: Soporte para enlaces directos <a href> en templates.
        Redirige directamente a la URL de logout después de cerrar sesión.
        """
        return self._process_logout(request)
    
    def post(self, request, *args, **kwargs):
        """
        POST /api/v1/core/auth/logout/
        
        ⚠️ PREFERIDO: Método recomendado para logout desde JavaScript (con CSRF).
        Retorna JSON con redirect_url.
        """
        return self._process_logout(request)


class PasswordResetRequestView(APIView):
    """
    Endpoint Core para solicitar reset de contraseña.
    
    POST /api/v1/core/auth/password-reset/request/
    
    ⚠️ POLÍTICA v2.30: Fachada Core que consume core.services.auth_service
    ⚠️ CSRF: Endpoint público, no requiere CSRF token (usuarios no autenticados)
    """
    permission_classes = [AllowAny]
    authentication_classes = []  # No requiere autenticación
    
    # ⚠️ CRÍTICO: Eximir de CSRF para permitir requests desde páginas estáticas sin sesión
    # Este endpoint es público y debe funcionar sin autenticación ni CSRF
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        tenant = getattr(request, 'tenant', None)
        
        if not tenant:
            return Response(
                {"detail": "No se pudo determinar el tenant actual."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        email_or_username = request.data.get('email') or request.data.get('username')
        
        if not email_or_username:
            return Response(
                {"detail": "Email o username es requerido."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            logger.info(
                "PasswordResetRequestView: Solicitud de reset recibida - email=%s, tenant=%s",
                email_or_username, tenant.schema_name if tenant else 'none'
            )
            result = password_reset_request(email_or_username, tenant)
            logger.info(
                "PasswordResetRequestView: Reset procesado exitosamente - email=%s, tenant=%s",
                email_or_username, tenant.schema_name if tenant else 'none'
            )
            return Response(result, status=status.HTTP_200_OK)
        except UserNotFoundError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(
                "PasswordResetRequestView: error inesperado: tenant=%s, error=%s",
                tenant.schema_name if tenant else 'none',
                str(e),
                exc_info=True
            )
            # Idempotente: retornar respuesta genérica
            return Response(
                {"detail": "Si el email existe y tiene acceso a este tenant, recibirás un correo con instrucciones."},
                status=status.HTTP_200_OK
            )


class PasswordResetValidateView(APIView):
    """
    Endpoint Core para validar token de reset de contraseña.
    
    POST /api/v1/core/auth/password-reset/validate/
    
    ⚠️ POLÍTICA v2.30: Fachada Core que consume core.services.auth_service
    """
    permission_classes = [AllowAny]
    authentication_classes = []  # No requiere autenticación
    
    def post(self, request, *args, **kwargs):
        tenant = getattr(request, 'tenant', None)
        
        if not tenant:
            return Response(
                {"detail": "No se pudo determinar el tenant actual."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Aceptar uid o uidb64 (unificar)
        uid = request.data.get('uid') or request.data.get('uidb64')
        token = request.data.get('token')
        
        if not uid or not token:
            return Response(
                {"detail": "Token de reset inválido o expirado."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            result = password_reset_validate(uid, token, tenant)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            error_msg = str(e)
            logger.warning(
                "PasswordResetValidateView: error validando token: tenant=%s, error=%s",
                tenant.schema_name if tenant else 'none',
                error_msg
            )
            return Response(
                {"detail": error_msg if error_msg else "Token de reset inválido o expirado."},
                status=status.HTTP_400_BAD_REQUEST
            )


class PasswordResetConfirmView(APIView):
    """
    Endpoint Core para confirmar reset de contraseña.
    
    POST /api/v1/core/auth/password-reset/confirm/
    
    ⚠️ POLÍTICA v2.30: Fachada Core que consume core.services.auth_service
    Retorna redirect_url="/workspace/#landing"
    """
    permission_classes = [AllowAny]
    authentication_classes = []  # No requiere autenticación
    
    def post(self, request, *args, **kwargs):
        tenant = getattr(request, 'tenant', None)
        
        if not tenant:
            return Response(
                {"detail": "No se pudo determinar el tenant actual."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Aceptar uid o uidb64 (unificar)
        uid = request.data.get('uid') or request.data.get('uidb64')
        token = request.data.get('token')
        password1 = request.data.get('password1')
        password2 = request.data.get('password2')
        
        if not uid or not token:
            return Response(
                {"detail": "Token de reset inválido o expirado."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not password1 or not password2:
            return Response(
                {"detail": "Las contraseñas son requeridas."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if password1 != password2:
            return Response(
                {"password2": ["Las contraseñas no coinciden."]},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if len(password1) < 8:
            return Response(
                {"password1": ["La contraseña debe tener al menos 8 caracteres."]},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            result = password_reset_confirm(uid, token, password1, tenant)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            error_msg = str(e)
            logger.error(
                "PasswordResetConfirmView: error confirmando reset: tenant=%s, error=%s",
                tenant.schema_name if tenant else 'none',
                error_msg,
                exc_info=True
            )
            return Response(
                {"detail": error_msg if error_msg else "Error al establecer la nueva contraseña. Por favor, intenta nuevamente."},
                status=status.HTTP_400_BAD_REQUEST if 'inválido' in error_msg.lower() or 'expirado' in error_msg.lower() else status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# --- Endpoints opcionales para ingesta por correo (Fase 4) ---
class CoreMailIngestionRunAPIView(APIView):
    """
    POST /api/v1/core/maildigester/run/
    
    Encola ejecución de ingesta de facturas desde correo.
    
    ⚠️ ORQUESTACIÓN: Core API consume servicios de facturas sin HTTP interno.
    ⚠️ PERMISOS: IsAuthenticated (TODO: permisos finos por TenantMembership)
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        # ⚠️ IMPORT LAZY: Evita ciclos de importación
        from apps.tenant.core.services.facturas_maildigester_adapter import core_run_mail_ingestion
        
        payload = request.data or {}
        
        try:
            data = core_run_mail_ingestion(
                user=request.user,
                config_id=int(payload.get("config_id")),
                limit_messages=int(payload.get("limit_messages", 50)),
            )
            return Response(data, status=status.HTTP_202_ACCEPTED)
        except Exception as e:
            return Response(
                {"error": "internal_error", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class CoreMailIngestionRunsListAPIView(APIView):
    """
    GET /api/v1/core/maildigester/runs/
    
    Lista ejecuciones recientes de ingesta por correo.
    
    ⚠️ ORQUESTACIÓN: Core API consume servicios de facturas sin HTTP interno.
    ⚠️ PERMISOS: IsAuthenticated (TODO: permisos finos)
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request, *args, **kwargs):
        # ⚠️ IMPORT LAZY: Evita ciclos de importación
        from apps.tenant.core.services.facturas_maildigester_adapter import core_list_mail_runs
        return Response({"results": core_list_mail_runs()})


class CoreMailIngestionConfigsListAPIView(APIView):
    """
    GET /api/v1/core/maildigester/configs/
    
    Lista configuraciones activas de buzones de correo.
    
    ⚠️ ORQUESTACIÓN: Core API consume servicios de empresa (SSoT) sin HTTP interno.
    ⚠️ PERMISOS: IsAuthenticated (TODO: permisos finos)
    ⚠️ SSoT: Las configuraciones se obtienen desde empresa (MailInboxConfig)
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request, *args, **kwargs):
        # ⚠️ IMPORT LAZY: Evita ciclos de importación
        from apps.tenant.core.services.facturas_maildigester_adapter import core_list_mail_configs
        return Response({"results": core_list_mail_configs()})


class CoreMailIngestionConfigTestAPIView(APIView):
    """
    POST /api/v1/core/maildigester/configs/test/
    
    Prueba conexión a un buzón de correo sin persistir configuración.
    
    ⚠️ DIAGNÓSTICO: Solo prueba conexión, no persiste nada.
    ⚠️ SEGURIDAD: No expone password en respuestas.
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        # ⚠️ IMPORT LAZY: Evita ciclos de importación
        from apps.tenant.core.services.facturas_maildigester_adapter import core_test_mailbox_connection
        
        payload = request.data or {}
        
        result = core_test_mailbox_connection(
            provider=payload.get("provider"),
            host=payload.get("host"),
            port=payload.get("port"),
            protocol=payload.get("protocol", "imap"),
            ssl=payload.get("ssl"),
            starttls=payload.get("starttls"),
            username=payload.get("username", ""),
            password=payload.get("password", ""),
            mailbox=payload.get("mailbox", "INBOX"),
            email_address=payload.get("email_address")
        )
        
        if result["ok"]:
            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)


class CoreMailIngestionRunStopAPIView(APIView):
    """
    POST /api/v1/core/maildigester/run/{run_id}/stop/
    
    Cancela una ejecución de ingesta de correo.
    
    ⚠️ REVOCACIÓN: Usa celery.app.control.revoke para cancelar la tarea.
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request, run_id, *args, **kwargs):
        # ⚠️ IMPORT LAZY: Evita ciclos de importación
        from apps.tenant.core.services.facturas_maildigester_adapter import core_stop_mail_ingestion_run
        
        payload = request.data or {}
        force = payload.get("force", False)
        
        result = core_stop_mail_ingestion_run(int(run_id), force=force)
        
        if result["ok"]:
            return Response(result, status=status.HTTP_202_ACCEPTED)
        else:
            # 409 si ya terminó, 404 si no existe
            if "no encontrada" in result["message"]:
                return Response(result, status=status.HTTP_404_NOT_FOUND)
            else:
                return Response(result, status=status.HTTP_409_CONFLICT)


class CoreMailIngestionRunDetailsAPIView(APIView):
    """
    GET /api/v1/core/maildigester/run/{run_id}/details/
    
    Obtiene detalles de una ejecución de ingesta, incluyendo lista de XMLs detectados.
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request, run_id, *args, **kwargs):
        # ⚠️ IMPORT LAZY: Evita ciclos de importación
        from apps.tenant.core.services.facturas_maildigester_adapter import core_get_mail_ingestion_run_details
        
        result = core_get_mail_ingestion_run_details(int(run_id))
        
        if result["status"] is None:
            return Response(result, status=status.HTTP_404_NOT_FOUND)
        
        return Response(result, status=status.HTTP_200_OK)


class CoreMailIngestionRunDeleteAPIView(APIView):
    """
    DELETE /api/v1/core/maildigester/run/{run_id}/
    
    Elimina una ejecución de ingesta de correo.
    
    ⚠️ SEGURIDAD: Solo permite eliminar ejecuciones terminadas (SUCCESS, FAILED, CANCELED, ABORTED).
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    
    def delete(self, request, run_id, *args, **kwargs):
        # ⚠️ IMPORT LAZY: Evita ciclos de importación
        from apps.tenant.core.services.facturas_maildigester_adapter import core_delete_mail_ingestion_run
        
        result = core_delete_mail_ingestion_run(int(run_id))
        
        if result["ok"]:
            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
