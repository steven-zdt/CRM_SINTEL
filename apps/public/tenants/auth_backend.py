"""
Backend de autenticación tenant-aware.

⚠️ SEGURIDAD CRÍTICA: Este backend intercepta el proceso de autenticación
estándar de Django para validar que el usuario tenga derecho a acceder
al tenant actual, incluso si las credenciales (usuario/password) son correctas.

Flujo de validación:
1. Valida credenciales usando el backend estándar
2. Si las credenciales son inválidas, retorna None
3. Si no hay contexto de tenant (request.tenant), permite el acceso (fallback para comandos de consola)
4. Si el tenant es 'public', permite el acceso (login global en dominio principal)
5. Valida que el usuario tenga TenantMembership activa para el tenant actual
6. Si tiene membresía, retorna el usuario (login exitoso)
7. Si NO tiene membresía, retorna None (login fallido, aunque el password sea correcto)

Uso:
    AUTHENTICATION_BACKENDS = [
        'apps.public.tenants.auth_backend.TenantAwareBackend',
        'django.contrib.auth.backends.ModelBackend',  # Fallback opcional
    ]
"""
import logging
from django.contrib.auth.backends import ModelBackend
from django.db import connection
from django_tenants.utils import get_public_schema_name

logger = logging.getLogger(__name__)


class TenantAwareBackend(ModelBackend):
    """
    Backend de autenticación que valida membresía del tenant.
    
    ⚠️ SEGURIDAD: Este backend previene el acceso cross-tenant validando
    que el usuario tenga una TenantMembership activa para el tenant actual
    antes de permitir el login, incluso si las credenciales son correctas.
    
    ⚠️ IMPORTANTE: Este backend debe ir ANTES de ModelBackend en
    AUTHENTICATION_BACKENDS para que filtre primero.
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Autentica un usuario validando credenciales Y membresía del tenant.
        
        Args:
            request: HttpRequest object (puede ser None para comandos de consola)
            username: Username o email del usuario
            password: Password del usuario
            **kwargs: Argumentos adicionales
        
        Returns:
            User: Si las credenciales son válidas Y el usuario tiene membresía
            None: Si las credenciales son inválidas O el usuario NO tiene membresía
        """
        # Paso 1: Validar credenciales usando el backend estándar
        # Si las credenciales son inválidas, retornar None inmediatamente
        user = super().authenticate(request, username=username, password=password, **kwargs)
        
        if user is None:
            # Credenciales inválidas, no continuar
            return None
        
        # Paso 2: Contexto del Request
        # Si request es None o no tiene tenant, permitir acceso (fallback para comandos de consola)
        # En web siempre habrá tenant gracias a TenantMainMiddleware
        if request is None or not hasattr(request, 'tenant') or request.tenant is None:
            # Comando de consola o contexto sin tenant: permitir acceso
            return user
        
        tenant = request.tenant
        
        # Paso 3: Esquema Público
        # Si el tenant es 'public', permitir acceso (login global en dominio principal)
        if tenant.schema_name == get_public_schema_name():
            return user
        
        # Paso 4: Validación de Membresía
        # Buscar TenantMembership activa para este usuario y tenant
        # TenantMembership está en SHARED_APPS, así que vive en el esquema public
        current_schema = connection.schema_name
        
        try:
            # Cambiar al esquema public para consultar TenantMembership
            connection.set_schema_to_public()
            
            from apps.public.tenants.models import TenantMembership
            
            # Buscar membresía activa (validar is_active=True)
            ok = TenantMembership.objects.filter(
                client=tenant,
                user=user,
                is_active=True
            ).exists()
            
            # Restaurar el esquema original
            connection.set_schema(current_schema)
            
            if ok:
                # Usuario tiene membresía activa: Login Exitoso
                return user
            else:
                # Usuario NO tiene membresía activa: Login Fallido
                # Log de seguridad para detectar intentos de acceso cruzado
                logger.warning(
                    f"Intento de acceso cruzado detectado: Usuario '{user.email}' "
                    f"(ID: {user.id}) intentó acceder al tenant '{tenant.schema_name}' "
                    f"({tenant.nombre}) sin membresía activa."
                )
                return None
                
        except Exception as e:
            # En caso de error inesperado, restaurar esquema y rechazar login por seguridad
            connection.set_schema(current_schema)
            logger.error(
                f"Error al validar membresía en TenantAwareBackend para usuario '{user.email}' "
                f"y tenant '{tenant.schema_name}': {e}"
            )
            # Por seguridad, rechazar el login si hay error
            return None
    
    def get_user(self, user_id):
        """
        Obtiene un usuario por su ID.
        
        Este método es requerido por Django para mantener la sesión del usuario.
        No necesita validación de tenant aquí porque la validación se hace en authenticate().
        
        Args:
            user_id: ID del usuario
        
        Returns:
            User: Usuario encontrado o None
        """
        return super().get_user(user_id)
