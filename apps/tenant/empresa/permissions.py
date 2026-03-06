"""
Permisos personalizados para la app empresa.

⚠️ SEGURIDAD: Solo ADMIN/STAFF pueden crear/editar empresas.
⚠️ v2.30: Usa TenantMembership para verificar rol, no is_staff global.
"""
import logging
from rest_framework.permissions import BasePermission
from django.db import connection
from django_tenants.utils import get_public_schema_name

log = logging.getLogger("empresa.permissions")


class IsTenantAdmin(BasePermission):
    """
    Permiso que verifica que el usuario tenga rol ADMIN/STAFF del tenant.
    
    ⚠️ v2.30: Usa TenantMembership para verificar rol del usuario en el tenant actual.
    No depende de is_staff global, sino del rol en TenantMembership.
    
    ⚠️ POLÍTICA: Solo ADMIN/STAFF pueden crear/editar/eliminar empresas.
    Todos los usuarios autenticados pueden leer (GET/HEAD/OPTIONS).
    
    Uso:
        class EmpresaViewSet(viewsets.ModelViewSet):
            permission_classes = [IsAuthenticated, IsTenantAdmin]
    """
    message = "Solo usuarios ADMIN/STAFF del tenant pueden modificar Empresa."
    
    def has_permission(self, request, view):
        """
        Verifica permisos según el método HTTP.
        
        - GET/HEAD/OPTIONS: Permitido a cualquier usuario autenticado con membresía
        - POST/PUT/PATCH/DELETE: Solo ADMIN/STAFF según TenantMembership
        
        ⚠️ v2.30: Verifica rol desde TenantMembership, no is_staff global.
        """
        user = request.user
        
        if not (user and user.is_authenticated):
            return False
        
        # Obtener el tenant del request (inyectado por TenantMainMiddleware)
        tenant = getattr(request, 'tenant', None)
        
        # Si no hay tenant, estamos en el esquema 'public' (no aplica)
        if not tenant:
            return False
        
        # Verificar membresía activa en el tenant
        current_schema = connection.schema_name
        public_schema = get_public_schema_name()
        
        try:
            # Cambiar al esquema public para consultar TenantMembership
            if current_schema != public_schema:
                connection.set_schema_to_public()
            
            # Importar aquí para evitar problemas de importación circular
            from apps.public.tenants.models import TenantMembership
            
            # Buscar membresía activa del usuario en el tenant
            membership = TenantMembership.objects.filter(
                client=tenant,
                user=user,
                is_active=True
            ).first()
            
            # Restaurar el esquema original
            connection.set_schema(current_schema)
            
            # Si no hay membresía, no tiene permisos
            if not membership:
                return False
            
            # Lectura: permitida a todos los usuarios autenticados con membresía
            if request.method in ("GET", "HEAD", "OPTIONS"):
                return True
            
            # Escritura: solo ADMIN/STAFF según TenantMembership
            is_admin_staff = membership.rol in ("ADMIN", "STAFF")
            
            # ⚠️ v2.30: Logging para diagnóstico de 403
            if not is_admin_staff and request.method not in ("GET", "HEAD", "OPTIONS"):
                log.warning(
                    f"403 Forbidden: Usuario {user.id} ({user.email}) intentó {request.method} "
                    f"en Empresa pero tiene rol '{membership.rol}' (requiere ADMIN/STAFF). "
                    f"Tenant: {tenant.schema_name}"
                )
            
            return is_admin_staff
            
        except Exception as e:
            # En caso de error, restaurar el esquema y denegar acceso
            connection.set_schema(current_schema)
            log.error(
                f"Error verificando permisos IsTenantAdmin para usuario {user.id if user else 'None'}: {e}",
                exc_info=True
            )
            return False
