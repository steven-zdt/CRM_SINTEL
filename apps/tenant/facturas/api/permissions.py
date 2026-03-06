"""
Permisos personalizados para la app facturas (API-First).

⚠️ v2.30: Usa TenantMembership para verificar rol, no is_staff global.
Único archivo de permisos para facturas (API-First).
"""
from rest_framework.permissions import BasePermission, SAFE_METHODS
from django.core.exceptions import ImproperlyConfigured
from django.db import connection
from django_tenants.utils import get_public_schema_name
import logging

logger = logging.getLogger(__name__)


class IsTenantAdminOrReadOnly(BasePermission):
    """
    Permiso que permite lectura a usuarios autenticados y escritura solo a ADMIN/STAFF.
    
    ⚠️ v2.30: Usa TenantMembership para verificar rol del usuario en el tenant actual.
    No depende de is_staff global, sino del rol en TenantMembership.
    
    ⚠️ POLÍTICA:
    - GET/HEAD/OPTIONS: Permitido a cualquier usuario autenticado con membresía
    - POST/PUT/PATCH/DELETE: Solo ADMIN/STAFF según TenantMembership
    """
    message = "Solo usuarios ADMIN/STAFF del tenant pueden crear/editar/eliminar Facturas."
    
    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        
        if not (user and user.is_authenticated):
            logger.info("IsTenantAdminOrReadOnly: usuario no autenticado")
            return False
        
        # Lectura: permitida a todos los usuarios autenticados con membresía
        if request.method in SAFE_METHODS:
            return True
        
        # Escritura: solo ADMIN/STAFF
        tenant = getattr(request, "tenant", None)
        if tenant is None:
            logger.error(
                "IsTenantAdminOrReadOnly: request.tenant es None (middleware/TENANT_URLCONF no resuelto)"
            )
            raise ImproperlyConfigured("Tenant no resuelto en request.")
        
        # Verificar membresía activa en el tenant
        current_schema = connection.schema_name
        public_schema = get_public_schema_name()
        
        try:
            # Cambiar al esquema public para consultar TenantMembership
            if current_schema != public_schema:
                connection.set_schema_to_public()
            
            # Importar aquí para evitar problemas de importación circular
            from apps.public.tenants.models import TenantMembership
            
            # Buscar membresía activa del usuario en el tenant con rol ADMIN/STAFF
            membership = TenantMembership.objects.filter(
                client=tenant,
                user=user,
                rol__in=["ADMIN", "STAFF"],
                is_active=True
            ).first()
            
            # Restaurar el esquema original
            connection.set_schema(current_schema)
            
            ok = membership is not None
            
            if not ok:
                logger.warning(
                    "IsTenantAdminOrReadOnly: permiso denegado | user=%s | tenant=%s | motivo=sin_rol_admin_staff",
                    getattr(user, "email", user.pk),
                    getattr(tenant, "schema_name", "?")
                )
            
            return ok
            
        except Exception as e:
            # En caso de error, restaurar el esquema y denegar acceso
            connection.set_schema(current_schema)
            logger.error(
                "IsTenantAdminOrReadOnly: error verificando permisos | user=%s | tenant=%s | error=%s",
                getattr(user, "email", user.pk) if user else "None",
                getattr(tenant, "schema_name", "?") if tenant else "None",
                str(e),
                exc_info=True
            )
            return False
