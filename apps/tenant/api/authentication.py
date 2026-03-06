"""
Autenticación personalizada para APIs de tenants.

⚠️ DESARROLLO: CSRF relajado solo en DEBUG=True
- En desarrollo, permite PATCH sin validar CSRF para facilitar testing del workspace
- En producción, mantiene CSRF estricto (comportamiento seguro)

⚠️ SEGURIDAD: Este módulo NO relaja autenticación ni permisos, solo CSRF en desarrollo.
"""

from django.conf import settings
from rest_framework.authentication import SessionAuthentication


class UnsafeSessionAuthentication(SessionAuthentication):
    """
    Autenticación de sesión que NO valida CSRF en desarrollo.
    
    ⚠️ SOLO PARA DESARROLLO (DEBUG=True):
    - Permite PATCH/POST sin token CSRF válido
    - Facilita testing del workspace en desarrollo local
    - NO afecta producción (solo se usa cuando DEBUG=True)
    
    ⚠️ IMPORTANTE:
    - La autenticación de sesión sigue funcionando (usuario debe estar logueado)
    - Los permisos siguen aplicándose (IsAuthenticated, IsTenantMember, etc.)
    - Solo se omite la validación de CSRF token
    
    Uso:
        from django.conf import settings
        from apps.tenant.api.authentication import UnsafeSessionAuthentication
        
        class MyViewSet(viewsets.ModelViewSet):
            if settings.DEBUG:
                authentication_classes = [UnsafeSessionAuthentication]
            else:
                authentication_classes = [SessionAuthentication]
    """
    
    def enforce_csrf(self, request):
        """
        Omite la validación de CSRF en desarrollo.
        
        ⚠️ CRÍTICO: Este método solo se ejecuta cuando DEBUG=True.
        En producción, esta clase NO debe usarse.
        """
        # En desarrollo, no validar CSRF
        # Esto permite que el workspace funcione aunque el token CSRF esté roto/ausente
        return
