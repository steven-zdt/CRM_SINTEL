"""
ViewSets para la app tenants.

⚠️ IMPORTANTE: Solo administradores pueden gestionar tenants.
- Autenticación: SessionAuthentication para permitir cookies de sesión desde la UI

Referencia: https://www.django-rest-framework.org/api-guide/viewsets/
"""
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.authentication import SessionAuthentication
from django.core.exceptions import ValidationError
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from apps.public.tenants.models import Client, Domain
from apps.public.tenants.api.serializers import ClientSerializer, DomainSerializer, OnboardTenantWithOwnerSerializer
from apps.public.tenants.api.filters import ClientFilter
from apps.config.api.pagination import StandardResultsSetPagination


class ClientViewSet(viewsets.ModelViewSet):
    """
    ViewSet CRUD completo para Client (solo administradores).
    
    ⚠️ IMPORTANTE: 
    - CRUD completo para uso administrativo exclusivo (requiere IsAdminUser)
    - La creación de tenants puede hacerse mediante el servicio de onboarding o por API
    - Todas las operaciones requieren permisos de administrador
    - Autenticación: SessionAuthentication (cookies de sesión desde UI)
    """
    authentication_classes = [SessionAuthentication]
    # Queryset optimizado: solo campos necesarios, sin prefetch pesado de membresías
    # ⚠️ OPTIMIZACIÓN: No hacer prefetch de membresías para evitar 500 y reducir carga
    # Para API pública/admin: usar only() para reducir carga
    queryset = Client.objects.only(
        "id", "schema_name", "nombre", "created_on", "is_active", 
        "on_trial", "paid_until"
    ).prefetch_related('domains').order_by("-created_on")
    serializer_class = ClientSerializer
    permission_classes = [permissions.IsAdminUser]  # Solo admins
    
    def get_queryset(self):
        """
        Queryset optimizado según la acción.
        
        ⚠️ OPTIMIZACIÓN: No hacer prefetch de membresías para evitar 500 y reducir carga.
        Si se necesitan membresías en admin, usar un serializer separado.
        """
        return super().get_queryset()
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ClientFilter  # Usar FilterSet personalizado para booleanos
    search_fields = ['nombre', 'schema_name']
    ordering_fields = ['nombre', 'created_on', 'paid_until']
    ordering = ['-created_on']
    
    @action(detail=False, methods=['post'], url_path='onboard', url_name='onboard')
    def onboard(self, request):
        """
        Endpoint para onboarding completo de un tenant con propietario.
        
        ⚠️ CONTRATO ESTABLE: Retorna dict {"client_id", "domain", "membership_id", "login_url"} con 201
        Aunque el seed de perfil falle, siempre retorna login_url si User, Client, Domain y Membership se crearon.
        
        Crea un tenant completo con:
        - Usuario global (public) - idempotente por email, set_unusable_password() (v2.29: sin password en onboarding)
        - Client (tenant) - auto_create_schema=True crea esquema + migra TENANT_APPS automáticamente
        - Domain (dominio principal) - sin puerto ni www (normalizado)
        - TenantMembership (usuario propietario) - en public, rol=ADMIN, is_primary_admin=True
        - (Opcional) Seed de perfil si la tabla existe - dentro de schema_context, solo si tabla existe
        
        ⚠️ PERMISOS: Requiere IsAdminUser (solo staff puede crear tenants)
        
        Payload esperado:
        {
            "nombre": "Empresa X",  # Requerido
            "schema_name": "empresa_x",  # Requerido
            "dominio_fqdn": "empresa-x.localhost",  # Opcional (se autogenera como <schema>.<TENANT_DOMAIN_BASE>)
            "owner_email": "owner@empresa-x.com",  # Requerido (si no se proporciona admin_user_id)
            # ⚠️ v2.29: owner_password ELIMINADO - NO se acepta password en onboarding
            "admin_user_id": 1,  # Opcional (alternativa a owner_email)
            "owner_is_staff": true,  # Opcional, default: true
            "owner_is_active": true,  # Opcional, default: true
            "paid_until": "2024-12-31",  # Opcional
            "on_trial": true  # Opcional, default: true
        }
        
        Returns:
            Response 201 Created con dict: {
                "client_id": int,
                "domain": str,
                "membership_id": int,
                "login_url": str
            }
        
        Raises:
            Response 400 Bad Request: Si hay errores de validación (ValidationError, ValueError)
            Response 403 Forbidden: Si el usuario no es staff (IsAdminUser)
            Response 500 Internal Server Error: Si hay errores inesperados
        """
        from apps.services.onboarding.empresa_service import crear_tenant_con_owner
        from apps.public.tenants.api.serializers import OnboardTenantWithOwnerSerializer
        
        import logging
        logger = logging.getLogger(__name__)
        
        serializer = OnboardTenantWithOwnerSerializer(data=request.data)
        if not serializer.is_valid():
            # Errores de validación del serializer (campos requeridos, formatos, etc.)
            errors = serializer.errors
            # Log detallado por campo
            for field, field_errors in errors.items():
                logger.warning(
                    "Onboarding 400 - Campo '%s': %s | Payload recibido: nombre=%s, schema_name=%s, dominio_fqdn=%s, owner_email=%s",
                    field,
                    field_errors,
                    request.data.get('nombre', 'N/A'),
                    request.data.get('schema_name', 'N/A'),
                    request.data.get('dominio_fqdn', 'N/A'),
                    request.data.get('owner_email', 'N/A'),
                )
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Crear tenant usando el servicio (retorna dict estable)
            # ⚠️ CONTRATO ESTABLE: Siempre retorna dict con client_id, domain, membership_id, login_url
            # Aunque el seed de perfil falle, el onboarding debe retornar 201 con login_url
            payload = crear_tenant_con_owner(**serializer.validated_data)
            logger.info(
                "✅ Onboarding exitoso: client_id=%s, domain=%s, membership_id=%s",
                payload.get('client_id'),
                payload.get('domain'),
                payload.get('membership_id'),
            )
            return Response(payload, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            # Errores de validación (dominio duplicado, schema inválido, etc.)
            error_detail = str(e)
            logger.warning(
                "Onboarding 400 - ValidationError: %s | Payload: nombre=%s, schema_name=%s, dominio_fqdn=%s",
                error_detail,
                serializer.validated_data.get('nombre', 'N/A'),
                serializer.validated_data.get('schema_name', 'N/A'),
                serializer.validated_data.get('dominio_fqdn', 'N/A'),
            )
            return Response(
                {'detail': error_detail},
                status=status.HTTP_400_BAD_REQUEST
            )
        except ValueError as e:
            # Errores de valor (campos requeridos faltantes, etc.)
            error_detail = str(e)
            logger.warning(
                "Onboarding 400 - ValueError: %s | Payload: nombre=%s, schema_name=%s, owner_email=%s",
                error_detail,
                serializer.validated_data.get('nombre', 'N/A'),
                serializer.validated_data.get('schema_name', 'N/A'),
                serializer.validated_data.get('owner_email', 'N/A'),
            )
            return Response(
                {'detail': error_detail},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            # Errores inesperados
            logger.error(
                "Onboarding 500 - Error inesperado: %s | Payload: %s",
                str(e),
                serializer.validated_data,
                exc_info=True
            )
            return Response(
                {'detail': 'Error al crear el tenant. Por favor, contacte al administrador.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'], url_path='toggle-active', url_name='toggle-active')
    def toggle_active(self, request, pk=None):
        """
        Activa o desactiva un tenant (toggle de is_active).
        
        ⚠️ CONTRATO: POST /api/public/v1/tenants/{id}/toggle-active/
        - Sin prefetch redundantes
        - Cambia is_active y retorna {"id", "is_active", "message"}
        
        Cambia el estado de is_active del tenant:
        - Si is_active=True → is_active=False (suspende)
        - Si is_active=False → is_active=True (activa)
        
        ⚠️ PERMISOS: Requiere IsAdminUser (solo staff puede cambiar estado de tenants)
        
        Returns:
            Response 200 OK con: {
                "id": int,
                "is_active": bool,
                "message": str
            }
        """
        try:
            client = self.get_object()
            client.is_active = not client.is_active
            client.save(update_fields=['is_active'])
            
            serializer = self.get_serializer(client)
            action = 'activado' if client.is_active else 'desactivado'
            
            return Response({
                'id': client.id,
                'is_active': client.is_active,
                'message': f'Tenant "{client.nombre}" {action} exitosamente'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error al cambiar estado del tenant: {str(e)}", exc_info=True)
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def destroy(self, request, *args, **kwargs):
        """
        Hard Delete de tenant (eliminación permanente).
        
        ⚠️ OPERACIÓN IRREVERSIBLE:
        - Elimina el esquema PostgreSQL del tenant (drop schema)
        - Elimina Client, Domain(s) y TenantMembership(s) del esquema public
        
        ⚠️ PRECONDICIONES OBLIGATORIAS:
        1. schema != 'public' (el tenant público NO puede eliminarse)
        2. is_active == False (el tenant debe estar suspendido antes de eliminarlo)
        
        ⚠️ MECANISMO:
        - Activar auto_drop_schema=True temporalmente
        - client.delete() para drop del esquema (mecanismo soportado por django-tenants)
        - Limpiar relaciones en public (Domains/Memberships) si no hay CASCADE
        
        ⚠️ PERMISOS: Requiere IsAdminUser (solo staff puede eliminar tenants)
        
        ⚠️ AUDITORÍA: Logs de seguridad registrados en logger 'security.tenants'
        
        Returns:
            Response 204 No Content si se elimina exitosamente
            Response 400 Bad Request si el tenant está activo
            Response 403 Forbidden si se intenta eliminar el tenant público
        
        Referencias:
        - django-tenants: https://django-tenants.readthedocs.io/en/latest/use.html
        - auto_drop_schema: https://django-tenants.readthedocs.io/en/latest/use.html#deleting-tenants
        """
        from apps.public.tenants.services.deletion_service import hard_delete_tenant
        
        try:
            client = self.get_object()
            
            # BLOQUEO ABSOLUTO DEL TENANT PÚBLICO (defensa en profundidad - capa API)
            from django_tenants.utils import get_public_schema_name
            public_schema = get_public_schema_name()
            if client.schema_name == public_schema:
                import logging
                logger = logging.getLogger('security.tenants')
                import datetime
                logger.critical(
                    f"🚨 API: INTENTO DE ELIMINAR TENANT PÚBLICO RECHAZADO | "
                    f"schema={public_schema} | "
                    f"user_id={request.user.id if request.user.is_authenticated else None} | "
                    f"ip={request.META.get('REMOTE_ADDR', 'unknown')} | "
                    f"time={datetime.datetime.now().isoformat()}"
                )
                return Response(
                    {
                        'error': 'El esquema público no puede eliminarse bajo ningún motivo.',
                        'detail': 'El tenant público es el núcleo del sistema y es indeletable.'
                    },
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Precondición: is_active == False
            if client.is_active:
                return Response(
                    {
                        'error': 'El tenant debe estar suspendido (is_active=False) antes de eliminarlo definitivamente.',
                        'detail': 'Primero desactiva el tenant usando el botón "Desactivar" o el endpoint /toggle-active/.'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Obtener ID del usuario que ejecuta la acción (para auditoría)
            actor_user_id = request.user.id if request.user.is_authenticated else None
            
            # Ejecutar hard delete
            hard_delete_tenant(client_id=client.id, actor_user_id=actor_user_id)
            
            return Response(
                {'message': f'Tenant "{client.nombre}" eliminado permanentemente'},
                status=status.HTTP_204_NO_CONTENT
            )
            
        except ValidationError as e:
            # Error de validación (incluye bloqueo de tenant público)
            error_msg = str(e)
            if 'público' in error_msg.lower() or 'public' in error_msg.lower():
                return Response(
                    {'error': error_msg},
                    status=status.HTTP_403_FORBIDDEN
                )
            return Response(
                {'error': error_msg},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error en hard delete tenant: {str(e)}", exc_info=True)
            return Response(
                {'error': f'Error al eliminar el tenant: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DomainViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet ReadOnly para Domain (solo administradores).
    
    ⚠️ IMPORTANTE: 
    - Solo lectura para uso administrativo
    - La creación de dominios debe hacerse mediante el servicio de onboarding
    """
    queryset = Domain.objects.all()
    serializer_class = DomainSerializer
    permission_classes = [permissions.IsAdminUser]  # Solo admins
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_primary', 'tenant']
    search_fields = ['domain']
    ordering_fields = ['domain', 'is_primary']
    ordering = ['domain']


# Lista de ViewSets para registro automático en el router
VIEWSETS = [
    (r'tenants', ClientViewSet, 'tenant'),
    (r'domains', DomainViewSet, 'domain'),
]
