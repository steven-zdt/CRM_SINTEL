"""
Permisos personalizados para APIs de tenants.

⚠️ SEGURIDAD: Cross-Tenant Isolation
- Garantiza que los usuarios solo puedan acceder a datos de tenants donde tienen membresía activa.
- Valida TenantMembership antes de permitir cualquier operación.
"""
from rest_framework import permissions
from django.core.exceptions import PermissionDenied
from apps.tenant.empresa.permissions import IsTenantAdmin


class IsTenantMember(permissions.BasePermission):
    """
    Permiso personalizado que verifica que el usuario tenga membresía activa
    en el tenant actual (request.tenant).
    
    ⚠️ CRÍTICO: Este permiso debe aplicarse a todas las APIs de tenant
    para garantizar el aislamiento cross-tenant.
    
    Uso:
        class MyViewSet(viewsets.ModelViewSet):
            permission_classes = [IsTenantMember]
    """
    
    def has_permission(self, request, view):
        """
        Verifica que el usuario tenga membresía activa en el tenant actual.
        
        Retorna:
        - True: Si el usuario tiene membresía activa en request.tenant
        - False: Si el usuario no tiene membresía o no está autenticado
        
        ⚠️ IMPORTANTE: request.tenant es inyectado por TenantMainMiddleware.
        Si no existe, se asume que estamos en el esquema 'public' y se permite el acceso
        (para APIs públicas como /api/v1/landing/info/).
        """
        # Si no está autenticado, no tiene permisos
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Obtener el tenant del request (inyectado por TenantMainMiddleware)
        tenant = getattr(request, 'tenant', None)
        
        # Si no hay tenant, estamos en el esquema 'public' (APIs públicas)
        # Permitir acceso (las APIs públicas tienen su propio control de permisos)
        if not tenant:
            return True
        
        # Verificar que el usuario tenga membresía activa en este tenant
        # TenantMembership está en el esquema 'public', así que necesitamos
        # cambiar temporalmente al esquema public para consultar
        from django.db import connection
        from django_tenants.utils import get_public_schema_name
        
        # Guardar el esquema actual
        current_schema = connection.schema_name
        
        try:
            # Cambiar al esquema public para consultar TenantMembership
            connection.set_schema_to_public()
            
            # Importar aquí para evitar problemas de importación circular
            from apps.public.tenants.models import TenantMembership
            
            # Verificar membresía activa
            membership = TenantMembership.objects.filter(
                client=tenant,
                user=request.user,
                is_active=True  # Solo membresías activas
            ).first()
            
            # Restaurar el esquema original
            connection.set_schema(current_schema)
            
            # Si existe membresía activa, el usuario tiene acceso
            return membership is not None
            
        except Exception as e:
            # En caso de error, restaurar el esquema y denegar acceso
            connection.set_schema(current_schema)
            return False
    
    def has_object_permission(self, request, view, obj):
        """
        Verifica permisos a nivel de objeto.
        
        Por defecto, si el usuario tiene membresía en el tenant,
        tiene acceso a todos los objetos del tenant (django-tenants
        ya aísla los datos por esquema).
        
        Si necesitas permisos más granulares, sobrescribe este método
        en tu ViewSet.
        """
        # Si tiene permisos a nivel de vista, tiene permisos a nivel de objeto
        return self.has_permission(request, view)


class IsTenantAdminOrReadOnly(permissions.BasePermission):
    """
    Permiso que permite lectura a usuarios autenticados y escritura solo a ADMIN/STAFF.
    
    ⚠️ IMPORTANTE: Para ViewSets con ENFORCED MODE, este permiso permite todas las operaciones
    y la verificación real se hace en _check_enforced_mode dentro de cada método.
    Esto permite que el método se ejecute y retorne 405 con un mensaje claro.
    
    Uso:
        class MyViewSet(viewsets.ModelViewSet):
            permission_classes = [IsAuthenticated, IsTenantAdminOrReadOnly]
    """
    message = "Solo usuarios ADMIN/STAFF del tenant pueden crear/editar/eliminar."
    
    def has_permission(self, request, view):
        from rest_framework.permissions import SAFE_METHODS
        
        user = getattr(request, "user", None)
        if not (user and user.is_authenticated):
            return False
        
        # Lectura siempre permitida
        if request.method in SAFE_METHODS:
            return True
        
        # Para mutaciones, si el ViewSet tiene _check_enforced_mode, permitir el acceso
        # y dejar que el método maneje la verificación (retornará 405 si no tiene permisos)
        if hasattr(view, '_check_enforced_mode'):
            return True  # Permitir acceso, _check_enforced_mode verificará en el método
        
        # Si no tiene _check_enforced_mode, usar verificación tradicional
        return IsTenantAdmin().has_permission(request, view)
