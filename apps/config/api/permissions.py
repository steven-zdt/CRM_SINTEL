"""
Permisos base para APIs.

Referencia: https://www.django-rest-framework.org/api-guide/permissions/
"""
from rest_framework.permissions import IsAuthenticated


class IsAuthenticatedDefault(IsAuthenticated):
    """
    Permiso base para APIs del proyecto.
    
    Extender aquí en el futuro para controlar permisos por tenant/rol.
    Por ahora, solo requiere autenticación.
    """
    pass
