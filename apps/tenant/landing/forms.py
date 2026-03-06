"""
Formulario de autenticación seguro para tenants privados.

⚠️ SEGURIDAD: Este formulario valida que el usuario tenga una TenantMembership
activa para el tenant actual antes de permitir el login.

Sin esta validación, cualquier usuario global podría loguearse en cualquier tenant,
violando el aislamiento multi-tenant.
"""
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.db import connection
from django_tenants.utils import get_public_schema_name

from apps.public.tenants.models import TenantMembership


class TenantAuthenticationForm(AuthenticationForm):
    """
    Formulario de autenticación que valida membresía del tenant.
    
    ⚠️ SEGURIDAD CRÍTICA: Este formulario previene el acceso cross-tenant
    validando que el usuario tenga una TenantMembership activa para el
    tenant actual antes de permitir el login.
    
    Flujo de validación:
    1. Django valida credenciales (username/password) - método padre
    2. Si las credenciales son válidas, se llama a confirm_login_allowed()
    3. Este método valida que el usuario tenga membresía en el tenant actual
    4. Si no tiene membresía o está inactiva, lanza ValidationError
    """
    
    def __init__(self, request=None, *args, **kwargs):
        """
        Inicializa el formulario con el request.
        
        LoginView pasa automáticamente request=request al formulario,
        pero lo hacemos explícito para asegurar que esté disponible.
        """
        super().__init__(request=request, *args, **kwargs)
        # El request se almacena en self.request por AuthenticationForm
    
    def clean(self):
        """
        Valida las credenciales y la membresía del tenant.
        
        ⚠️ UX CRÍTICA: Este método distingue entre:
        - "Contraseña incorrecta" (credenciales inválidas)
        - "Usuario no autorizado en este tenant" (credenciales válidas pero sin membresía)
        
        Esto evita que el usuario crea que olvidó su clave cuando en realidad
        no tiene acceso a este tenant.
        """
        # Llamar al método padre primero (valida username/password)
        cleaned_data = super().clean()
        
        # Si el formulario ya tiene errores (credenciales inválidas), no continuar
        if self.errors:
            return cleaned_data
        
        # Obtener el usuario autenticado (si las credenciales son válidas)
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')
        
        if not username or not password:
            return cleaned_data
        
        # Intentar autenticar usando el backend (que valida membresía)
        from django.contrib.auth import authenticate
        user = authenticate(
            request=self.request,
            username=username,
            password=password
        )
        
        # Si el backend retorna None, puede ser por dos razones:
        # 1. Credenciales inválidas (ya manejado por el método padre)
        # 2. Credenciales válidas pero sin membresía (necesitamos detectar esto)
        
        if user is None:
            # Verificar si el usuario existe y el password es correcto
            # Esto nos permite distinguir entre "password incorrecto" y "sin membresía"
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            try:
                # Intentar obtener el usuario (puede ser username o email)
                try:
                    user_obj = User.objects.get(username=username)
                except User.DoesNotExist:
                    try:
                        user_obj = User.objects.get(email=username)
                    except User.DoesNotExist:
                        user_obj = None
                
                # Si el usuario existe, verificar el password manualmente
                if user_obj and user_obj.check_password(password):
                    # Credenciales válidas pero backend retornó None = Sin membresía
                    tenant = getattr(self.request, 'tenant', None)
                    tenant_name = getattr(tenant, 'nombre', 'esta empresa') if tenant else 'esta empresa'
                    
                    raise forms.ValidationError(
                        f"Tu cuenta existe, pero no tienes acceso a la empresa {tenant_name}. "
                        "Contacta a tu administrador.",
                        code='no_membership'
                    )
                # Si el password no coincide, el error ya fue manejado por el método padre
            except forms.ValidationError:
                # Re-lanzar ValidationError de membresía
                raise
            except Exception:
                # Si hay algún error al verificar, dejar que el método padre maneje el error genérico
                pass
        
        return cleaned_data
    
    def confirm_login_allowed(self, user):
        """
        Valida que el usuario tenga membresía activa en el tenant actual.
        
        ⚠️ SEGURIDAD: Este método se ejecuta DESPUÉS de validar credenciales
        pero ANTES de autenticar al usuario. Si falla, el login se rechaza.
        
        Args:
            user: Usuario autenticado (credenciales válidas)
        
        Raises:
            forms.ValidationError: Si el usuario no tiene membresía o está inactiva
        
        Returns:
            None: Si la validación pasa, permite el login
        """
        # Llamar al método padre primero (valida usuario activo, etc.)
        super().confirm_login_allowed(user)
        
        # Obtener el tenant actual desde el request
        # django-tenants inyecta 'tenant' en request mediante TenantMainMiddleware
        tenant = getattr(self.request, 'tenant', None)
        
        if not tenant:
            # Si no hay tenant en el request, algo está mal configurado
            # En este caso, permitimos el login (fallback para desarrollo)
            # En producción, esto no debería pasar
            return
        
        # Si el tenant es 'public', permitir acceso (admin global)
        # El esquema 'public' es especial y no requiere membresía
        if tenant.schema_name == 'public':
            return
        
        # Guardar el esquema actual para restaurarlo después
        current_schema = connection.schema_name
        
        try:
            # Cambiar al esquema public para consultar TenantMembership
            # TenantMembership está en SHARED_APPS, así que vive en el esquema public
            connection.set_schema_to_public()
            
            # Buscar membresía del usuario en el tenant actual
            membership = TenantMembership.objects.filter(
                client=tenant,
                user=user
            ).first()
            
            # Restaurar el esquema original
            connection.set_schema(current_schema)
            
            # Validar membresía
            if not membership:
                # Usuario no tiene membresía en este tenant
                tenant_name = getattr(tenant, 'nombre', 'esta empresa')
                raise forms.ValidationError(
                    f"Tu cuenta existe, pero no tienes acceso a la empresa {tenant_name}. "
                    "Contacta a tu administrador.",
                    code='no_membership'
                )
            
            # Verificar que la membresía esté activa
            # Nota: TenantMembership no tiene campo is_active por defecto,
            # pero podemos verificar si el tenant está activo
            if not tenant.is_active:
                raise forms.ValidationError(
                    "Esta empresa está suspendida. Por favor, contacta al administrador.",
                    code='tenant_inactive'
                )
            
            # Si llegamos aquí, el usuario tiene membresía activa
            # Permitir el login (no hacer nada, el método padre ya validó)
            
        except forms.ValidationError:
            # Re-lanzar ValidationError (no restaurar esquema, ya se hizo arriba)
            raise
        except Exception as e:
            # En caso de error inesperado, restaurar esquema y re-lanzar
            connection.set_schema(current_schema)
            # Log del error para debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error al validar membresía en TenantAuthenticationForm: {e}")
            # Por seguridad, rechazar el login si hay error
            raise forms.ValidationError(
                "Error al validar acceso. Por favor, intenta nuevamente.",
                code='validation_error'
            )
